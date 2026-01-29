#!/usr/bin/env python3
"""
VEP1445 Traffic Generator - Main Module
Integrates all protocols and features
"""

import sys
import os

# Add all protocol paths
sys.path.insert(0, '/opt/vep1445-traffic-gen/protocols/tcp')
sys.path.insert(0, '/opt/vep1445-traffic-gen/protocols/http')
sys.path.insert(0, '/opt/vep1445-traffic-gen/protocols/dns')
sys.path.insert(0, '/opt/vep1445-traffic-gen/protocols/ipv6')
sys.path.insert(0, '/opt/vep1445-traffic-gen/protocols/sip')
sys.path.insert(0, '/opt/vep1445-traffic-gen/protocols/bgp')
sys.path.insert(0, '/opt/vep1445-traffic-gen/monitoring/snmp')
sys.path.insert(0, '/opt/vep1445-traffic-gen/monitoring/netflow')
sys.path.insert(0, '/opt/vep1445-traffic-gen/testing/qos')
sys.path.insert(0, '/opt/vep1445-traffic-gen/testing/impairments')
sys.path.insert(0, '/opt/vep1445-traffic-gen/testing/pcap')
sys.path.insert(0, '/opt/vep1445-traffic-gen/testing/imix')

# Import all components
try:
    from tcp_performance_optimized import TCPConnectionPoolOptimized, HighPerformanceTCPEngine
    TCP_AVAILABLE = True
except:
    TCP_AVAILABLE = False

try:
    from http_client import HTTPClient
    from tls_client import HTTPSClient
    from http2_client import HTTP2Client
    HTTP_AVAILABLE = True
except:
    HTTP_AVAILABLE = False

try:
    from dns_client import DNSClient
    DNS_AVAILABLE = True
except:
    DNS_AVAILABLE = False

try:
    from snmp_agent import SNMPAgent, SNMPAgentFarm
    SNMP_AVAILABLE = True
except:
    SNMP_AVAILABLE = False

try:
    from netflow_generator import FlowGenerator
    NETFLOW_AVAILABLE = True
except:
    NETFLOW_AVAILABLE = False

try:
    from qos_validation import QoSValidator
    QOS_AVAILABLE = True
except:
    QOS_AVAILABLE = False

try:
    from network_impairments import PacketImpairment
    IMPAIRMENTS_AVAILABLE = True
except:
    IMPAIRMENTS_AVAILABLE = False

import logging

logger = logging.getLogger(__name__)

class VEP1445Engine:
    """Main VEP1445 Traffic Generator Engine"""
    
    def __init__(self):
        self.version = "2.0.0"
        self.features = {
            'tcp': TCP_AVAILABLE,
            'http': HTTP_AVAILABLE,
            'dns': DNS_AVAILABLE,
            'snmp': SNMP_AVAILABLE,
            'netflow': NETFLOW_AVAILABLE,
            'qos': QOS_AVAILABLE,
            'impairments': IMPAIRMENTS_AVAILABLE
        }
        
        # Initialize components
        self.tcp_engine = None
        self.http_client = None
        self.dns_client = None
        self.snmp_farm = None
        self.netflow_gen = None
        
        logger.info(f"VEP1445 Engine v{self.version} initialized")
        logger.info(f"Available features: {sum(self.features.values())}/{len(self.features)}")
    
    def initialize(self):
        """Initialize all available components"""
        if TCP_AVAILABLE:
            self.tcp_engine = HighPerformanceTCPEngine()
            logger.info("✓ High-Performance TCP Engine initialized")
        
        if SNMP_AVAILABLE:
            self.snmp_farm = SNMPAgentFarm()
            logger.info("✓ SNMP Agent Farm ready")
        
        if NETFLOW_AVAILABLE:
            self.netflow_gen = FlowGenerator('netflow5')
            logger.info("✓ NetFlow Generator ready")
        
        return True
    
    def get_status(self):
        """Get engine status"""
        return {
            'version': self.version,
            'features': self.features,
            'tcp_engine': self.tcp_engine is not None,
            'snmp_farm': self.snmp_farm is not None,
            'netflow_gen': self.netflow_gen is not None
        }

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("VEP1445 Traffic Generator v2.0")
    print("=" * 60)
    
    engine = VEP1445Engine()
    engine.initialize()
    
    status = engine.get_status()
    print(f"\nStatus: {sum(status['features'].values())}/{len(status['features'])} features available")
    print("\nAvailable Features:")
    for feature, available in status['features'].items():
        icon = "✓" if available else "✗"
        print(f"  {icon} {feature.upper()}")
    
    print("\n" + "=" * 60)
    print("Ready for traffic generation!")
    print("=" * 60)
