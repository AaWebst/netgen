#!/usr/bin/env python3
"""
PCAP Replay Module
Load and replay packet captures at configurable speeds
"""

import struct
import time
from typing import List, Callable, Optional
import logging

logger = logging.getLogger(__name__)

class PCAPPacket:
    """Single packet from PCAP file"""
    
    def __init__(self, timestamp: float, captured_len: int, original_len: int, data: bytes):
        self.timestamp = timestamp
        self.captured_len = captured_len
        self.original_len = original_len
        self.data = data
    
    def __repr__(self):
        return f"<PCAPPacket ts={self.timestamp:.6f} len={self.captured_len}>"

class PCAPReader:
    """PCAP File Reader (supports .pcap format)"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.packets = []
        self.header = None
        
    def load(self) -> bool:
        """Load PCAP file"""
        try:
            with open(self.filename, 'rb') as f:
                # Read global header
                magic = struct.unpack('I', f.read(4))[0]
                
                if magic == 0xa1b2c3d4:
                    # Native byte order
                    byteorder = 'native'
                elif magic == 0xd4c3b2a1:
                    # Swapped byte order
                    byteorder = 'swapped'
                    logger.warning("PCAP file has swapped byte order")
                else:
                    logger.error(f"Invalid PCAP magic: {hex(magic)}")
                    return False
                
                # Read rest of global header
                version_major = struct.unpack('H', f.read(2))[0]
                version_minor = struct.unpack('H', f.read(2))[0]
                thiszone = struct.unpack('i', f.read(4))[0]
                sigfigs = struct.unpack('I', f.read(4))[0]
                snaplen = struct.unpack('I', f.read(4))[0]
                network = struct.unpack('I', f.read(4))[0]
                
                self.header = {
                    'magic': magic,
                    'version_major': version_major,
                    'version_minor': version_minor,
                    'thiszone': thiszone,
                    'sigfigs': sigfigs,
                    'snaplen': snaplen,
                    'network': network
                }
                
                logger.info(f"PCAP: version {version_major}.{version_minor}, "
                          f"snaplen={snaplen}, network={network}")
                
                # Read packets
                packet_count = 0
                while True:
                    # Read packet header
                    packet_header = f.read(16)
                    if len(packet_header) < 16:
                        break
                    
                    ts_sec = struct.unpack('I', packet_header[0:4])[0]
                    ts_usec = struct.unpack('I', packet_header[4:8])[0]
                    incl_len = struct.unpack('I', packet_header[8:12])[0]
                    orig_len = struct.unpack('I', packet_header[12:16])[0]
                    
                    # Read packet data
                    packet_data = f.read(incl_len)
                    if len(packet_data) < incl_len:
                        logger.warning(f"Truncated packet at #{packet_count}")
                        break
                    
                    timestamp = ts_sec + ts_usec / 1000000.0
                    
                    packet = PCAPPacket(timestamp, incl_len, orig_len, packet_data)
                    self.packets.append(packet)
                    packet_count += 1
                
                logger.info(f"PCAP: Loaded {packet_count} packets from {self.filename}")
                return True
        
        except Exception as e:
            logger.error(f"Failed to load PCAP: {e}")
            return False
    
    def get_duration(self) -> float:
        """Get capture duration in seconds"""
        if len(self.packets) < 2:
            return 0.0
        return self.packets[-1].timestamp - self.packets[0].timestamp
    
    def get_stats(self) -> dict:
        """Get capture statistics"""
        if not self.packets:
            return {}
        
        total_bytes = sum(p.captured_len for p in self.packets)
        duration = self.get_duration()
        
        return {
            'packet_count': len(self.packets),
            'total_bytes': total_bytes,
            'duration': duration,
            'avg_pps': len(self.packets) / duration if duration > 0 else 0,
            'avg_bps': total_bytes * 8 / duration if duration > 0 else 0,
            'first_timestamp': self.packets[0].timestamp,
            'last_timestamp': self.packets[-1].timestamp
        }

class PCAPReplayer:
    """PCAP Replayer with speed control"""
    
    def __init__(self, pcap_reader: PCAPReader, send_callback: Callable):
        self.reader = pcap_reader
        self.send_callback = send_callback
        self.speed_multiplier = 1.0
        self.loop = False
        self.running = False
        
    def replay(self, speed: float = 1.0, loop: bool = False, 
              interface: str = None, burst: bool = False) -> None:
        """
        Replay packets from PCAP
        
        Args:
            speed: Speed multiplier (1.0 = original speed, 2.0 = 2x, 0.5 = half speed)
            loop: Loop replay indefinitely
            interface: Interface to send on
            burst: Send all packets as fast as possible (ignore timing)
        """
        self.speed_multiplier = speed
        self.loop = loop
        self.running = True
        
        packets = self.reader.packets
        if not packets:
            logger.error("No packets to replay")
            return
        
        logger.info(f"Starting PCAP replay: {len(packets)} packets, "
                   f"speed={speed}x, loop={loop}, burst={burst}")
        
        iterations = 0
        total_sent = 0
        
        while self.running:
            start_time = time.time()
            base_timestamp = packets[0].timestamp
            
            for i, packet in enumerate(packets):
                if not self.running:
                    break
                
                if not burst:
                    # Calculate when this packet should be sent
                    packet_offset = (packet.timestamp - base_timestamp) / self.speed_multiplier
                    target_time = start_time + packet_offset
                    
                    # Wait until target time
                    now = time.time()
                    if now < target_time:
                        time.sleep(target_time - now)
                
                # Send packet
                try:
                    self.send_callback(packet.data, interface)
                    total_sent += 1
                except Exception as e:
                    logger.error(f"Failed to send packet {i}: {e}")
            
            iterations += 1
            
            if not self.loop:
                break
        
        logger.info(f"PCAP replay complete: {total_sent} packets sent in {iterations} iteration(s)")
        self.running = False
    
    def stop(self):
        """Stop replay"""
        self.running = False

class PCAPWriter:
    """PCAP File Writer"""
    
    def __init__(self, filename: str, snaplen: int = 65535, network: int = 1):
        self.filename = filename
        self.snaplen = snaplen
        self.network = network  # 1 = Ethernet
        self.file = None
        
    def open(self):
        """Open file and write global header"""
        self.file = open(self.filename, 'wb')
        
        # Write global header
        self.file.write(struct.pack('I', 0xa1b2c3d4))  # Magic
        self.file.write(struct.pack('H', 2))           # Version major
        self.file.write(struct.pack('H', 4))           # Version minor
        self.file.write(struct.pack('i', 0))           # Thiszone
        self.file.write(struct.pack('I', 0))           # Sigfigs
        self.file.write(struct.pack('I', self.snaplen)) # Snaplen
        self.file.write(struct.pack('I', self.network)) # Network
        
        logger.info(f"PCAP writer opened: {self.filename}")
    
    def write_packet(self, data: bytes, timestamp: Optional[float] = None):
        """Write packet to PCAP file"""
        if not self.file:
            raise Exception("PCAP file not opened")
        
        if timestamp is None:
            timestamp = time.time()
        
        ts_sec = int(timestamp)
        ts_usec = int((timestamp - ts_sec) * 1000000)
        
        incl_len = min(len(data), self.snaplen)
        orig_len = len(data)
        
        # Write packet header
        self.file.write(struct.pack('I', ts_sec))
        self.file.write(struct.pack('I', ts_usec))
        self.file.write(struct.pack('I', incl_len))
        self.file.write(struct.pack('I', orig_len))
        
        # Write packet data
        self.file.write(data[:incl_len])
    
    def close(self):
        """Close PCAP file"""
        if self.file:
            self.file.close()
            logger.info(f"PCAP writer closed: {self.filename}")

class PCAPFilter:
    """Filter packets from PCAP"""
    
    @staticmethod
    def filter_by_protocol(packets: List[PCAPPacket], protocol: str) -> List[PCAPPacket]:
        """Filter packets by protocol (tcp, udp, icmp)"""
        filtered = []
        
        for packet in packets:
            # Simple Ethernet frame check (assuming Ethernet)
            if len(packet.data) < 14:
                continue
            
            # Check EtherType
            ethertype = struct.unpack('!H', packet.data[12:14])[0]
            
            if ethertype == 0x0800:  # IPv4
                if len(packet.data) < 34:
                    continue
                
                ip_protocol = packet.data[23]
                
                if protocol.lower() == 'tcp' and ip_protocol == 6:
                    filtered.append(packet)
                elif protocol.lower() == 'udp' and ip_protocol == 17:
                    filtered.append(packet)
                elif protocol.lower() == 'icmp' and ip_protocol == 1:
                    filtered.append(packet)
        
        logger.info(f"Filtered {len(filtered)}/{len(packets)} packets for protocol {protocol}")
        return filtered
    
    @staticmethod
    def filter_by_port(packets: List[PCAPPacket], port: int) -> List[PCAPPacket]:
        """Filter packets by TCP/UDP port"""
        filtered = []
        
        for packet in packets:
            if len(packet.data) < 14:
                continue
            
            ethertype = struct.unpack('!H', packet.data[12:14])[0]
            
            if ethertype == 0x0800:  # IPv4
                if len(packet.data) < 34:
                    continue
                
                ip_protocol = packet.data[23]
                
                if ip_protocol in [6, 17]:  # TCP or UDP
                    # Get IP header length
                    ihl = (packet.data[14] & 0x0F) * 4
                    
                    if len(packet.data) < 14 + ihl + 4:
                        continue
                    
                    src_port = struct.unpack('!H', packet.data[14+ihl:14+ihl+2])[0]
                    dst_port = struct.unpack('!H', packet.data[14+ihl+2:14+ihl+4])[0]
                    
                    if src_port == port or dst_port == port:
                        filtered.append(packet)
        
        logger.info(f"Filtered {len(filtered)}/{len(packets)} packets for port {port}")
        return filtered

# Test usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("PCAP Replay Module Test")
    print("=" * 60)
    
    print("\nUsage:")
    print("  # Load PCAP file")
    print("  reader = PCAPReader('capture.pcap')")
    print("  reader.load()")
    print("")
    print("  # Get statistics")
    print("  stats = reader.get_stats()")
    print("  print(f'Packets: {stats[\"packet_count\"]}')")
    print("")
    print("  # Replay at 2x speed")
    print("  replayer = PCAPReplayer(reader, send_callback)")
    print("  replayer.replay(speed=2.0)")
    print("")
    print("  # Filter by protocol")
    print("  tcp_packets = PCAPFilter.filter_by_protocol(reader.packets, 'tcp')")
    print("")
    print("  # Write PCAP")
    print("  writer = PCAPWriter('output.pcap')")
    print("  writer.open()")
    print("  writer.write_packet(packet_data)")
    print("  writer.close()")
    
    print("\n✓ PCAP module ready")
