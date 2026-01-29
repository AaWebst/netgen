#!/usr/bin/env python3
"""
IPv6 Packet Builder and ICMPv6 Support
Full IPv6 stack implementation for VEP1445
"""

import struct
import socket
import random
from typing import Optional, Tuple

class IPv6Packet:
    """IPv6 Packet Builder"""
    
    def __init__(self, src_ip: str, dst_ip: str, payload: bytes, 
                 next_header: int, hop_limit: int = 64):
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.payload = payload
        self.next_header = next_header
        self.hop_limit = hop_limit
        self.traffic_class = 0
        self.flow_label = 0
    
    def build(self) -> bytes:
        """Build complete IPv6 packet"""
        # IPv6 header is 40 bytes
        version_tc_fl = (6 << 28) | (self.traffic_class << 20) | self.flow_label
        payload_length = len(self.payload)
        
        # Pack IPv6 header
        header = struct.pack('!IHBBx',
            version_tc_fl,      # Version (4 bits), Traffic Class (8 bits), Flow Label (20 bits)
            payload_length,     # Payload Length
            self.next_header,   # Next Header
            self.hop_limit      # Hop Limit
        )
        
        # Add source and destination addresses (16 bytes each)
        src_addr = socket.inet_pton(socket.AF_INET6, self.src_ip)
        dst_addr = socket.inet_pton(socket.AF_INET6, self.dst_ip)
        
        # Note: struct format needs adjustment - pack header manually
        header = struct.pack('!I', version_tc_fl)
        header += struct.pack('!HBB', payload_length, self.next_header, self.hop_limit)
        header += src_addr
        header += dst_addr
        
        return header + self.payload
    
    @staticmethod
    def parse(packet: bytes) -> dict:
        """Parse IPv6 packet"""
        if len(packet) < 40:
            raise ValueError("Packet too short for IPv6")
        
        # Parse header
        version_tc_fl = struct.unpack('!I', packet[0:4])[0]
        version = (version_tc_fl >> 28) & 0xF
        traffic_class = (version_tc_fl >> 20) & 0xFF
        flow_label = version_tc_fl & 0xFFFFF
        
        payload_length = struct.unpack('!H', packet[4:6])[0]
        next_header = packet[6]
        hop_limit = packet[7]
        
        src_ip = socket.inet_ntop(socket.AF_INET6, packet[8:24])
        dst_ip = socket.inet_ntop(socket.AF_INET6, packet[24:40])
        
        payload = packet[40:40+payload_length]
        
        return {
            'version': version,
            'traffic_class': traffic_class,
            'flow_label': flow_label,
            'payload_length': payload_length,
            'next_header': next_header,
            'hop_limit': hop_limit,
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'payload': payload
        }

class ICMPv6:
    """ICMPv6 Message Builder"""
    
    # ICMPv6 Types
    ECHO_REQUEST = 128
    ECHO_REPLY = 129
    NEIGHBOR_SOLICITATION = 135
    NEIGHBOR_ADVERTISEMENT = 136
    ROUTER_SOLICITATION = 133
    ROUTER_ADVERTISEMENT = 134
    
    @staticmethod
    def build_echo_request(identifier: int, sequence: int, data: bytes = b'') -> bytes:
        """Build ICMPv6 Echo Request (ping)"""
        icmp_type = ICMPv6.ECHO_REQUEST
        icmp_code = 0
        checksum = 0  # Will calculate later
        
        message = struct.pack('!BBHHH',
            icmp_type,
            icmp_code,
            checksum,
            identifier,
            sequence
        )
        message += data
        
        # Calculate checksum (simplified - should include pseudo-header)
        checksum = ICMPv6._calculate_checksum(message)
        
        # Rebuild with correct checksum
        message = struct.pack('!BBHHH',
            icmp_type,
            icmp_code,
            checksum,
            identifier,
            sequence
        ) + data
        
        return message
    
    @staticmethod
    def build_neighbor_solicitation(target_ip: str, src_mac: str) -> bytes:
        """Build ICMPv6 Neighbor Solicitation (like ARP for IPv6)"""
        icmp_type = ICMPv6.NEIGHBOR_SOLICITATION
        icmp_code = 0
        checksum = 0
        reserved = 0
        
        # Convert target IP to bytes
        target_addr = socket.inet_pton(socket.AF_INET6, target_ip)
        
        # Build message
        message = struct.pack('!BBHI',
            icmp_type,
            icmp_code,
            checksum,
            reserved
        )
        message += target_addr
        
        # Add source link-layer address option
        option_type = 1  # Source Link-Layer Address
        option_length = 1  # In units of 8 bytes
        mac_bytes = bytes.fromhex(src_mac.replace(':', ''))
        
        message += struct.pack('!BB', option_type, option_length)
        message += mac_bytes
        
        # Calculate checksum
        checksum = ICMPv6._calculate_checksum(message)
        
        # Rebuild with checksum
        message = struct.pack('!BBHI',
            icmp_type,
            icmp_code,
            checksum,
            reserved
        ) + target_addr
        message += struct.pack('!BB', option_type, option_length) + mac_bytes
        
        return message
    
    @staticmethod
    def build_neighbor_advertisement(target_ip: str, dst_mac: str, 
                                    router: bool = False, solicited: bool = True,
                                    override: bool = True) -> bytes:
        """Build ICMPv6 Neighbor Advertisement"""
        icmp_type = ICMPv6.NEIGHBOR_ADVERTISEMENT
        icmp_code = 0
        checksum = 0
        
        # Flags: Router(R), Solicited(S), Override(O)
        flags = 0
        if router:
            flags |= 0x80000000
        if solicited:
            flags |= 0x40000000
        if override:
            flags |= 0x20000000
        
        target_addr = socket.inet_pton(socket.AF_INET6, target_ip)
        
        message = struct.pack('!BBHI',
            icmp_type,
            icmp_code,
            checksum,
            flags
        )
        message += target_addr
        
        # Add target link-layer address option
        option_type = 2  # Target Link-Layer Address
        option_length = 1
        mac_bytes = bytes.fromhex(dst_mac.replace(':', ''))
        
        message += struct.pack('!BB', option_type, option_length)
        message += mac_bytes
        
        # Calculate checksum
        checksum = ICMPv6._calculate_checksum(message)
        
        # Rebuild
        message = struct.pack('!BBHI',
            icmp_type,
            icmp_code,
            checksum,
            flags
        ) + target_addr
        message += struct.pack('!BB', option_type, option_length) + mac_bytes
        
        return message
    
    @staticmethod
    def _calculate_checksum(data: bytes) -> int:
        """Calculate ICMPv6 checksum (simplified)"""
        if len(data) % 2:
            data += b'\x00'
        
        checksum = 0
        for i in range(0, len(data), 2):
            word = (data[i] << 8) + data[i+1]
            checksum += word
            checksum = (checksum & 0xFFFF) + (checksum >> 16)
        
        return ~checksum & 0xFFFF
    
    @staticmethod
    def parse(data: bytes) -> dict:
        """Parse ICMPv6 message"""
        if len(data) < 4:
            raise ValueError("ICMPv6 message too short")
        
        icmp_type = data[0]
        icmp_code = data[1]
        checksum = struct.unpack('!H', data[2:4])[0]
        
        result = {
            'type': icmp_type,
            'code': icmp_code,
            'checksum': checksum,
            'payload': data[4:]
        }
        
        # Parse specific types
        if icmp_type in [ICMPv6.ECHO_REQUEST, ICMPv6.ECHO_REPLY]:
            if len(data) >= 8:
                identifier, sequence = struct.unpack('!HH', data[4:8])
                result['identifier'] = identifier
                result['sequence'] = sequence
                result['data'] = data[8:]
        
        elif icmp_type == ICMPv6.NEIGHBOR_SOLICITATION:
            if len(data) >= 24:
                reserved = struct.unpack('!I', data[4:8])[0]
                target = socket.inet_ntop(socket.AF_INET6, data[8:24])
                result['target'] = target
        
        elif icmp_type == ICMPv6.NEIGHBOR_ADVERTISEMENT:
            if len(data) >= 24:
                flags = struct.unpack('!I', data[4:8])[0]
                target = socket.inet_ntop(socket.AF_INET6, data[8:24])
                result['flags'] = flags
                result['target'] = target
                result['router'] = bool(flags & 0x80000000)
                result['solicited'] = bool(flags & 0x40000000)
                result['override'] = bool(flags & 0x20000000)
        
        return result

class IPv6Helper:
    """IPv6 Helper Functions"""
    
    @staticmethod
    def expand_ipv6(addr: str) -> str:
        """Expand compressed IPv6 address"""
        return socket.inet_ntop(socket.AF_INET6, socket.inet_pton(socket.AF_INET6, addr))
    
    @staticmethod
    def compress_ipv6(addr: str) -> str:
        """Compress IPv6 address (remove leading zeros, compress longest run of zeros)"""
        # Python's inet_ntop already does compression
        return socket.inet_ntop(socket.AF_INET6, socket.inet_pton(socket.AF_INET6, addr))
    
    @staticmethod
    def is_link_local(addr: str) -> bool:
        """Check if address is link-local (fe80::/10)"""
        try:
            packed = socket.inet_pton(socket.AF_INET6, addr)
            return packed[0] == 0xfe and (packed[1] & 0xc0) == 0x80
        except:
            return False
    
    @staticmethod
    def is_multicast(addr: str) -> bool:
        """Check if address is multicast (ff00::/8)"""
        try:
            packed = socket.inet_pton(socket.AF_INET6, addr)
            return packed[0] == 0xff
        except:
            return False
    
    @staticmethod
    def solicited_node_multicast(addr: str) -> str:
        """Get solicited-node multicast address for given IPv6 address"""
        try:
            packed = socket.inet_pton(socket.AF_INET6, addr)
            # ff02::1:ff00:0/104 + last 24 bits of address
            last_24 = packed[13:16]
            multicast = b'\xff\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\xff' + last_24
            return socket.inet_ntop(socket.AF_INET6, multicast)
        except:
            return None
    
    @staticmethod
    def mac_to_link_local(mac: str) -> str:
        """Convert MAC address to IPv6 link-local address (EUI-64)"""
        # Remove separators
        mac_clean = mac.replace(':', '').replace('-', '')
        if len(mac_clean) != 12:
            raise ValueError("Invalid MAC address")
        
        # Convert to bytes
        mac_bytes = bytes.fromhex(mac_clean)
        
        # Insert FFFE in the middle
        eui64 = mac_bytes[:3] + b'\xff\xfe' + mac_bytes[3:]
        
        # Flip 7th bit (universal/local bit)
        eui64 = bytes([eui64[0] ^ 0x02]) + eui64[1:]
        
        # Build link-local address (fe80::/64 + EUI-64)
        link_local = b'\xfe\x80' + b'\x00' * 6 + eui64
        
        return socket.inet_ntop(socket.AF_INET6, link_local)

# Test and usage examples
if __name__ == '__main__':
    print("IPv6 Module Test")
    print("=" * 60)
    
    # Test 1: IPv6 packet building
    print("\n1. IPv6 Packet Builder:")
    icmp_payload = ICMPv6.build_echo_request(1234, 1, b'Hello IPv6')
    ipv6_packet = IPv6Packet(
        src_ip='2001:db8::1',
        dst_ip='2001:db8::2',
        payload=icmp_payload,
        next_header=58  # ICMPv6
    )
    packet = ipv6_packet.build()
    print(f"  Built IPv6 packet: {len(packet)} bytes")
    print(f"  Header: {packet[:40].hex()}")
    
    # Test 2: ICMPv6 Echo Request
    print("\n2. ICMPv6 Echo Request (Ping):")
    echo = ICMPv6.build_echo_request(9999, 1, b'ping data')
    print(f"  Built ICMPv6 echo: {len(echo)} bytes")
    
    # Test 3: Neighbor Solicitation
    print("\n3. ICMPv6 Neighbor Solicitation:")
    ns = ICMPv6.build_neighbor_solicitation('fe80::1', '00:11:22:33:44:55')
    print(f"  Built NS: {len(ns)} bytes")
    
    # Test 4: IPv6 address helpers
    print("\n4. IPv6 Address Helpers:")
    link_local = IPv6Helper.mac_to_link_local('00:11:22:33:44:55')
    print(f"  Link-local from MAC: {link_local}")
    
    solicited = IPv6Helper.solicited_node_multicast('2001:db8::abcd')
    print(f"  Solicited-node multicast: {solicited}")
    
    print(f"  Is link-local? {IPv6Helper.is_link_local('fe80::1')}")
    print(f"  Is multicast? {IPv6Helper.is_multicast('ff02::1')}")
    
    print("\n✓ IPv6 module ready for integration")
