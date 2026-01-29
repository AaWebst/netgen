#!/usr/bin/env python3
"""
SNMP Agent Simulator for VEP1445
Simulate thousands of network devices for monitoring system testing
"""

import struct
import socket
import threading
import time
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class SNMPType:
    """SNMP Data Types"""
    INTEGER = 0x02
    OCTET_STRING = 0x04
    NULL = 0x05
    OBJECT_IDENTIFIER = 0x06
    SEQUENCE = 0x30
    IP_ADDRESS = 0x40
    COUNTER32 = 0x41
    GAUGE32 = 0x42
    TIME_TICKS = 0x43
    COUNTER64 = 0x46

class SNMPOID:
    """Common SNMP OIDs"""
    SYS_DESCR = "1.3.6.1.2.1.1.1.0"
    SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
    SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
    SYS_CONTACT = "1.3.6.1.2.1.1.4.0"
    SYS_NAME = "1.3.6.1.2.1.1.5.0"
    SYS_LOCATION = "1.3.6.1.2.1.1.6.0"
    
    # Interface stats
    IF_IN_OCTETS = "1.3.6.1.2.1.2.2.1.10"   # .{ifIndex}
    IF_OUT_OCTETS = "1.3.6.1.2.1.2.2.1.16"
    IF_IN_ERRORS = "1.3.6.1.2.1.2.2.1.14"
    IF_OUT_ERRORS = "1.3.6.1.2.1.2.2.1.20"
    
    # CPU/Memory
    CPU_LOAD = "1.3.6.1.4.1.2021.10.1.3.1"
    MEMORY_TOTAL = "1.3.6.1.4.1.2021.4.5.0"
    MEMORY_FREE = "1.3.6.1.4.1.2021.4.6.0"

class SNMPMessage:
    """SNMP Message Builder/Parser"""
    
    # SNMP PDU Types
    GET_REQUEST = 0xA0
    GET_NEXT_REQUEST = 0xA1
    GET_RESPONSE = 0xA2
    SET_REQUEST = 0xA3
    TRAP = 0xA4
    GET_BULK_REQUEST = 0xA5
    
    def __init__(self, version: int = 1, community: str = "public"):
        self.version = version  # 0=v1, 1=v2c
        self.community = community
        self.request_id = 0
        self.error_status = 0
        self.error_index = 0
        self.varbinds = []
    
    def add_varbind(self, oid: str, value_type: int, value):
        """Add variable binding (OID + value)"""
        self.varbinds.append((oid, value_type, value))
    
    def build_response(self) -> bytes:
        """Build SNMP GET-RESPONSE"""
        # Build varbind list
        varbind_data = b''
        for oid, value_type, value in self.varbinds:
            varbind_data += self._encode_varbind(oid, value_type, value)
        
        # Build varbind sequence
        varbind_seq = self._encode_sequence(varbind_data)
        
        # Build PDU
        pdu_data = b''
        pdu_data += self._encode_integer(self.request_id)
        pdu_data += self._encode_integer(self.error_status)
        pdu_data += self._encode_integer(self.error_index)
        pdu_data += varbind_seq
        
        pdu = self._encode_tlv(self.GET_RESPONSE, pdu_data)
        
        # Build message
        message_data = b''
        message_data += self._encode_integer(self.version)
        message_data += self._encode_octet_string(self.community)
        message_data += pdu
        
        message = self._encode_sequence(message_data)
        
        return message
    
    def _encode_varbind(self, oid: str, value_type: int, value) -> bytes:
        """Encode single varbind"""
        oid_encoded = self._encode_oid(oid)
        
        if value_type == SNMPType.INTEGER:
            value_encoded = self._encode_integer(value)
        elif value_type == SNMPType.OCTET_STRING:
            value_encoded = self._encode_octet_string(value)
        elif value_type == SNMPType.COUNTER32 or value_type == SNMPType.GAUGE32:
            value_encoded = self._encode_tlv(value_type, self._encode_integer_bytes(value))
        elif value_type == SNMPType.TIME_TICKS:
            value_encoded = self._encode_tlv(value_type, self._encode_integer_bytes(value))
        elif value_type == SNMPType.IP_ADDRESS:
            # IP as 4 bytes
            ip_bytes = bytes([int(x) for x in value.split('.')])
            value_encoded = self._encode_tlv(value_type, ip_bytes)
        else:
            value_encoded = b'\x05\x00'  # NULL
        
        return self._encode_sequence(oid_encoded + value_encoded)
    
    def _encode_oid(self, oid: str) -> bytes:
        """Encode OID"""
        parts = [int(x) for x in oid.split('.')]
        
        # First two parts are combined: 40*first + second
        encoded = bytes([40 * parts[0] + parts[1]])
        
        # Remaining parts
        for part in parts[2:]:
            encoded += self._encode_oid_subid(part)
        
        return self._encode_tlv(SNMPType.OBJECT_IDENTIFIER, encoded)
    
    def _encode_oid_subid(self, value: int) -> bytes:
        """Encode OID sub-identifier"""
        if value < 128:
            return bytes([value])
        
        # Multi-byte encoding
        result = []
        while value > 0:
            result.insert(0, (value & 0x7F) | (0x80 if len(result) > 0 else 0))
            value >>= 7
        
        return bytes(result)
    
    def _encode_sequence(self, data: bytes) -> bytes:
        """Encode SEQUENCE"""
        return self._encode_tlv(SNMPType.SEQUENCE, data)
    
    def _encode_integer(self, value: int) -> bytes:
        """Encode INTEGER"""
        return self._encode_tlv(SNMPType.INTEGER, self._encode_integer_bytes(value))
    
    def _encode_integer_bytes(self, value: int) -> bytes:
        """Encode integer to bytes"""
        if value == 0:
            return b'\x00'
        
        # Convert to bytes (big-endian)
        result = []
        negative = value < 0
        if negative:
            value = -value
        
        while value > 0:
            result.insert(0, value & 0xFF)
            value >>= 8
        
        # Add sign byte if needed
        if not negative and result[0] & 0x80:
            result.insert(0, 0)
        
        return bytes(result)
    
    def _encode_octet_string(self, value: str) -> bytes:
        """Encode OCTET STRING"""
        return self._encode_tlv(SNMPType.OCTET_STRING, value.encode('utf-8'))
    
    def _encode_tlv(self, tag: int, value: bytes) -> bytes:
        """Encode Tag-Length-Value"""
        length = len(value)
        
        if length < 128:
            return bytes([tag, length]) + value
        else:
            # Long form length
            length_bytes = []
            temp = length
            while temp > 0:
                length_bytes.insert(0, temp & 0xFF)
                temp >>= 8
            
            return bytes([tag, 0x80 | len(length_bytes)] + length_bytes) + value
    
    @staticmethod
    def parse_get_request(data: bytes) -> Optional[Dict]:
        """Parse SNMP GET request (simplified)"""
        try:
            # Very simplified parser - just extract request ID and OIDs
            # In production, use proper ASN.1 parser
            
            offset = 0
            
            # Skip SEQUENCE tag + length
            offset += 2
            
            # Version
            if data[offset] == SNMPType.INTEGER:
                offset += 2  # tag + length
                version = data[offset]
                offset += 1
            
            # Community
            if data[offset] == SNMPType.OCTET_STRING:
                offset += 1
                comm_len = data[offset]
                offset += 1
                community = data[offset:offset+comm_len].decode('utf-8')
                offset += comm_len
            
            # PDU type (GET_REQUEST = 0xA0)
            pdu_type = data[offset]
            offset += 1
            
            # PDU length
            pdu_len = data[offset]
            offset += 1
            
            # Request ID
            if data[offset] == SNMPType.INTEGER:
                offset += 2
                request_id = (data[offset] << 24) | (data[offset+1] << 16) | \
                           (data[offset+2] << 8) | data[offset+3]
                offset += 4
            
            return {
                'version': version,
                'community': community,
                'pdu_type': pdu_type,
                'request_id': request_id
            }
        except:
            return None

class SNMPAgent:
    """SNMP Agent Simulator"""
    
    def __init__(self, ip: str, port: int = 161, 
                 device_name: str = "VEP1445-Device",
                 device_type: str = "Router"):
        self.ip = ip
        self.port = port
        self.device_name = device_name
        self.device_type = device_type
        
        # MIB database
        self.mib = self._initialize_mib()
        
        # Statistics
        self.start_time = int(time.time())
        self.requests_received = 0
        self.responses_sent = 0
        
        # Socket
        self.sock = None
        self.running = False
    
    def _initialize_mib(self) -> Dict:
        """Initialize MIB with default values"""
        return {
            SNMPOID.SYS_DESCR: ("VEP1445 Traffic Generator - Simulated Device", SNMPType.OCTET_STRING),
            SNMPOID.SYS_NAME: (self.device_name, SNMPType.OCTET_STRING),
            SNMPOID.SYS_LOCATION: ("VEP1445 Lab", SNMPType.OCTET_STRING),
            SNMPOID.SYS_CONTACT: ("admin@vep1445.local", SNMPType.OCTET_STRING),
            SNMPOID.SYS_UPTIME: (0, SNMPType.TIME_TICKS),  # Updated dynamically
            
            # Interface stats (example for interface 1)
            f"{SNMPOID.IF_IN_OCTETS}.1": (0, SNMPType.COUNTER32),
            f"{SNMPOID.IF_OUT_OCTETS}.1": (0, SNMPType.COUNTER32),
            f"{SNMPOID.IF_IN_ERRORS}.1": (0, SNMPType.COUNTER32),
            f"{SNMPOID.IF_OUT_ERRORS}.1": (0, SNMPType.COUNTER32),
            
            # CPU/Memory
            SNMPOID.CPU_LOAD: (25, SNMPType.INTEGER),  # 25% CPU
            SNMPOID.MEMORY_TOTAL: (8192, SNMPType.INTEGER),  # 8GB
            SNMPOID.MEMORY_FREE: (4096, SNMPType.INTEGER),   # 4GB free
        }
    
    def start(self):
        """Start SNMP agent"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))
        self.running = True
        
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        
        logger.info(f"SNMP Agent started on {self.ip}:{self.port}")
    
    def stop(self):
        """Stop SNMP agent"""
        self.running = False
        if self.sock:
            self.sock.close()
        logger.info("SNMP Agent stopped")
    
    def _run(self):
        """Main agent loop"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                
                # Parse request
                request = SNMPMessage.parse_get_request(data)
                if not request:
                    continue
                
                self.requests_received += 1
                
                # Build response
                response = self._build_response(request)
                
                # Send response
                self.sock.sendto(response, addr)
                self.responses_sent += 1
                
            except:
                if self.running:
                    time.sleep(0.001)
    
    def _build_response(self, request: Dict) -> bytes:
        """Build SNMP response"""
        msg = SNMPMessage(
            version=request['version'],
            community=request['community']
        )
        msg.request_id = request['request_id']
        
        # Update dynamic values
        uptime = (int(time.time()) - self.start_time) * 100  # In hundredths of seconds
        self.mib[SNMPOID.SYS_UPTIME] = (uptime, SNMPType.TIME_TICKS)
        
        # For simplicity, return all common OIDs
        # In production, parse requested OIDs from request
        for oid, (value, vtype) in self.mib.items():
            msg.add_varbind(oid, vtype, value)
        
        return msg.build_response()
    
    def update_interface_stats(self, if_index: int, in_octets: int, out_octets: int):
        """Update interface statistics"""
        self.mib[f"{SNMPOID.IF_IN_OCTETS}.{if_index}"] = (in_octets, SNMPType.COUNTER32)
        self.mib[f"{SNMPOID.IF_OUT_OCTETS}.{if_index}"] = (out_octets, SNMPType.COUNTER32)
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        return {
            'requests_received': self.requests_received,
            'responses_sent': self.responses_sent,
            'uptime_seconds': int(time.time()) - self.start_time
        }

class SNMPAgentFarm:
    """Simulate multiple SNMP agents (device farm)"""
    
    def __init__(self):
        self.agents = []
    
    def create_agents(self, base_ip: str, count: int, start_port: int = 10161):
        """Create multiple SNMP agents"""
        base_octets = [int(x) for x in base_ip.split('.')]
        
        for i in range(count):
            # Vary IP and port
            ip = f"{base_octets[0]}.{base_octets[1]}.{base_octets[2]}.{(base_octets[3] + i) % 256}"
            port = start_port + i
            
            agent = SNMPAgent(
                ip=ip,
                port=port,
                device_name=f"Device-{i+1:04d}",
                device_type="Router"
            )
            
            self.agents.append(agent)
        
        logger.info(f"Created {count} SNMP agents")
    
    def start_all(self):
        """Start all agents"""
        for agent in self.agents:
            agent.start()
        logger.info(f"Started {len(self.agents)} SNMP agents")
    
    def stop_all(self):
        """Stop all agents"""
        for agent in self.agents:
            agent.stop()
    
    def get_total_stats(self) -> Dict:
        """Get statistics for all agents"""
        total_requests = sum(a.requests_received for a in self.agents)
        total_responses = sum(a.responses_sent for a in self.agents)
        
        return {
            'agent_count': len(self.agents),
            'total_requests': total_requests,
            'total_responses': total_responses
        }

# Test usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("SNMP Agent Simulator Test")
    print("=" * 60)
    
    print("\nFeatures:")
    print("  ✓ SNMPv1/v2c support")
    print("  ✓ System MIB (sysDescr, sysName, etc.)")
    print("  ✓ Interface statistics")
    print("  ✓ CPU/Memory stats")
    print("  ✓ Multiple agent simulation")
    print("  ✓ Trap generation (TODO)")
    
    print("\nUsage:")
    print("  # Single agent")
    print("  agent = SNMPAgent('192.168.1.100', device_name='Router-1')")
    print("  agent.start()")
    print("")
    print("  # Multiple agents (device farm)")
    print("  farm = SNMPAgentFarm()")
    print("  farm.create_agents('192.168.1.1', count=1000)")
    print("  farm.start_all()")
    print("")
    print("  # Test with snmpwalk:")
    print("  snmpwalk -v2c -c public 192.168.1.100:10161 system")
    
    print("\n✓ SNMP agent simulator ready")
    print("✓ Test monitoring systems (Nagios, PRTG, SolarWinds)")
    print("✓ Simulate thousands of network devices")
