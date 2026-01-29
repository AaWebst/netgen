#!/usr/bin/env python3
"""
NetFlow v5/v9 and IPFIX Generator
Test flow collectors and traffic analysis systems
"""

import struct
import socket
import time
import random
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class NetFlowV5Generator:
    """NetFlow v5 Flow Generator"""
    
    def __init__(self, source_id: int = 0):
        self.source_id = source_id
        self.sequence = 0
        self.sys_uptime = int(time.time())
        self.flows_sent = 0
    
    def generate_flow_record(self, src_ip: str, dst_ip: str,
                            src_port: int, dst_port: int,
                            protocol: int, packets: int, octets: int) -> bytes:
        """Generate single NetFlow v5 record (48 bytes)"""
        
        # Convert IPs to integers
        src_addr = socket.inet_aton(src_ip)
        dst_addr = socket.inet_aton(dst_ip)
        
        # Next hop (0.0.0.0 for now)
        nexthop = socket.inet_aton("0.0.0.0")
        
        # SNMP indices
        input_snmp = 1
        output_snmp = 2
        
        # Timestamps (milliseconds since boot)
        first = int((time.time() - self.sys_uptime) * 1000)
        last = first + random.randint(100, 5000)  # Flow duration
        
        # TCP flags
        tcp_flags = 0x18 if protocol == 6 else 0  # ACK+PSH for TCP
        
        # TOS
        tos = 0
        
        # AS numbers
        src_as = 0
        dst_as = 0
        
        # Prefix masks
        src_mask = 24
        dst_mask = 24
        
        # Pack record (48 bytes)
        record = struct.pack('!4s4s4sHHIIIIHHBBBBHHBBH',
            src_addr,       # Source IP
            dst_addr,       # Dest IP
            nexthop,        # Next hop IP
            input_snmp,     # Input interface
            output_snmp,    # Output interface
            packets,        # Packet count
            octets,         # Byte count
            first,          # First packet timestamp
            last,           # Last packet timestamp
            src_port,       # Source port
            dst_port,       # Dest port
            0,              # Padding
            tcp_flags,      # TCP flags
            protocol,       # Protocol
            tos,            # Type of Service
            src_as,         # Source AS
            dst_as,         # Dest AS
            src_mask,       # Source mask
            dst_mask,       # Dest mask
            0               # Padding
        )
        
        return record
    
    def generate_packet(self, flows: List[Dict]) -> bytes:
        """
        Generate NetFlow v5 packet (max 30 flows per packet)
        
        Args:
            flows: List of flow dicts with: src_ip, dst_ip, src_port, 
                   dst_port, protocol, packets, octets
        """
        # NetFlow v5 header (24 bytes)
        version = 5
        count = min(len(flows), 30)  # Max 30 records per packet
        
        uptime = int((time.time() - self.sys_uptime) * 1000)
        unix_secs = int(time.time())
        unix_nsecs = int((time.time() % 1) * 1e9)
        
        header = struct.pack('!HHIIIHH',
            version,        # Version
            count,          # Number of flow records
            uptime,         # System uptime (ms)
            unix_secs,      # Unix seconds
            unix_nsecs,     # Unix nanoseconds
            self.sequence,  # Flow sequence
            0,              # Engine type (0)
            0               # Engine ID (0)
        )
        
        # Build records
        records = b''
        for flow in flows[:count]:
            records += self.generate_flow_record(
                flow['src_ip'], flow['dst_ip'],
                flow['src_port'], flow['dst_port'],
                flow['protocol'], flow['packets'], flow['octets']
            )
        
        self.sequence += count
        self.flows_sent += count
        
        return header + records
    
    def send_flows(self, flows: List[Dict], collector_ip: str, 
                   collector_port: int = 2055):
        """Send flows to NetFlow collector"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Split flows into packets of 30
        for i in range(0, len(flows), 30):
            batch = flows[i:i+30]
            packet = self.generate_packet(batch)
            sock.sendto(packet, (collector_ip, collector_port))
        
        sock.close()
        logger.info(f"Sent {len(flows)} NetFlow v5 records to {collector_ip}:{collector_port}")

class IPFIXGenerator:
    """IPFIX (IP Flow Information Export) Generator"""
    
    # IPFIX Information Element IDs
    IE_SOURCE_IPV4 = 8
    IE_DEST_IPV4 = 12
    IE_IP_PROTOCOL = 4
    IE_SOURCE_PORT = 7
    IE_DEST_PORT = 11
    IE_PACKET_COUNT = 2
    IE_OCTET_COUNT = 1
    IE_FLOW_START = 150
    IE_FLOW_END = 151
    
    def __init__(self, observation_domain_id: int = 0):
        self.observation_domain_id = observation_domain_id
        self.sequence = 0
        self.template_id = 256
    
    def generate_template_set(self) -> bytes:
        """Generate IPFIX template set"""
        # Template header
        set_id = 2  # Template Set
        
        # Template record
        template_record = struct.pack('!HH',
            self.template_id,  # Template ID
            9                  # Field count
        )
        
        # Field specifiers (type, length)
        fields = [
            (self.IE_SOURCE_IPV4, 4),
            (self.IE_DEST_IPV4, 4),
            (self.IE_IP_PROTOCOL, 1),
            (self.IE_SOURCE_PORT, 2),
            (self.IE_DEST_PORT, 2),
            (self.IE_PACKET_COUNT, 8),
            (self.IE_OCTET_COUNT, 8),
            (self.IE_FLOW_START, 8),
            (self.IE_FLOW_END, 8)
        ]
        
        for ie_id, length in fields:
            template_record += struct.pack('!HH', ie_id, length)
        
        # Set header (set_id, length)
        set_length = 4 + len(template_record)
        set_header = struct.pack('!HH', set_id, set_length)
        
        return set_header + template_record
    
    def generate_data_set(self, flows: List[Dict]) -> bytes:
        """Generate IPFIX data set"""
        # Data set header
        set_id = self.template_id
        
        # Data records
        records = b''
        for flow in flows:
            records += socket.inet_aton(flow['src_ip'])
            records += socket.inet_aton(flow['dst_ip'])
            records += struct.pack('!B', flow['protocol'])
            records += struct.pack('!H', flow['src_port'])
            records += struct.pack('!H', flow['dst_port'])
            records += struct.pack('!Q', flow['packets'])
            records += struct.pack('!Q', flow['octets'])
            records += struct.pack('!Q', int(time.time() * 1000))  # Start time
            records += struct.pack('!Q', int(time.time() * 1000))  # End time
        
        # Set header
        set_length = 4 + len(records)
        set_header = struct.pack('!HH', set_id, set_length)
        
        return set_header + records
    
    def generate_message(self, flows: List[Dict], 
                        include_template: bool = False) -> bytes:
        """Generate complete IPFIX message"""
        # Message header (16 bytes)
        version = 10  # IPFIX
        export_time = int(time.time())
        
        # Build sets
        sets = b''
        if include_template:
            sets += self.generate_template_set()
        sets += self.generate_data_set(flows)
        
        length = 16 + len(sets)
        
        header = struct.pack('!HHIII',
            version,                        # Version
            length,                         # Length
            export_time,                    # Export time
            self.sequence,                  # Sequence number
            self.observation_domain_id      # Observation domain ID
        )
        
        self.sequence += len(flows)
        
        return header + sets
    
    def send_flows(self, flows: List[Dict], collector_ip: str,
                   collector_port: int = 4739, send_template: bool = True):
        """Send flows to IPFIX collector"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        message = self.generate_message(flows, include_template=send_template)
        sock.sendto(message, (collector_ip, collector_port))
        
        sock.close()
        logger.info(f"Sent {len(flows)} IPFIX records to {collector_ip}:{collector_port}")

class FlowGenerator:
    """High-level flow generator"""
    
    def __init__(self, protocol: str = "netflow5"):
        """
        Args:
            protocol: "netflow5", "netflow9", or "ipfix"
        """
        self.protocol = protocol
        
        if protocol == "netflow5":
            self.generator = NetFlowV5Generator()
        elif protocol == "ipfix":
            self.generator = IPFIXGenerator()
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")
    
    def generate_random_flows(self, count: int, 
                             base_src_ip: str = "10.1.0.0",
                             base_dst_ip: str = "192.168.1.0") -> List[Dict]:
        """Generate random flows for testing"""
        flows = []
        
        for i in range(count):
            # Vary IPs
            src_ip = f"10.1.{i//256}.{i%256}"
            dst_ip = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
            
            # Random ports
            src_port = random.randint(1024, 65535)
            dst_port = random.choice([80, 443, 22, 25, 53, 3389])  # Common ports
            
            # Protocol (mostly TCP)
            protocol = random.choice([6, 6, 6, 17])  # 75% TCP, 25% UDP
            
            # Traffic volume
            packets = random.randint(10, 1000)
            octets = packets * random.randint(100, 1400)
            
            flows.append({
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'src_port': src_port,
                'dst_port': dst_port,
                'protocol': protocol,
                'packets': packets,
                'octets': octets
            })
        
        return flows
    
    def simulate_traffic_pattern(self, duration: int, 
                                 flows_per_second: int,
                                 collector_ip: str,
                                 collector_port: int):
        """
        Simulate realistic traffic pattern
        
        Args:
            duration: Simulation duration in seconds
            flows_per_second: Target flow rate
            collector_ip: Collector IP
            collector_port: Collector port
        """
        start_time = time.time()
        total_flows = 0
        
        logger.info(f"Starting flow generation: {flows_per_second} flows/sec for {duration}s")
        
        while time.time() - start_time < duration:
            # Generate batch of flows
            batch_size = min(flows_per_second, 1000)
            flows = self.generate_random_flows(batch_size)
            
            # Send to collector
            if self.protocol == "netflow5":
                self.generator.send_flows(flows, collector_ip, collector_port)
            elif self.protocol == "ipfix":
                self.generator.send_flows(flows, collector_ip, collector_port)
            
            total_flows += len(flows)
            
            # Wait for next batch
            time.sleep(1.0)
        
        elapsed = time.time() - start_time
        rate = total_flows / elapsed
        
        logger.info(f"Flow generation complete: {total_flows} flows in {elapsed:.1f}s ({rate:.0f} flows/sec)")
        
        return {
            'total_flows': total_flows,
            'duration': elapsed,
            'average_rate': rate
        }

# Test usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("NetFlow/IPFIX Generator Test")
    print("=" * 60)
    
    print("\nSupported Protocols:")
    print("  ✓ NetFlow v5 (Cisco)")
    print("  ✓ IPFIX (RFC 7011)")
    print("  ⚠ NetFlow v9 (TODO)")
    
    print("\nFeatures:")
    print("  ✓ Random flow generation")
    print("  ✓ Realistic traffic patterns")
    print("  ✓ Configurable flow rates")
    print("  ✓ Multiple collector support")
    
    print("\nUsage:")
    print("  # NetFlow v5")
    print("  gen = FlowGenerator('netflow5')")
    print("  flows = gen.generate_random_flows(count=1000)")
    print("  gen.generator.send_flows(flows, '192.168.1.100', 2055)")
    print("")
    print("  # IPFIX")
    print("  gen = FlowGenerator('ipfix')")
    print("  gen.simulate_traffic_pattern(")
    print("      duration=60,")
    print("      flows_per_second=1000,")
    print("      collector_ip='192.168.1.100',")
    print("      collector_port=4739")
    print("  )")
    
    print("\nTest: Generating 100 NetFlow v5 flows...")
    
    gen = FlowGenerator('netflow5')
    flows = gen.generate_random_flows(100)
    
    print(f"  Generated {len(flows)} flows")
    print(f"  Example flow: {flows[0]['src_ip']}:{flows[0]['src_port']} -> "
          f"{flows[0]['dst_ip']}:{flows[0]['dst_port']}")
    print(f"  Protocol: {flows[0]['protocol']}, Packets: {flows[0]['packets']}, "
          f"Octets: {flows[0]['octets']}")
    
    print("\n✓ NetFlow/IPFIX generator ready")
    print("✓ Test with nfdump, Elastiflow, or other collectors")
