#!/usr/bin/env python3
"""
VEP1445 Multi-LAN Traffic Generator & Impairment Engine
Supports IPv4/6, MPLS, VXLAN, Q-in-Q, RFC2544
"""

import socket
import struct
import threading
import time
import random
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import ipaddress
from queue import Queue, Empty
import select

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class InterfaceConfig:
    """Configuration for a single network interface"""
    name: str
    mac_address: str
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    ipv6_address: Optional[str] = None
    gateway: Optional[str] = None
    vlan_id: Optional[int] = None
    discovered_hosts: List[str] = None
    
    def __post_init__(self):
        if self.discovered_hosts is None:
            self.discovered_hosts = []


@dataclass
class TrafficProfile:
    """Traffic generation profile"""
    name: str
    src_interface: str
    dst_interface: str
    dst_ip: str
    bandwidth_mbps: float
    packet_size: int
    protocol: str  # 'ipv4', 'ipv6', 'mpls', 'vxlan', 'qinq'
    dscp: int = 0
    vlan_outer: Optional[int] = None
    vlan_inner: Optional[int] = None
    vni: Optional[int] = None  # VXLAN Network Identifier
    mpls_label: Optional[int] = None
    enabled: bool = True
    
    # Impairments
    latency_ms: float = 0.0
    jitter_ms: float = 0.0
    packet_loss_percent: float = 0.0
    
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


class ARPListener:
    """Listen for ARP packets to discover network topology"""
    
    def __init__(self, interface_name: str):
        self.interface_name = interface_name
        self.discovered_ips = set()
        self.ip_mac_map = {}
        self.running = False
        self.thread = None
        
    def start(self):
        """Start ARP listener thread"""
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        logger.info(f"ARP listener started on {self.interface_name}")
        
    def stop(self):
        """Stop ARP listener"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
            
    def _listen_loop(self):
        """Main ARP listening loop"""
        try:
            # Create raw socket for ARP (ETH_P_ARP = 0x0806)
            sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0806))
            sock.bind((self.interface_name, 0))
            sock.settimeout(1.0)
            
            while self.running:
                try:
                    packet, addr = sock.recvfrom(65535)
                    self._parse_arp(packet)
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"ARP parse error: {e}")
                    
        except Exception as e:
            logger.error(f"ARP listener error on {self.interface_name}: {e}")
        finally:
            sock.close()
            
    def _parse_arp(self, packet: bytes):
        """Parse ARP packet and extract IP/MAC information"""
        if len(packet) < 42:
            return
            
        # ARP packet structure
        # Ethernet header: 14 bytes
        # ARP header starts at byte 14
        arp_header = packet[14:42]
        
        # Parse ARP fields
        hw_type = struct.unpack('!H', arp_header[0:2])[0]
        proto_type = struct.unpack('!H', arp_header[2:4])[0]
        
        if hw_type != 1 or proto_type != 0x0800:  # Ethernet and IPv4
            return
            
        operation = struct.unpack('!H', arp_header[6:8])[0]
        sender_mac = ':'.join(f'{b:02x}' for b in arp_header[8:14])
        sender_ip = '.'.join(str(b) for b in arp_header[14:18])
        
        if sender_ip != '0.0.0.0':
            self.discovered_ips.add(sender_ip)
            self.ip_mac_map[sender_ip] = sender_mac
            logger.debug(f"Discovered: {sender_ip} ({sender_mac})")


class DHCPClient:
    """Simple DHCP client for obtaining IP addresses"""
    
    def __init__(self, interface_name: str, mac_address: str):
        self.interface_name = interface_name
        self.mac_address = mac_address
        self.assigned_ip = None
        self.subnet_mask = None
        self.gateway = None
        self.lease_time = 0
        
    def request_ip(self) -> Optional[str]:
        """Request IP address via DHCP"""
        try:
            # Create DHCP discover packet
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', 68))
            sock.settimeout(5.0)
            
            # Build DHCP DISCOVER
            transaction_id = random.randint(0, 0xFFFFFFFF)
            discover = self._build_dhcp_discover(transaction_id)
            
            sock.sendto(discover, ('255.255.255.255', 67))
            logger.info(f"Sent DHCP DISCOVER on {self.interface_name}")
            
            # Wait for OFFER
            try:
                data, addr = sock.recvfrom(1024)
                offer_ip = self._parse_dhcp_offer(data, transaction_id)
                
                if offer_ip:
                    # Send DHCP REQUEST
                    request = self._build_dhcp_request(transaction_id, offer_ip)
                    sock.sendto(request, ('255.255.255.255', 67))
                    logger.info(f"Sent DHCP REQUEST for {offer_ip}")
                    
                    # Wait for ACK
                    data, addr = sock.recvfrom(1024)
                    if self._parse_dhcp_ack(data, transaction_id):
                        logger.info(f"Got DHCP ACK - IP assigned: {self.assigned_ip}")
                        return self.assigned_ip
                        
            except socket.timeout:
                logger.warning(f"DHCP timeout on {self.interface_name}")
                
            sock.close()
            
        except Exception as e:
            logger.error(f"DHCP error on {self.interface_name}: {e}")
            
        return None
        
    def _build_dhcp_discover(self, xid: int) -> bytes:
        """Build DHCP DISCOVER packet"""
        packet = bytearray(300)
        packet[0] = 1  # Boot request
        packet[1] = 1  # Ethernet
        packet[2] = 6  # Hardware address length
        packet[3] = 0  # Hops
        
        struct.pack_into('!I', packet, 4, xid)
        
        # Client MAC address
        mac_bytes = bytes.fromhex(self.mac_address.replace(':', ''))
        packet[28:34] = mac_bytes
        
        # Magic cookie
        packet[236:240] = b'\x63\x82\x53\x63'
        
        # DHCP options
        offset = 240
        # Message type: DISCOVER
        packet[offset:offset+3] = b'\x35\x01\x01'
        offset += 3
        # End option
        packet[offset] = 0xff
        
        return bytes(packet)
        
    def _build_dhcp_request(self, xid: int, requested_ip: str) -> bytes:
        """Build DHCP REQUEST packet"""
        packet = bytearray(300)
        packet[0] = 1  # Boot request
        packet[1] = 1  # Ethernet
        packet[2] = 6  # Hardware address length
        packet[3] = 0  # Hops
        
        struct.pack_into('!I', packet, 4, xid)
        
        # Client MAC address
        mac_bytes = bytes.fromhex(self.mac_address.replace(':', ''))
        packet[28:34] = mac_bytes
        
        # Magic cookie
        packet[236:240] = b'\x63\x82\x53\x63'
        
        # DHCP options
        offset = 240
        # Message type: REQUEST
        packet[offset:offset+3] = b'\x35\x01\x03'
        offset += 3
        # Requested IP
        packet[offset] = 50  # Option code
        packet[offset+1] = 4  # Length
        packet[offset+2:offset+6] = socket.inet_aton(requested_ip)
        offset += 6
        # End option
        packet[offset] = 0xff
        
        return bytes(packet)
        
    def _parse_dhcp_offer(self, packet: bytes, xid: int) -> Optional[str]:
        """Parse DHCP OFFER packet"""
        if len(packet) < 240:
            return None
            
        # Check transaction ID
        pkt_xid = struct.unpack('!I', packet[4:8])[0]
        if pkt_xid != xid:
            return None
            
        # Offered IP address (yiaddr)
        offered_ip = socket.inet_ntoa(packet[16:20])
        
        # Parse options for subnet mask
        offset = 240
        while offset < len(packet) and packet[offset] != 0xff:
            option = packet[offset]
            if option == 0:  # Padding
                offset += 1
                continue
                
            length = packet[offset + 1]
            
            if option == 1:  # Subnet mask
                self.subnet_mask = socket.inet_ntoa(packet[offset+2:offset+6])
            elif option == 3:  # Router/Gateway
                self.gateway = socket.inet_ntoa(packet[offset+2:offset+6])
                
            offset += 2 + length
            
        return offered_ip
        
    def _parse_dhcp_ack(self, packet: bytes, xid: int) -> bool:
        """Parse DHCP ACK packet"""
        if len(packet) < 240:
            return False
            
        # Check transaction ID
        pkt_xid = struct.unpack('!I', packet[4:8])[0]
        if pkt_xid != xid:
            return False
            
        # Assigned IP address
        self.assigned_ip = socket.inet_ntoa(packet[16:20])
        return True


class PacketGenerator:
    """Generate various types of network packets"""
    
    @staticmethod
    def generate_ipv4_packet(src_ip: str, dst_ip: str, payload_size: int, 
                            dscp: int = 0, ttl: int = 64) -> bytes:
        """Generate IPv4 packet"""
        # IPv4 header
        version_ihl = (4 << 4) | 5  # Version 4, IHL 5 (20 bytes)
        tos = dscp << 2
        total_length = 20 + payload_size
        identification = random.randint(0, 65535)
        flags_fragment = 0
        protocol = 17  # UDP
        checksum = 0  # Will be calculated
        
        src_addr = socket.inet_aton(src_ip)
        dst_addr = socket.inet_aton(dst_ip)
        
        header = struct.pack('!BBHHHBBH4s4s',
                           version_ihl, tos, total_length,
                           identification, flags_fragment,
                           ttl, protocol, checksum,
                           src_addr, dst_addr)
        
        # Calculate checksum
        checksum = PacketGenerator._calculate_checksum(header)
        header = struct.pack('!BBHHHBBH4s4s',
                           version_ihl, tos, total_length,
                           identification, flags_fragment,
                           ttl, protocol, checksum,
                           src_addr, dst_addr)
        
        # Generate payload
        payload = bytes(random.getrandbits(8) for _ in range(payload_size))
        
        return header + payload
        
    @staticmethod
    def generate_ipv6_packet(src_ip: str, dst_ip: str, payload_size: int,
                            traffic_class: int = 0) -> bytes:
        """Generate IPv6 packet"""
        # IPv6 header (40 bytes)
        version_class_label = (6 << 28) | (traffic_class << 20)
        payload_length = payload_size
        next_header = 17  # UDP
        hop_limit = 64
        
        src_addr = socket.inet_pton(socket.AF_INET6, src_ip)
        dst_addr = socket.inet_pton(socket.AF_INET6, dst_ip)
        
        header = struct.pack('!IHBB16s16s',
                           version_class_label, payload_length,
                           next_header, hop_limit,
                           src_addr, dst_addr)
        
        payload = bytes(random.getrandbits(8) for _ in range(payload_size))
        
        return header + payload
        
    @staticmethod
    def generate_vlan_tag(vlan_id: int, pcp: int = 0) -> bytes:
        """Generate 802.1Q VLAN tag"""
        tci = (pcp << 13) | vlan_id
        return struct.pack('!HH', 0x8100, tci)
        
    @staticmethod
    def generate_qinq_packet(outer_vlan: int, inner_vlan: int,
                            payload: bytes, outer_pcp: int = 0,
                            inner_pcp: int = 0) -> bytes:
        """Generate Q-in-Q (802.1ad) packet"""
        # Outer tag (802.1ad - 0x88a8)
        outer_tci = (outer_pcp << 13) | outer_vlan
        outer_tag = struct.pack('!HH', 0x88a8, outer_tci)
        
        # Inner tag (802.1Q - 0x8100)
        inner_tci = (inner_pcp << 13) | inner_vlan
        inner_tag = struct.pack('!HH', 0x8100, inner_tci)
        
        return outer_tag + inner_tag + payload
        
    @staticmethod
    def generate_mpls_header(label: int, exp: int = 0, ttl: int = 64,
                            bottom_of_stack: bool = True) -> bytes:
        """Generate MPLS header"""
        bos = 1 if bottom_of_stack else 0
        mpls_word = (label << 12) | (exp << 9) | (bos << 8) | ttl
        return struct.pack('!I', mpls_word)
        
    @staticmethod
    def generate_vxlan_packet(vni: int, inner_packet: bytes) -> bytes:
        """Generate VXLAN packet"""
        # VXLAN header (8 bytes)
        flags = 0x08  # Valid VNI flag
        reserved1 = 0
        vni_reserved = (vni << 8)
        
        vxlan_header = struct.pack('!BBH I',
                                  flags, reserved1, 0, vni_reserved)
        
        return vxlan_header + inner_packet
        
    @staticmethod
    def _calculate_checksum(data: bytes) -> int:
        """Calculate IP checksum"""
        if len(data) % 2 == 1:
            data += b'\x00'
            
        checksum = 0
        for i in range(0, len(data), 2):
            word = (data[i] << 8) + data[i + 1]
            checksum += word
            
        checksum = (checksum >> 16) + (checksum & 0xffff)
        checksum += checksum >> 16
        
        return ~checksum & 0xffff


class TrafficImpairment:
    """Apply network impairments to traffic"""
    
    def __init__(self):
        self.latency_queue = Queue()
        self.processing = False
        self.thread = None
        
    def should_drop_packet(self, loss_percent: float) -> bool:
        """Determine if packet should be dropped based on loss percentage"""
        return random.random() * 100 < loss_percent
        
    def add_latency(self, packet: bytes, latency_ms: float,
                   jitter_ms: float) -> None:
        """Add latency and jitter to packet"""
        actual_latency = latency_ms
        if jitter_ms > 0:
            actual_latency += random.uniform(-jitter_ms, jitter_ms)
            
        send_time = time.time() + (actual_latency / 1000.0)
        self.latency_queue.put((send_time, packet))
        
    def start_processing(self, send_callback):
        """Start processing delayed packets"""
        self.processing = True
        self.thread = threading.Thread(
            target=self._process_delayed_packets,
            args=(send_callback,),
            daemon=True
        )
        self.thread.start()
        
    def stop_processing(self):
        """Stop processing delayed packets"""
        self.processing = False
        if self.thread:
            self.thread.join(timeout=2)
            
    def _process_delayed_packets(self, send_callback):
        """Process packets from latency queue"""
        while self.processing:
            try:
                send_time, packet = self.latency_queue.get(timeout=0.1)
                
                # Wait until send time
                delay = send_time - time.time()
                if delay > 0:
                    time.sleep(delay)
                    
                send_callback(packet)
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Latency processing error: {e}")


class RFC2544Tester:
    """RFC2544 benchmarking tests"""
    
    def __init__(self):
        self.results = {}
        
    def run_throughput_test(self, profile: TrafficProfile,
                           send_func, receive_func) -> Dict:
        """Run RFC2544 throughput test"""
        results = {}
        
        for frame_size in profile.rfc2544_frame_sizes:
            logger.info(f"Testing throughput for frame size {frame_size}")
            
            # Binary search for maximum throughput
            min_rate = 0
            max_rate = profile.bandwidth_mbps
            threshold = 0.001  # 0.001% loss threshold
            
            while max_rate - min_rate > 0.1:
                test_rate = (min_rate + max_rate) / 2
                loss_rate = self._measure_loss_rate(
                    profile, frame_size, test_rate,
                    send_func, receive_func
                )
                
                if loss_rate <= threshold:
                    min_rate = test_rate
                else:
                    max_rate = test_rate
                    
            results[frame_size] = {
                'max_throughput_mbps': min_rate,
                'frame_size': frame_size
            }
            
        return results
        
    def run_latency_test(self, profile: TrafficProfile,
                        send_func, receive_func) -> Dict:
        """Run RFC2544 latency test"""
        results = {}
        
        for frame_size in profile.rfc2544_frame_sizes:
            latencies = []
            num_packets = 1000
            
            for i in range(num_packets):
                start_time = time.time()
                # Send packet with timestamp
                send_func(frame_size, timestamp=start_time)
                
                # Receive and measure
                received_time = receive_func()
                if received_time:
                    latency = (received_time - start_time) * 1000  # ms
                    latencies.append(latency)
                    
                time.sleep(0.001)  # 1ms interval
                
            if latencies:
                results[frame_size] = {
                    'avg_latency_ms': sum(latencies) / len(latencies),
                    'min_latency_ms': min(latencies),
                    'max_latency_ms': max(latencies),
                }
                
        return results
        
    def run_frame_loss_test(self, profile: TrafficProfile,
                           send_func, receive_func) -> Dict:
        """Run RFC2544 frame loss rate test"""
        results = {}
        
        for frame_size in profile.rfc2544_frame_sizes:
            rates = [10, 25, 50, 75, 90, 100]  # Percentage of max rate
            
            for rate_pct in rates:
                test_rate = profile.bandwidth_mbps * (rate_pct / 100)
                loss_rate = self._measure_loss_rate(
                    profile, frame_size, test_rate,
                    send_func, receive_func
                )
                
                if frame_size not in results:
                    results[frame_size] = {}
                    
                results[frame_size][rate_pct] = loss_rate
                
        return results
        
    def run_back_to_back_test(self, profile: TrafficProfile,
                             send_func, receive_func) -> Dict:
        """Run RFC2544 back-to-back test"""
        results = {}
        
        for frame_size in profile.rfc2544_frame_sizes:
            # Send burst at line rate
            burst_size = 10000
            duration_seconds = 2
            
            successful_bursts = []
            
            for trial in range(50):
                sent = 0
                received = 0
                
                start_time = time.time()
                
                # Send burst
                for i in range(burst_size):
                    send_func(frame_size)
                    sent += 1
                    
                # Count received
                time.sleep(duration_seconds)
                received = receive_func(timeout=duration_seconds)
                
                if received == sent:
                    successful_bursts.append(sent)
                    
            if successful_bursts:
                results[frame_size] = {
                    'max_burst_size': max(successful_bursts),
                    'avg_burst_size': sum(successful_bursts) / len(successful_bursts)
                }
                
        return results
        
    def _measure_loss_rate(self, profile: TrafficProfile, frame_size: int,
                          rate_mbps: float, send_func, receive_func) -> float:
        """Measure packet loss rate at given frame size and rate"""
        num_packets = 10000
        duration = 60  # seconds
        
        sent = 0
        received = 0
        
        packets_per_second = (rate_mbps * 1000000) / (frame_size * 8)
        interval = 1.0 / packets_per_second if packets_per_second > 0 else 0.001
        
        start_time = time.time()
        
        while time.time() - start_time < duration and sent < num_packets:
            send_func(frame_size)
            sent += 1
            time.sleep(interval)
            
        # Wait for stragglers
        time.sleep(1)
        
        received = receive_func()
        
        if sent == 0:
            return 100.0
            
        loss_rate = ((sent - received) / sent) * 100
        return max(0.0, loss_rate)


class NetworkInterface:
    """Manage a single network interface"""
    
    def __init__(self, config: InterfaceConfig):
        self.config = config
        self.arp_listener = None
        self.dhcp_client = None
        self.socket = None
        self.running = False
        
    def initialize(self, use_dhcp: bool = True, use_arp_discovery: bool = True):
        """Initialize the network interface"""
        logger.info(f"Initializing interface {self.config.name}")
        
        # Start ARP listener for network discovery
        if use_arp_discovery:
            self.arp_listener = ARPListener(self.config.name)
            self.arp_listener.start()
            time.sleep(2)  # Give it time to discover
            
        # Try DHCP if no IP assigned
        if use_dhcp and not self.config.ip_address:
            self.dhcp_client = DHCPClient(self.config.name, self.config.mac_address)
            assigned_ip = self.dhcp_client.request_ip()
            
            if assigned_ip:
                self.config.ip_address = assigned_ip
                self.config.subnet_mask = self.dhcp_client.subnet_mask
                self.config.gateway = self.dhcp_client.gateway
            else:
                # Auto-assign from ARP discovery
                if self.arp_listener and self.arp_listener.discovered_ips:
                    self._auto_assign_ip()
                    
        # Update discovered hosts
        if self.arp_listener:
            self.config.discovered_hosts = list(self.arp_listener.discovered_ips)
            
    def _auto_assign_ip(self):
        """Auto-assign IP based on discovered network"""
        if not self.arp_listener.discovered_ips:
            return
            
        # Analyze discovered IPs to determine subnet
        discovered = list(self.arp_listener.discovered_ips)
        
        # Simple heuristic: take first IP and modify last octet
        base_ip = discovered[0]
        octets = base_ip.split('.')
        
        # Find unused IP in the same subnet
        for i in range(2, 254):
            test_ip = f"{octets[0]}.{octets[1]}.{octets[2]}.{i}"
            if test_ip not in discovered:
                self.config.ip_address = test_ip
                self.config.subnet_mask = "255.255.255.0"
                logger.info(f"Auto-assigned IP {test_ip} to {self.config.name}")
                break
                
    def create_raw_socket(self):
        """Create raw socket for sending packets"""
        try:
            self.socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            self.socket.bind((self.config.name, 0))
            logger.info(f"Created raw socket on {self.config.name}")
        except Exception as e:
            logger.error(f"Failed to create socket on {self.config.name}: {e}")
            
    def send_packet(self, packet: bytes):
        """Send raw packet"""
        if self.socket:
            try:
                self.socket.send(packet)
            except Exception as e:
                logger.error(f"Send error on {self.config.name}: {e}")
                
    def cleanup(self):
        """Cleanup interface resources"""
        if self.arp_listener:
            self.arp_listener.stop()
        if self.socket:
            self.socket.close()


class TrafficEngineCore:
    """Core traffic generation engine"""
    
    def __init__(self):
        self.interfaces: Dict[str, NetworkInterface] = {}
        self.traffic_profiles: Dict[str, TrafficProfile] = {}
        self.generator_threads: Dict[str, threading.Thread] = {}
        self.running = False
        self.impairment = TrafficImpairment()
        self.rfc2544 = RFC2544Tester()
        self.stats = defaultdict(lambda: {
            'tx_packets': 0,
            'tx_bytes': 0,
            'rx_packets': 0,
            'rx_bytes': 0,
            'dropped_packets': 0
        })
        
    def add_interface(self, config: InterfaceConfig):
        """Add a network interface"""
        interface = NetworkInterface(config)
        self.interfaces[config.name] = interface
        logger.info(f"Added interface: {config.name}")
        
    def initialize_interfaces(self, use_dhcp: bool = True):
        """Initialize all interfaces"""
        for interface in self.interfaces.values():
            interface.initialize(use_dhcp=use_dhcp)
            interface.create_raw_socket()
            
    def add_traffic_profile(self, profile: TrafficProfile):
        """Add traffic generation profile"""
        self.traffic_profiles[profile.name] = profile
        logger.info(f"Added traffic profile: {profile.name}")
        
    def start_traffic(self):
        """Start all enabled traffic profiles"""
        self.running = True
        
        # Start impairment processor
        self.impairment.start_processing(self._send_delayed_packet)
        
        for name, profile in self.traffic_profiles.items():
            if profile.enabled:
                thread = threading.Thread(
                    target=self._traffic_generator_loop,
                    args=(profile,),
                    daemon=True
                )
                self.generator_threads[name] = thread
                thread.start()
                logger.info(f"Started traffic generation: {name}")
                
    def stop_traffic(self):
        """Stop all traffic generation"""
        self.running = False
        self.impairment.stop_processing()
        
        for thread in self.generator_threads.values():
            thread.join(timeout=2)
            
        self.generator_threads.clear()
        logger.info("Stopped all traffic generation")
        
    def _traffic_generator_loop(self, profile: TrafficProfile):
        """Main traffic generation loop for a profile"""
        src_interface = self.interfaces.get(profile.src_interface)
        dst_interface = self.interfaces.get(profile.dst_interface)
        
        if not src_interface or not dst_interface:
            logger.error(f"Invalid interfaces for profile {profile.name}")
            return
            
        # Calculate packet rate
        bits_per_packet = profile.packet_size * 8
        packets_per_second = (profile.bandwidth_mbps * 1000000) / bits_per_packet
        interval = 1.0 / packets_per_second if packets_per_second > 0 else 0.001
        
        logger.info(f"Profile {profile.name}: {packets_per_second:.2f} pps, interval {interval:.6f}s")
        
        while self.running and profile.enabled:
            try:
                # Generate packet based on protocol
                packet = self._generate_packet(profile, src_interface.config, dst_interface.config)
                
                if packet:
                    # Apply impairments
                    if self.impairment.should_drop_packet(profile.packet_loss_percent):
                        self.stats[profile.name]['dropped_packets'] += 1
                    else:
                        if profile.latency_ms > 0 or profile.jitter_ms > 0:
                            self.impairment.add_latency(
                                packet, profile.latency_ms, profile.jitter_ms
                            )
                        else:
                            src_interface.send_packet(packet)
                            
                        self.stats[profile.name]['tx_packets'] += 1
                        self.stats[profile.name]['tx_bytes'] += len(packet)
                        
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Traffic generation error in {profile.name}: {e}")
                time.sleep(0.1)
                
    def _generate_packet(self, profile: TrafficProfile,
                        src_config: InterfaceConfig,
                        dst_config: InterfaceConfig) -> Optional[bytes]:
        """Generate packet according to profile"""
        try:
            if profile.protocol == 'ipv4':
                packet = PacketGenerator.generate_ipv4_packet(
                    src_config.ip_address,
                    profile.dst_ip,
                    profile.packet_size,
                    dscp=profile.dscp
                )
                
            elif profile.protocol == 'ipv6':
                packet = PacketGenerator.generate_ipv6_packet(
                    src_config.ipv6_address or "fe80::1",
                    profile.dst_ip,
                    profile.packet_size,
                    traffic_class=profile.dscp
                )
                
            elif profile.protocol == 'mpls':
                # Generate inner IP packet first
                inner_packet = PacketGenerator.generate_ipv4_packet(
                    src_config.ip_address,
                    profile.dst_ip,
                    profile.packet_size - 4  # Account for MPLS header
                )
                mpls_header = PacketGenerator.generate_mpls_header(
                    profile.mpls_label or 100
                )
                packet = mpls_header + inner_packet
                
            elif profile.protocol == 'vxlan':
                # Generate inner packet
                inner_packet = PacketGenerator.generate_ipv4_packet(
                    src_config.ip_address,
                    profile.dst_ip,
                    profile.packet_size - 8  # Account for VXLAN header
                )
                packet = PacketGenerator.generate_vxlan_packet(
                    profile.vni or 100,
                    inner_packet
                )
                
            elif profile.protocol == 'qinq':
                # Generate inner packet
                inner_packet = PacketGenerator.generate_ipv4_packet(
                    src_config.ip_address,
                    profile.dst_ip,
                    profile.packet_size - 8  # Account for double VLAN tags
                )
                packet = PacketGenerator.generate_qinq_packet(
                    profile.vlan_outer or 100,
                    profile.vlan_inner or 200,
                    inner_packet
                )
                
            else:
                logger.error(f"Unknown protocol: {profile.protocol}")
                return None
                
            return packet
            
        except Exception as e:
            logger.error(f"Packet generation error: {e}")
            return None
            
    def _send_delayed_packet(self, packet: bytes):
        """Callback for sending delayed packets"""
        # This is called by the impairment processor
        # In a real implementation, we'd need to track which interface to use
        # For now, just log
        pass
        
    def get_interface_status(self) -> Dict:
        """Get status of all interfaces"""
        status = {}
        for name, interface in self.interfaces.items():
            status[name] = {
                'ip_address': interface.config.ip_address,
                'subnet_mask': interface.config.subnet_mask,
                'gateway': interface.config.gateway,
                'discovered_hosts': interface.config.discovered_hosts,
                'mac_address': interface.config.mac_address
            }
        return status
        
    def get_traffic_stats(self) -> Dict:
        """Get traffic statistics"""
        return dict(self.stats)
        
    def get_config(self) -> Dict:
        """Get complete configuration"""
        return {
            'interfaces': {
                name: asdict(iface.config)
                for name, iface in self.interfaces.items()
            },
            'traffic_profiles': {
                name: asdict(profile)
                for name, profile in self.traffic_profiles.items()
            }
        }
        
    def save_config(self, filename: str):
        """Save configuration to JSON file"""
        config = self.get_config()
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuration saved to {filename}")
        
    def load_config(self, filename: str):
        """Load configuration from JSON file"""
        with open(filename, 'r') as f:
            config = json.load(f)
            
        # Load interfaces
        for name, iface_data in config.get('interfaces', {}).items():
            iface_config = InterfaceConfig(**iface_data)
            self.add_interface(iface_config)
            
        # Load traffic profiles
        for name, profile_data in config.get('traffic_profiles', {}).items():
            profile = TrafficProfile(**profile_data)
            self.add_traffic_profile(profile)
            
        logger.info(f"Configuration loaded from {filename}")
        
    def cleanup(self):
        """Cleanup all resources"""
        self.stop_traffic()
        for interface in self.interfaces.values():
            interface.cleanup()


# Example usage
if __name__ == "__main__":
    # Create engine
    engine = TrafficEngineCore()
    
    # Add 5 interfaces (simulating VEP1445 with 5 ports)
    for i in range(1, 6):
        config = InterfaceConfig(
            name=f"eth{i}",
            mac_address=f"00:11:22:33:44:{i:02x}"
        )
        engine.add_interface(config)
    
    # Initialize interfaces
    engine.initialize_interfaces()
    
    # Add traffic profiles
    # LAN1 -> LAN2
    profile1 = TrafficProfile(
        name="LAN1_to_LAN2",
        src_interface="eth1",
        dst_interface="eth2",
        dst_ip="192.168.2.100",
        bandwidth_mbps=100.0,
        packet_size=1024,
        protocol="ipv4",
        dscp=46,  # EF for voice
        latency_ms=10.0,
        jitter_ms=2.0,
        packet_loss_percent=0.1
    )
    engine.add_traffic_profile(profile1)
    
    # Save configuration
    engine.save_config('/home/claude/vep1445_config.json')
    
    print("Traffic engine initialized. Configuration saved.")
    print("Interface status:", json.dumps(engine.get_interface_status(), indent=2))
