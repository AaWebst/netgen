#!/usr/bin/env python3
"""
VEP1445 Unified Multi-Mode Traffic Generator
Supports mixed deployment: Standard copper ports + DPDK 10G SFP ports
Unified control interface for all interface types
"""

import socket
import struct
import threading
import time
import random
import json
import logging
import mmap
import ctypes
import os
import subprocess
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
import ipaddress
from queue import Queue, Empty
import select
import multiprocessing as mp
from multiprocessing import shared_memory, Value, Array
import array
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Hardware timestamp constants
SO_TIMESTAMPING = 37
SOF_TIMESTAMPING_TX_HARDWARE = (1 << 0)
SOF_TIMESTAMPING_RX_HARDWARE = (1 << 2)
SOF_TIMESTAMPING_RAW_HARDWARE = (1 << 6)

# Performance constants
BATCH_SIZE = 64
HUGE_PAGE_SIZE = 2 * 1024 * 1024


class InterfaceType(Enum):
    """Type of network interface"""
    COPPER_STANDARD = "copper_standard"      # 100M/1G copper, standard mode
    COPPER_OPTIMIZED = "copper_optimized"    # 1G copper, optimized mode
    SFP_10G_DPDK = "sfp_10g_dpdk"           # 10G SFP, DPDK mode
    SFP_10G_OPTIMIZED = "sfp_10g_optimized" # 10G SFP, optimized (non-DPDK)


@dataclass
class InterfaceConfig:
    """Configuration for a single network interface"""
    name: str
    mac_address: str
    interface_type: InterfaceType
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    ipv6_address: Optional[str] = None
    gateway: Optional[str] = None
    vlan_id: Optional[int] = None
    discovered_hosts: List[str] = None
    pci_address: Optional[str] = None
    numa_node: int = 0
    speed_mbps: int = 1000  # Interface speed
    
    def __post_init__(self):
        if self.discovered_hosts is None:
            self.discovered_hosts = []
    
    def is_dpdk_enabled(self) -> bool:
        """Check if this interface uses DPDK"""
        return self.interface_type == InterfaceType.SFP_10G_DPDK
    
    def max_bandwidth_mbps(self) -> int:
        """Get maximum bandwidth for this interface"""
        if self.interface_type == InterfaceType.COPPER_STANDARD:
            return 1000  # 1 Gbps
        elif self.interface_type == InterfaceType.COPPER_OPTIMIZED:
            return 1000  # 1 Gbps
        elif self.interface_type in [InterfaceType.SFP_10G_DPDK, InterfaceType.SFP_10G_OPTIMIZED]:
            return 10000  # 10 Gbps
        return 1000


@dataclass
class TrafficProfile:
    """Traffic generation profile"""
    name: str
    src_interface: str
    dst_interface: str
    dst_ip: str
    bandwidth_mbps: float
    packet_size: int
    protocol: str
    dscp: int = 0
    vlan_outer: Optional[int] = None
    vlan_inner: Optional[int] = None
    vni: Optional[int] = None
    mpls_label: Optional[int] = None
    enabled: bool = True
    
    # Impairments
    latency_ms: float = 0.0
    jitter_ms: float = 0.0
    packet_loss_percent: float = 0.0
    
    # Performance settings (auto-configured based on interface type)
    use_hardware_timestamps: bool = True
    batch_size: int = BATCH_SIZE
    zero_copy: bool = True
    
    # RFC2544
    rfc2544_enabled: bool = False
    rfc2544_frame_sizes: List[int] = None
    rfc2544_throughput_test: bool = False
    rfc2544_latency_test: bool = False
    rfc2544_frame_loss_test: bool = False
    rfc2544_back_to_back_test: bool = False
    
    def __post_init__(self):
        if self.rfc2544_frame_sizes is None:
            self.rfc2544_frame_sizes = [64, 128, 256, 512, 1024, 1280, 1518]


class HardwareTimestamp:
    """Hardware timestamping support"""
    
    @staticmethod
    def enable_hw_timestamps(sock: socket.socket, interface: str) -> bool:
        """Enable hardware timestamping on socket"""
        try:
            flags = (SOF_TIMESTAMPING_TX_HARDWARE |
                    SOF_TIMESTAMPING_RX_HARDWARE |
                    SOF_TIMESTAMPING_RAW_HARDWARE)
            
            sock.setsockopt(socket.SOL_SOCKET, SO_TIMESTAMPING, flags)
            logger.info(f"Hardware timestamping enabled on {interface}")
            return True
            
        except OSError as e:
            logger.debug(f"Hardware timestamping not available on {interface}: {e}")
            return False
    
    @staticmethod
    def get_tx_timestamp(sock: socket.socket) -> Optional[float]:
        """Get hardware TX timestamp in nanoseconds"""
        try:
            data, ancdata, flags, addr = sock.recvmsg(1, 1024, socket.MSG_ERRQUEUE)
            
            for cmsg_level, cmsg_type, cmsg_data in ancdata:
                if cmsg_level == socket.SOL_SOCKET and cmsg_type == SO_TIMESTAMPING:
                    if len(cmsg_data) >= 48:
                        sec = struct.unpack('q', cmsg_data[32:40])[0]
                        nsec = struct.unpack('q', cmsg_data[40:48])[0]
                        return sec * 1e9 + nsec
                        
        except (OSError, BlockingIOError):
            pass
            
        return None


class PacketMemPool:
    """Pre-allocated packet memory pool"""
    
    def __init__(self, num_packets: int = 16384, packet_size: int = 2048):
        self.num_packets = num_packets
        self.packet_size = packet_size
        self.pool_size = num_packets * packet_size
        
        # Try huge pages first
        try:
            self.memory = mmap.mmap(-1, self.pool_size,
                                   flags=mmap.MAP_SHARED | mmap.MAP_ANONYMOUS | mmap.MAP_HUGETLB,
                                   prot=mmap.PROT_READ | mmap.PROT_WRITE)
            logger.debug(f"Allocated {self.pool_size} bytes using huge pages")
        except OSError:
            self.memory = mmap.mmap(-1, self.pool_size,
                                   flags=mmap.MAP_SHARED | mmap.MAP_ANONYMOUS,
                                   prot=mmap.PROT_READ | mmap.PROT_WRITE)
            logger.debug(f"Allocated {self.pool_size} bytes using regular pages")
        
        self.free_packets = Queue(maxsize=num_packets)
        for i in range(num_packets):
            self.free_packets.put(i)
    
    def alloc_packet(self) -> Optional[int]:
        """Allocate packet from pool"""
        try:
            return self.free_packets.get_nowait()
        except Empty:
            return None
    
    def free_packet(self, packet_idx: int):
        """Free packet back to pool"""
        try:
            self.free_packets.put_nowait(packet_idx)
        except:
            pass
    
    def write_packet(self, packet_idx: int, data: bytes) -> int:
        """Write packet data to buffer"""
        if len(data) > self.packet_size:
            data = data[:self.packet_size]
        
        offset = packet_idx * self.packet_size
        length = len(data)
        self.memory[offset:offset + length] = data
        return length


class DPDKInterface:
    """DPDK interface wrapper"""
    
    def __init__(self, port_id: int, config: InterfaceConfig):
        self.port_id = port_id
        self.config = config
        self.dpdk_available = False
        self.dpdk = None
        
        try:
            import dpdk
            self.dpdk = dpdk
            self.dpdk_available = True
            logger.info(f"DPDK available for {config.name} (port {port_id})")
        except ImportError:
            logger.warning(f"DPDK not available for {config.name}, will use fallback")
    
    def init_port(self, num_rx_desc: int = 1024, num_tx_desc: int = 1024) -> bool:
        """Initialize DPDK port"""
        if not self.dpdk_available:
            return False
        
        try:
            self.dpdk.eth_dev_configure(self.port_id, 1, 1)
            self.dpdk.eth_rx_queue_setup(self.port_id, 0, num_rx_desc)
            self.dpdk.eth_tx_queue_setup(self.port_id, 0, num_tx_desc)
            self.dpdk.eth_dev_start(self.port_id)
            
            logger.info(f"DPDK port {self.port_id} ({self.config.name}) initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize DPDK port {self.config.name}: {e}")
            return False
    
    def send_burst(self, packets: List[bytes]) -> int:
        """Send burst of packets via DPDK"""
        if not self.dpdk_available:
            return 0
        
        try:
            mbufs = []
            for pkt in packets:
                mbuf = self.dpdk.pktmbuf_alloc()
                mbuf.data = pkt
                mbufs.append(mbuf)
            
            sent = self.dpdk.eth_tx_burst(self.port_id, 0, mbufs)
            
            for i in range(sent, len(mbufs)):
                self.dpdk.pktmbuf_free(mbufs[i])
            
            return sent
            
        except Exception as e:
            logger.error(f"DPDK send error on {self.config.name}: {e}")
            return 0


class StandardInterface:
    """Standard/optimized raw socket interface"""
    
    def __init__(self, config: InterfaceConfig):
        self.config = config
        self.socket = None
        self.hw_timestamps_enabled = False
        
    def initialize(self) -> bool:
        """Initialize raw socket"""
        try:
            self.socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
            self.socket.bind((self.config.name, 0))
            
            # Optimize buffers
            if self.config.interface_type == InterfaceType.COPPER_OPTIMIZED:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 16 * 1024 * 1024)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16 * 1024 * 1024)
            
            # Try hardware timestamps
            self.hw_timestamps_enabled = HardwareTimestamp.enable_hw_timestamps(
                self.socket, self.config.name
            )
            
            self.socket.setblocking(False)
            
            logger.info(f"Standard interface {self.config.name} initialized "
                       f"(HW timestamps: {self.hw_timestamps_enabled})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.config.name}: {e}")
            return False
    
    def send_packet_batch(self, packets: List[bytes]) -> int:
        """Send batch of packets"""
        sent = 0
        for packet in packets:
            try:
                self.socket.send(packet)
                sent += 1
            except BlockingIOError:
                break
            except Exception as e:
                logger.error(f"Send error on {self.config.name}: {e}")
                break
        return sent
    
    def cleanup(self):
        """Cleanup interface"""
        if self.socket:
            self.socket.close()


class UnifiedNetworkInterface:
    """Unified interface supporting both standard and DPDK modes"""
    
    def __init__(self, config: InterfaceConfig):
        self.config = config
        self.dpdk_interface = None
        self.standard_interface = None
        self.mempool = PacketMemPool()
        
        # Performance counters
        self.tx_packets = Value('Q', 0)
        self.tx_bytes = Value('Q', 0)
        self.rx_packets = Value('Q', 0)
        self.rx_bytes = Value('Q', 0)
        self.dropped = Value('Q', 0)
    
    def initialize(self) -> bool:
        """Initialize interface based on type"""
        if self.config.is_dpdk_enabled():
            # Try DPDK first
            port_id = self._get_dpdk_port_id()
            if port_id >= 0:
                self.dpdk_interface = DPDKInterface(port_id, self.config)
                if self.dpdk_interface.init_port():
                    logger.info(f"{self.config.name}: Running in DPDK mode (10G)")
                    return True
                else:
                    logger.warning(f"{self.config.name}: DPDK init failed, falling back to optimized mode")
            
            # Fallback to optimized standard
            self.config.interface_type = InterfaceType.SFP_10G_OPTIMIZED
        
        # Use standard interface
        self.standard_interface = StandardInterface(self.config)
        if self.standard_interface.initialize():
            mode = "optimized" if "OPTIMIZED" in self.config.interface_type.value else "standard"
            speed = "10G" if "10G" in self.config.interface_type.value else "1G"
            logger.info(f"{self.config.name}: Running in {mode} mode ({speed})")
            return True
        
        return False
    
    def _get_dpdk_port_id(self) -> int:
        """Get DPDK port ID for this interface"""
        try:
            # This is simplified - real implementation would query DPDK
            # For now, extract from interface name if it follows convention
            if 'sfp' in self.config.name.lower():
                # Assume sfp1 -> port 0, sfp2 -> port 1, etc.
                import re
                match = re.search(r'(\d+)$', self.config.name)
                if match:
                    return int(match.group(1)) - 1
            return -1
        except:
            return -1
    
    def send_packet_batch(self, packets: List[bytes]) -> int:
        """Send batch via appropriate backend"""
        if self.dpdk_interface:
            sent = self.dpdk_interface.send_burst(packets)
        elif self.standard_interface:
            sent = self.standard_interface.send_packet_batch(packets)
        else:
            return 0
        
        with self.tx_packets.get_lock():
            self.tx_packets.value += sent
        
        total_bytes = sum(len(p) for p in packets[:sent])
        with self.tx_bytes.get_lock():
            self.tx_bytes.value += total_bytes
        
        return sent
    
    def get_stats(self) -> Dict:
        """Get interface statistics"""
        return {
            'tx_packets': self.tx_packets.value,
            'tx_bytes': self.tx_bytes.value,
            'rx_packets': self.rx_packets.value,
            'rx_bytes': self.rx_bytes.value,
            'dropped': self.dropped.value,
            'interface_type': self.config.interface_type.value,
            'speed_mbps': self.config.speed_mbps,
            'hw_timestamps': (self.standard_interface.hw_timestamps_enabled 
                            if self.standard_interface else False)
        }
    
    def cleanup(self):
        """Cleanup interface resources"""
        if self.standard_interface:
            self.standard_interface.cleanup()


class PacketGenerator:
    """Optimized packet generator"""
    
    def __init__(self):
        self.packet_cache = {}
    
    @staticmethod
    def generate_ethernet_header(src_mac: str, dst_mac: str, ethertype: int = 0x0800) -> bytes:
        """Generate Ethernet header"""
        src = bytes.fromhex(src_mac.replace(':', ''))
        dst = bytes.fromhex(dst_mac.replace(':', ''))
        return dst + src + struct.pack('!H', ethertype)
    
    @staticmethod
    def generate_ipv4_packet(src_ip: str, dst_ip: str, payload_size: int,
                           dscp: int = 0, ttl: int = 64) -> bytes:
        """Generate IPv4 packet"""
        version_ihl = 0x45
        tos = dscp << 2
        total_length = 20 + payload_size
        identification = random.randint(0, 65535)
        flags_fragment = 0x4000
        protocol = 17  # UDP
        
        src_addr = socket.inet_aton(src_ip)
        dst_addr = socket.inet_aton(dst_ip)
        
        header = struct.pack('!BBHHHBBH4s4s',
                           version_ihl, tos, total_length,
                           identification, flags_fragment,
                           ttl, protocol, 0,
                           src_addr, dst_addr)
        
        # Fast checksum
        checksum = 0
        for i in range(0, len(header), 2):
            word = (header[i] << 8) + header[i + 1]
            checksum += word
        checksum = (checksum >> 16) + (checksum & 0xffff)
        checksum += checksum >> 16
        checksum = ~checksum & 0xffff
        
        header = struct.pack('!BBHHHBBH4s4s',
                           version_ihl, tos, total_length,
                           identification, flags_fragment,
                           ttl, protocol, checksum,
                           src_addr, dst_addr)
        
        return header
    
    def generate_packet_batch(self, profile: TrafficProfile, src_mac: str,
                             dst_mac: str, count: int) -> List[bytes]:
        """Generate batch of packets"""
        cache_key = f"{profile.name}_{profile.packet_size}"
        
        if cache_key not in self.packet_cache:
            eth_header = self.generate_ethernet_header(src_mac, dst_mac)
            
            if profile.protocol == 'ipv4':
                ip_packet = self.generate_ipv4_packet(
                    "0.0.0.0",
                    profile.dst_ip,
                    profile.packet_size - 20,
                    dscp=profile.dscp
                )
            else:
                ip_packet = b''
            
            payload_size = profile.packet_size - len(eth_header) - len(ip_packet)
            if payload_size > 0:
                payload = bytes(payload_size)
            else:
                payload = b''
            
            template = eth_header + ip_packet + payload
            self.packet_cache[cache_key] = template
        
        template = self.packet_cache[cache_key]
        return [template] * count


class UnifiedTrafficEngine:
    """Unified traffic engine supporting mixed interface types"""
    
    def __init__(self):
        self.interfaces: Dict[str, UnifiedNetworkInterface] = {}
        self.traffic_profiles: Dict[str, TrafficProfile] = {}
        self.running = False
        self.worker_processes = []
        self.packet_generator = PacketGenerator()
        
    def add_interface(self, config: InterfaceConfig) -> bool:
        """Add and initialize interface"""
        interface = UnifiedNetworkInterface(config)
        if interface.initialize():
            self.interfaces[config.name] = interface
            logger.info(f"Added interface {config.name} ({config.interface_type.value})")
            return True
        return False
    
    def add_traffic_profile(self, profile: TrafficProfile):
        """Add traffic profile with validation"""
        # Validate bandwidth doesn't exceed interface capacity
        src_iface = self.interfaces.get(profile.src_interface)
        if src_iface:
            max_bw = src_iface.config.max_bandwidth_mbps()
            if profile.bandwidth_mbps > max_bw:
                logger.warning(f"Profile {profile.name}: bandwidth {profile.bandwidth_mbps}Mbps "
                             f"exceeds interface max {max_bw}Mbps")
        
        self.traffic_profiles[profile.name] = profile
        logger.info(f"Added profile {profile.name}: {profile.bandwidth_mbps}Mbps "
                   f"({profile.src_interface} → {profile.dst_interface})")
    
    def start_traffic(self):
        """Start all enabled traffic profiles"""
        self.running = True
        
        for name, profile in self.traffic_profiles.items():
            if profile.enabled:
                process = mp.Process(
                    target=self._traffic_worker,
                    args=(profile,),
                    daemon=False
                )
                self.worker_processes.append(process)
                process.start()
                logger.info(f"Started worker for {name}")
    
    def _traffic_worker(self, profile: TrafficProfile):
        """Traffic generation worker process"""
        src_interface = self.interfaces.get(profile.src_interface)
        if not src_interface:
            logger.error(f"Source interface not found: {profile.src_interface}")
            return
        
        # Calculate timing
        bits_per_packet = profile.packet_size * 8
        packets_per_second = (profile.bandwidth_mbps * 1_000_000) / bits_per_packet
        interval_ns = int(1_000_000_000 / packets_per_second) if packets_per_second > 0 else 1000
        
        # Adaptive batch sizing based on rate
        if packets_per_second > 100_000:
            batch_size = min(profile.batch_size, 128)
        elif packets_per_second > 10_000:
            batch_size = min(profile.batch_size, 64)
        else:
            batch_size = min(profile.batch_size, 32)
        
        batch_interval_ns = interval_ns * batch_size
        
        logger.info(f"Worker {profile.name}: {packets_per_second:.0f} pps, "
                   f"batch={batch_size}, interface_type={src_interface.config.interface_type.value}")
        
        # Generate packet template
        src_mac = src_interface.config.mac_address
        dst_mac = "ff:ff:ff:ff:ff:ff"
        
        packet_template = self.packet_generator.generate_packet_batch(
            profile, src_mac, dst_mac, 1
        )[0]
        
        # Main loop
        next_send_time = time.time_ns()
        
        while self.running and profile.enabled:
            current_time = time.time_ns()
            
            if current_time >= next_send_time:
                batch = [packet_template] * batch_size
                src_interface.send_packet_batch(batch)
                next_send_time += batch_interval_ns
                
                if current_time > next_send_time:
                    next_send_time = current_time + batch_interval_ns
            else:
                if packets_per_second < 1000:
                    sleep_time = (next_send_time - current_time) / 1_000_000_000
                    if sleep_time > 0.001:
                        time.sleep(sleep_time - 0.001)
    
    def stop_traffic(self):
        """Stop all traffic generation"""
        self.running = False
        
        for process in self.worker_processes:
            process.join(timeout=2)
            if process.is_alive():
                process.terminate()
        
        self.worker_processes.clear()
        logger.info("All traffic workers stopped")
    
    def get_stats(self) -> Dict:
        """Get statistics for all interfaces"""
        stats = {}
        for name, interface in self.interfaces.items():
            stats[name] = interface.get_stats()
        return stats
    
    def get_interface_capabilities(self) -> Dict:
        """Get capabilities of all interfaces"""
        capabilities = {}
        for name, interface in self.interfaces.items():
            capabilities[name] = {
                'type': interface.config.interface_type.value,
                'speed_mbps': interface.config.speed_mbps,
                'max_bandwidth_mbps': interface.config.max_bandwidth_mbps(),
                'dpdk_enabled': interface.config.is_dpdk_enabled(),
                'hw_timestamps': (interface.standard_interface.hw_timestamps_enabled 
                                if interface.standard_interface else True),
                'pci_address': interface.config.pci_address
            }
        return capabilities
    
    def cleanup(self):
        """Cleanup all resources"""
        self.stop_traffic()
        for interface in self.interfaces.values():
            interface.cleanup()


# Backwards compatibility
TrafficEngineCore = UnifiedTrafficEngine


if __name__ == "__main__":
    print("VEP1445 Unified Multi-Mode Traffic Generator")
    print("=" * 60)
    print("Supports: Copper (1G) + SFP 10G with mixed DPDK/Standard modes")
    print()
    
    # Example configuration
    engine = UnifiedTrafficEngine()
    
    # Add copper ports (standard mode)
    for i in range(1, 6):
        config = InterfaceConfig(
            name=f"eth{i}",
            mac_address=f"00:11:22:33:44:{i:02x}",
            interface_type=InterfaceType.COPPER_OPTIMIZED,
            speed_mbps=1000
        )
        engine.add_interface(config)
    
    # Add SFP 10G ports (DPDK mode)
    for i in range(1, 3):
        config = InterfaceConfig(
            name=f"sfp{i}",
            mac_address=f"00:11:22:33:55:{i:02x}",
            interface_type=InterfaceType.SFP_10G_DPDK,
            speed_mbps=10000
        )
        engine.add_interface(config)
    
    print(f"Initialized {len(engine.interfaces)} interfaces")
    print("\nInterface Capabilities:")
    for name, cap in engine.get_interface_capabilities().items():
        print(f"  {name}: {cap['type']}, {cap['speed_mbps']}Mbps, "
              f"DPDK={cap['dpdk_enabled']}, HW_TS={cap['hw_timestamps']}")
