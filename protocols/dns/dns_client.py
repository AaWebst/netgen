#!/usr/bin/env python3
"""
DNS Client - Query and response handling
Supports A, AAAA, PTR, MX, TXT records
"""

import struct
import socket
import random
import time
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DNSQueryType:
    """DNS Query Types"""
    A = 1        # IPv4 address
    NS = 2       # Name server
    CNAME = 5    # Canonical name
    MX = 15      # Mail exchange
    TXT = 16     # Text
    AAAA = 28    # IPv6 address
    PTR = 12     # Pointer (reverse lookup)

class DNSQuery:
    """DNS Query Builder"""
    
    def __init__(self, domain: str, qtype: int = DNSQueryType.A):
        self.domain = domain
        self.qtype = qtype
        self.qclass = 1  # IN (Internet)
        self.query_id = random.randint(0, 65535)
    
    def build(self) -> bytes:
        """Build DNS query packet"""
        packet = b''
        
        # Header
        packet += struct.pack('!H', self.query_id)  # ID
        packet += struct.pack('!H', 0x0100)  # Flags: standard query
        packet += struct.pack('!H', 1)  # Questions
        packet += struct.pack('!H', 0)  # Answer RRs
        packet += struct.pack('!H', 0)  # Authority RRs
        packet += struct.pack('!H', 0)  # Additional RRs
        
        # Question
        packet += self._encode_domain(self.domain)
        packet += struct.pack('!HH', self.qtype, self.qclass)
        
        return packet
    
    def _encode_domain(self, domain: str) -> bytes:
        """Encode domain name in DNS format"""
        encoded = b''
        
        for label in domain.split('.'):
            encoded += struct.pack('!B', len(label))
            encoded += label.encode('ascii')
        
        encoded += b'\x00'  # Null terminator
        
        return encoded

class DNSResponse:
    """DNS Response Parser"""
    
    def __init__(self, data: bytes):
        self.raw = data
        self.query_id = 0
        self.flags = 0
        self.questions = []
        self.answers = []
        self.authorities = []
        self.additionals = []
        
        self._parse()
    
    def _parse(self):
        """Parse DNS response"""
        try:
            offset = 0
            
            # Header
            self.query_id = struct.unpack('!H', self.raw[offset:offset+2])[0]
            offset += 2
            
            self.flags = struct.unpack('!H', self.raw[offset:offset+2])[0]
            offset += 2
            
            qdcount = struct.unpack('!H', self.raw[offset:offset+2])[0]
            offset += 2
            ancount = struct.unpack('!H', self.raw[offset:offset+2])[0]
            offset += 2
            nscount = struct.unpack('!H', self.raw[offset:offset+2])[0]
            offset += 2
            arcount = struct.unpack('!H', self.raw[offset:offset+2])[0]
            offset += 2
            
            # Questions
            for _ in range(qdcount):
                domain, offset = self._decode_domain(offset)
                qtype = struct.unpack('!H', self.raw[offset:offset+2])[0]
                offset += 2
                qclass = struct.unpack('!H', self.raw[offset:offset+2])[0]
                offset += 2
                
                self.questions.append({
                    'domain': domain,
                    'type': qtype,
                    'class': qclass
                })
            
            # Answers
            for _ in range(ancount):
                answer, offset = self._parse_rr(offset)
                self.answers.append(answer)
            
            # Authority
            for _ in range(nscount):
                auth, offset = self._parse_rr(offset)
                self.authorities.append(auth)
            
            # Additional
            for _ in range(arcount):
                add, offset = self._parse_rr(offset)
                self.additionals.append(add)
        
        except Exception as e:
            logger.error(f"DNS parse error: {e}")
    
    def _decode_domain(self, offset: int) -> tuple:
        """Decode domain name from DNS packet"""
        labels = []
        
        while True:
            length = self.raw[offset]
            
            if length == 0:
                offset += 1
                break
            
            if (length & 0xC0) == 0xC0:
                # Compression pointer
                pointer = struct.unpack('!H', self.raw[offset:offset+2])[0] & 0x3FFF
                domain, _ = self._decode_domain(pointer)
                offset += 2
                return domain, offset
            
            offset += 1
            labels.append(self.raw[offset:offset+length].decode('ascii'))
            offset += length
        
        return '.'.join(labels), offset
    
    def _parse_rr(self, offset: int) -> tuple:
        """Parse resource record"""
        domain, offset = self._decode_domain(offset)
        
        rtype = struct.unpack('!H', self.raw[offset:offset+2])[0]
        offset += 2
        rclass = struct.unpack('!H', self.raw[offset:offset+2])[0]
        offset += 2
        ttl = struct.unpack('!I', self.raw[offset:offset+4])[0]
        offset += 4
        rdlength = struct.unpack('!H', self.raw[offset:offset+2])[0]
        offset += 2
        
        rdata = self.raw[offset:offset+rdlength]
        offset += rdlength
        
        # Parse rdata based on type
        parsed_data = self._parse_rdata(rtype, rdata)
        
        return {
            'name': domain,
            'type': rtype,
            'class': rclass,
            'ttl': ttl,
            'data': parsed_data
        }, offset
    
    def _parse_rdata(self, rtype: int, rdata: bytes):
        """Parse rdata based on record type"""
        try:
            if rtype == DNSQueryType.A:
                # IPv4 address
                return socket.inet_ntoa(rdata)
            elif rtype == DNSQueryType.AAAA:
                # IPv6 address
                return socket.inet_ntop(socket.AF_INET6, rdata)
            elif rtype == DNSQueryType.CNAME:
                # Domain name
                domain, _ = self._decode_domain(0)
                return domain
            elif rtype == DNSQueryType.MX:
                # Mail exchange
                preference = struct.unpack('!H', rdata[:2])[0]
                domain, _ = self._decode_domain(2)
                return f"{preference} {domain}"
            elif rtype == DNSQueryType.TXT:
                # Text
                return rdata[1:].decode('utf-8', errors='ignore')
            else:
                return rdata.hex()
        except:
            return rdata.hex()
    
    def get_addresses(self) -> List[str]:
        """Get all IP addresses from answer section"""
        addresses = []
        
        for answer in self.answers:
            if answer['type'] in [DNSQueryType.A, DNSQueryType.AAAA]:
                addresses.append(answer['data'])
        
        return addresses
    
    def __repr__(self):
        return f"<DNSResponse id={self.query_id} answers={len(self.answers)}>"

class DNSClient:
    """DNS Client"""
    
    def __init__(self, udp_send_callback, default_server: str = '8.8.8.8'):
        self.udp_send = udp_send_callback
        self.default_server = default_server
        self.pending_queries = {}  # query_id -> (query, timestamp, callback)
        self.timeout = 5.0
    
    def query(self, domain: str, qtype: int = DNSQueryType.A,
             src_ip: str = None, interface: str = None,
             dns_server: str = None, callback=None) -> Optional[int]:
        """Send DNS query"""
        
        if not dns_server:
            dns_server = self.default_server
        
        # Build query
        query = DNSQuery(domain, qtype)
        packet = query.build()
        
        # Build UDP packet (simplified)
        src_port = random.randint(10000, 65535)
        
        # Send via UDP (port 53)
        self.udp_send(packet, src_ip, src_port, dns_server, 53, interface)
        
        # Track query
        self.pending_queries[query.query_id] = {
            'query': query,
            'timestamp': time.time(),
            'callback': callback
        }
        
        logger.info(f"DNS query: {domain} ({qtype}) -> {dns_server}")
        
        return query.query_id
    
    def handle_response(self, response_data: bytes):
        """Handle DNS response"""
        try:
            response = DNSResponse(response_data)
            
            if response.query_id in self.pending_queries:
                query_info = self.pending_queries.pop(response.query_id)
                
                logger.info(f"DNS response: {response.query_id} - {len(response.answers)} answers")
                
                if query_info['callback']:
                    query_info['callback'](response)
                
                return response
        
        except Exception as e:
            logger.error(f"DNS response handling error: {e}")
        
        return None
    
    def check_timeouts(self):
        """Check for timed out queries"""
        now = time.time()
        
        timed_out = [
            qid for qid, info in self.pending_queries.items()
            if now - info['timestamp'] > self.timeout
        ]
        
        for qid in timed_out:
            logger.warning(f"DNS query timeout: {qid}")
            del self.pending_queries[qid]
    
    def resolve(self, domain: str, timeout: float = 5.0) -> List[str]:
        """Synchronous resolve (blocking)"""
        result = []
        event = {'done': False}
        
        def callback(response):
            result.extend(response.get_addresses())
            event['done'] = True
        
        self.query(domain, callback=callback)
        
        start = time.time()
        while not event['done'] and time.time() - start < timeout:
            time.sleep(0.01)
        
        return result

# Test
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("DNS Client module loaded")
    print("Usage:")
    print("  dns = DNSClient(udp_send_callback)")
    print("  dns.query('example.com', DNSQueryType.A, src_ip='192.168.1.1')")
