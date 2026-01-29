#!/usr/bin/env python3
"""
TCP Packet Builder
Constructs TCP packets with proper headers, options, and checksums
"""

import struct
import socket
import random
from enum import IntFlag
from typing import Optional, Dict, List, Tuple

class TCPFlags(IntFlag):
    """TCP Header Flags"""
    FIN = 0x01
    SYN = 0x02
    RST = 0x04
    PSH = 0x08
    ACK = 0x10
    URG = 0x20
    ECE = 0x40
    CWR = 0x80

class TCPOption:
    """TCP Options"""
    END_OF_OPTIONS = 0
    NOP = 1
    MSS = 2
    WINDOW_SCALE = 3
    SACK_PERMITTED = 4
    SACK = 5
    TIMESTAMP = 8

class TCPPacket:
    """TCP Packet Builder"""
    
    def __init__(self,
                 src_ip: str,
                 dst_ip: str,
                 src_port: int,
                 dst_port: int,
                 seq_num: int = 0,
                 ack_num: int = 0,
                 flags: int = 0,
                 window: int = 65535,
                 data: bytes = b'',
                 options: Optional[List[Tuple[int, bytes]]] = None):
        
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.src_port = src_port
        self.dst_port = dst_port
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.window = window
        self.data = data
        self.options = options or []
        
    def build(self) -> bytes:
        """Build complete TCP packet with IP header"""
        tcp_header = self._build_tcp_header()
        ip_header = self._build_ip_header(len(tcp_header) + len(self.data))
        
        return ip_header + tcp_header + self.data
    
    def _build_tcp_header(self) -> bytes:
        """Build TCP header with options and checksum"""
        # Build options
        options_bytes = self._build_options()
        
        # Calculate data offset (header length in 32-bit words)
        header_len = 20 + len(options_bytes)
        data_offset = (header_len + 3) // 4  # Round up to nearest word
        
        # Pad options to 4-byte boundary
        padding_len = (data_offset * 4) - header_len
        options_bytes += b'\x00' * padding_len
        
        # Build TCP header (without checksum)
        tcp_header = struct.pack('!HHIIBBHHH',
            self.src_port,           # Source port
            self.dst_port,           # Destination port
            self.seq_num,            # Sequence number
            self.ack_num,            # Acknowledgment number
            (data_offset << 4),      # Data offset (4 bits) + reserved (4 bits)
            self.flags,              # Flags
            self.window,             # Window size
            0,                       # Checksum (placeholder)
            0                        # Urgent pointer
        )
        
        # Add options
        tcp_header += options_bytes
        
        # Calculate checksum
        checksum = self._calculate_tcp_checksum(tcp_header + self.data)
        
        # Rebuild header with correct checksum
        tcp_header = struct.pack('!HHIIBBH',
            self.src_port,
            self.dst_port,
            self.seq_num,
            self.ack_num,
            (data_offset << 4),
            self.flags,
            self.window,
            checksum
        ) + struct.pack('!H', 0) + options_bytes  # Urgent pointer + options
        
        return tcp_header
    
    def _build_options(self) -> bytes:
        """Build TCP options"""
        options_bytes = b''
        
        for opt_kind, opt_data in self.options:
            if opt_kind == TCPOption.END_OF_OPTIONS:
                break
            elif opt_kind == TCPOption.NOP:
                options_bytes += struct.pack('!B', opt_kind)
            elif opt_kind == TCPOption.MSS:
                mss = struct.unpack('!H', opt_data)[0]
                options_bytes += struct.pack('!BBH', opt_kind, 4, mss)
            elif opt_kind == TCPOption.WINDOW_SCALE:
                shift = struct.unpack('!B', opt_data)[0]
                options_bytes += struct.pack('!BBB', opt_kind, 3, shift)
            elif opt_kind == TCPOption.SACK_PERMITTED:
                options_bytes += struct.pack('!BB', opt_kind, 2)
            elif opt_kind == TCPOption.TIMESTAMP:
                ts_val, ts_ecr = struct.unpack('!II', opt_data)
                options_bytes += struct.pack('!BBII', opt_kind, 10, ts_val, ts_ecr)
            else:
                # Generic option
                options_bytes += struct.pack('!BB', opt_kind, 2 + len(opt_data)) + opt_data
        
        return options_bytes
    
    def _calculate_tcp_checksum(self, tcp_segment: bytes) -> int:
        """Calculate TCP checksum over pseudo-header + TCP segment"""
        # Build pseudo-header
        src_addr = socket.inet_aton(self.src_ip)
        dst_addr = socket.inet_aton(self.dst_ip)
        
        pseudo_header = struct.pack('!4s4sBBH',
            src_addr,
            dst_addr,
            0,                      # Reserved
            socket.IPPROTO_TCP,     # Protocol
            len(tcp_segment)        # TCP length
        )
        
        # Combine pseudo-header and TCP segment
        data = pseudo_header + tcp_segment
        
        # Calculate checksum
        if len(data) % 2 == 1:
            data += b'\x00'
        
        checksum = 0
        for i in range(0, len(data), 2):
            word = (data[i] << 8) + data[i + 1]
            checksum += word
            checksum = (checksum & 0xffff) + (checksum >> 16)
        
        checksum = ~checksum & 0xffff
        return checksum
    
    def _build_ip_header(self, payload_len: int) -> bytes:
        """Build IPv4 header"""
        version_ihl = 0x45  # Version 4, header length 5 (20 bytes)
        tos = 0
        total_length = 20 + payload_len
        identification = random.randint(0, 65535)
        flags_fragment = 0x4000  # Don't fragment
        ttl = 64
        protocol = socket.IPPROTO_TCP
        
        src_addr = socket.inet_aton(self.src_ip)
        dst_addr = socket.inet_aton(self.dst_ip)
        
        # Build header without checksum
        header = struct.pack('!BBHHHBBH4s4s',
            version_ihl, tos, total_length,
            identification, flags_fragment,
            ttl, protocol, 0,
            src_addr, dst_addr
        )
        
        # Calculate IP checksum
        checksum = 0
        for i in range(0, len(header), 2):
            word = (header[i] << 8) + header[i + 1]
            checksum += word
            checksum = (checksum & 0xffff) + (checksum >> 16)
        
        checksum = ~checksum & 0xffff
        
        # Rebuild with correct checksum
        header = struct.pack('!BBHHHBBH4s4s',
            version_ihl, tos, total_length,
            identification, flags_fragment,
            ttl, protocol, checksum,
            src_addr, dst_addr
        )
        
        return header
    
    @staticmethod
    def parse(packet_bytes: bytes) -> Dict:
        """Parse TCP packet from bytes"""
        # Parse IP header (assuming 20 bytes, no options)
        ip_header = struct.unpack('!BBHHHBBH4s4s', packet_bytes[:20])
        
        src_ip = socket.inet_ntoa(ip_header[8])
        dst_ip = socket.inet_ntoa(ip_header[9])
        
        # Parse TCP header
        tcp_start = 20
        tcp_header = struct.unpack('!HHIIBBHHH', packet_bytes[tcp_start:tcp_start+20])
        
        src_port = tcp_header[0]
        dst_port = tcp_header[1]
        seq_num = tcp_header[2]
        ack_num = tcp_header[3]
        data_offset = (tcp_header[4] >> 4) * 4
        flags = tcp_header[5]
        window = tcp_header[6]
        
        # Extract data
        tcp_end = tcp_start + data_offset
        data = packet_bytes[tcp_end:]
        
        return {
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'src_port': src_port,
            'dst_port': dst_port,
            'seq_num': seq_num,
            'ack_num': ack_num,
            'flags': flags,
            'window': window,
            'data': data,
            'has_syn': bool(flags & TCPFlags.SYN),
            'has_ack': bool(flags & TCPFlags.ACK),
            'has_fin': bool(flags & TCPFlags.FIN),
            'has_rst': bool(flags & TCPFlags.RST),
            'has_psh': bool(flags & TCPFlags.PSH),
        }

def build_syn_packet(src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                     seq_num: int, mss: int = 1460) -> bytes:
    """Helper: Build SYN packet with MSS option"""
    options = [
        (TCPOption.MSS, struct.pack('!H', mss)),
        (TCPOption.WINDOW_SCALE, struct.pack('!B', 7)),
        (TCPOption.SACK_PERMITTED, b''),
    ]
    
    packet = TCPPacket(
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        seq_num=seq_num,
        flags=TCPFlags.SYN,
        window=65535,
        options=options
    )
    
    return packet.build()

def build_syn_ack_packet(src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                         seq_num: int, ack_num: int) -> bytes:
    """Helper: Build SYN-ACK packet"""
    packet = TCPPacket(
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        seq_num=seq_num,
        ack_num=ack_num,
        flags=TCPFlags.SYN | TCPFlags.ACK,
        window=65535
    )
    
    return packet.build()

def build_ack_packet(src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                     seq_num: int, ack_num: int) -> bytes:
    """Helper: Build ACK packet"""
    packet = TCPPacket(
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        seq_num=seq_num,
        ack_num=ack_num,
        flags=TCPFlags.ACK,
        window=65535
    )
    
    return packet.build()

def build_data_packet(src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                      seq_num: int, ack_num: int, data: bytes) -> bytes:
    """Helper: Build data packet with PSH+ACK"""
    packet = TCPPacket(
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        seq_num=seq_num,
        ack_num=ack_num,
        flags=TCPFlags.PSH | TCPFlags.ACK,
        window=65535,
        data=data
    )
    
    return packet.build()

def build_fin_packet(src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                     seq_num: int, ack_num: int) -> bytes:
    """Helper: Build FIN packet"""
    packet = TCPPacket(
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        seq_num=seq_num,
        ack_num=ack_num,
        flags=TCPFlags.FIN | TCPFlags.ACK,
        window=65535
    )
    
    return packet.build()

def build_rst_packet(src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                     seq_num: int) -> bytes:
    """Helper: Build RST packet"""
    packet = TCPPacket(
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        seq_num=seq_num,
        flags=TCPFlags.RST,
        window=0
    )
    
    return packet.build()

if __name__ == '__main__':
    # Test TCP packet building
    print("Testing TCP Packet Builder...")
    
    # Build SYN packet
    syn = build_syn_packet('192.168.1.1', '192.168.1.2', 12345, 80, 1000)
    print(f"SYN packet: {len(syn)} bytes")
    
    # Build SYN-ACK packet
    syn_ack = build_syn_ack_packet('192.168.1.2', '192.168.1.1', 80, 12345, 2000, 1001)
    print(f"SYN-ACK packet: {len(syn_ack)} bytes")
    
    # Build data packet
    data_pkt = build_data_packet('192.168.1.1', '192.168.1.2', 12345, 80, 1001, 2001, b'Hello, World!')
    print(f"Data packet: {len(data_pkt)} bytes")
    
    print("✓ TCP Packet Builder working!")
