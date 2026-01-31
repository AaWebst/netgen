#!/usr/bin/env python3
"""
BGP Route Injection for VEP1445
Inject routes, test routing convergence, simulate BGP scenarios
"""

import struct
import socket
import time
import random
from typing import List, Dict, Optional
from enum import IntEnum
import logging

logger = logging.getLogger(__name__)

class BGPMessageType(IntEnum):
    """BGP Message Types"""
    OPEN = 1
    UPDATE = 2
    NOTIFICATION = 3
    KEEPALIVE = 4
    ROUTE_REFRESH = 5

class BGPPathAttribute(IntEnum):
    """BGP Path Attributes"""
    ORIGIN = 1
    AS_PATH = 2
    NEXT_HOP = 3
    MULTI_EXIT_DISC = 4
    LOCAL_PREF = 5
    ATOMIC_AGGREGATE = 6
    AGGREGATOR = 7
    COMMUNITY = 8
    MP_REACH_NLRI = 14
    MP_UNREACH_NLRI = 15

class BGPMessage:
    """BGP Message Builder"""
    
    MARKER = b'\xff' * 16  # 16 bytes of 0xFF
    
    def __init__(self, msg_type: int, data: bytes = b''):
        self.msg_type = msg_type
        self.data = data
    
    def build(self) -> bytes:
        """Build BGP message"""
        length = 19 + len(self.data)  # 16 (marker) + 2 (length) + 1 (type) + data
        
        message = self.MARKER
        message += struct.pack('!H', length)
        message += struct.pack('!B', self.msg_type)
        message += self.data
        
        return message
    
    @staticmethod
    def parse(data: bytes) -> Optional['BGPMessage']:
        """Parse BGP message"""
        if len(data) < 19:
            return None
        
        # Verify marker
        marker = data[0:16]
        if marker != BGPMessage.MARKER:
            logger.error("Invalid BGP marker")
            return None
        
        length = struct.unpack('!H', data[16:18])[0]
        msg_type = data[18]
        
        if len(data) < length:
            return None
        
        msg_data = data[19:length]
        
        return BGPMessage(msg_type, msg_data)

class BGPOpen:
    """BGP OPEN Message"""
    
    def __init__(self, my_asn: int, router_id: str, hold_time: int = 180):
        self.version = 4
        self.my_asn = my_asn
        self.hold_time = hold_time
        self.router_id = router_id
        self.capabilities = []
    
    def add_capability(self, cap_code: int, cap_value: bytes):
        """Add BGP capability"""
        self.capabilities.append((cap_code, cap_value))
    
    def build(self) -> bytes:
        """Build OPEN message data"""
        # Build optional parameters (capabilities)
        opt_params = b''
        
        if self.capabilities:
            cap_data = b''
            for cap_code, cap_value in self.capabilities:
                cap_data += struct.pack('!BB', cap_code, len(cap_value))
                cap_data += cap_value
            
            # Parameter type 2 = Capabilities
            opt_params = struct.pack('!BB', 2, len(cap_data))
            opt_params += cap_data
        
        # Pack OPEN data
        data = struct.pack('!B', self.version)
        data += struct.pack('!H', self.my_asn)
        data += struct.pack('!H', self.hold_time)
        data += socket.inet_aton(self.router_id)
        data += struct.pack('!B', len(opt_params))
        data += opt_params
        
        return data

class BGPUpdate:
    """BGP UPDATE Message"""
    
    def __init__(self):
        self.withdrawn_routes = []  # List of (prefix, length) tuples
        self.path_attributes = []   # List of (attr_type, attr_value) tuples
        self.nlri = []              # Network Layer Reachability Information
    
    def add_withdrawn_route(self, prefix: str, prefix_len: int):
        """Add withdrawn route"""
        self.withdrawn_routes.append((prefix, prefix_len))
    
    def add_path_attribute(self, attr_type: int, attr_value: bytes, 
                          optional: bool = False, transitive: bool = True):
        """Add path attribute"""
        flags = 0
        if optional:
            flags |= 0x80
        if transitive:
            flags |= 0x40
        
        self.path_attributes.append((flags, attr_type, attr_value))
    
    def add_nlri(self, prefix: str, prefix_len: int):
        """Add advertised route (NLRI)"""
        self.nlri.append((prefix, prefix_len))
    
    def build(self) -> bytes:
        """Build UPDATE message data"""
        data = b''
        
        # Withdrawn routes
        withdrawn = b''
        for prefix, prefix_len in self.withdrawn_routes:
            withdrawn += self._encode_prefix(prefix, prefix_len)
        
        data += struct.pack('!H', len(withdrawn))
        data += withdrawn
        
        # Path attributes
        path_attrs = b''
        for flags, attr_type, attr_value in self.path_attributes:
            # Extended length if value > 255 bytes
            if len(attr_value) > 255:
                flags |= 0x10  # Extended length
                path_attrs += struct.pack('!BBH', flags, attr_type, len(attr_value))
            else:
                path_attrs += struct.pack('!BBB', flags, attr_type, len(attr_value))
            path_attrs += attr_value
        
        data += struct.pack('!H', len(path_attrs))
        data += path_attrs
        
        # NLRI
        for prefix, prefix_len in self.nlri:
            data += self._encode_prefix(prefix, prefix_len)
        
        return data
    
    def _encode_prefix(self, prefix: str, prefix_len: int) -> bytes:
        """Encode IP prefix"""
        # Pack prefix length
        encoded = struct.pack('!B', prefix_len)
        
        # Pack prefix bytes (only significant octets)
        octets_needed = (prefix_len + 7) // 8
        prefix_bytes = socket.inet_aton(prefix)
        encoded += prefix_bytes[:octets_needed]
        
        return encoded

class BGPSession:
    """BGP Session Manager"""
    
    def __init__(self, local_ip: str, local_asn: int, 
                 remote_ip: str, remote_asn: int,
                 router_id: str = None):
        self.local_ip = local_ip
        self.local_asn = local_asn
        self.remote_ip = remote_ip
        self.remote_asn = remote_asn
        self.router_id = router_id or local_ip
        
        self.state = 'IDLE'
        self.socket = None
        self.hold_time = 180
        self.keepalive_timer = self.hold_time // 3
        
        # Statistics
        self.routes_advertised = 0
        self.routes_withdrawn = 0
        self.updates_sent = 0
        self.keepalives_sent = 0
    
    def connect(self, port: int = 179) -> bool:
        """Establish TCP connection to BGP peer"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.remote_ip, port))
            self.state = 'CONNECT'
            logger.info(f"BGP: Connected to {self.remote_ip}:{port}")
            return True
        except Exception as e:
            logger.error(f"BGP connection failed: {e}")
            return False
    
    def send_open(self) -> bool:
        """Send BGP OPEN message"""
        try:
            bgp_open = BGPOpen(self.local_asn, self.router_id, self.hold_time)
            
            # Add capabilities
            # Capability 1: Multiprotocol (IPv4 unicast)
            mp_cap = struct.pack('!HBB', 1, 1, 1)  # AFI=1 (IPv4), SAFI=1 (unicast)
            bgp_open.add_capability(1, mp_cap)
            
            # Capability 2: Route Refresh
            bgp_open.add_capability(2, b'')
            
            # Capability 65: 4-byte ASN (if ASN > 65535)
            if self.local_asn > 65535:
                bgp_open.add_capability(65, struct.pack('!I', self.local_asn))
            
            open_data = bgp_open.build()
            message = BGPMessage(BGPMessageType.OPEN, open_data)
            
            self.socket.send(message.build())
            self.state = 'OPEN_SENT'
            logger.info(f"BGP: Sent OPEN (ASN {self.local_asn})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send OPEN: {e}")
            return False
    
    def send_keepalive(self) -> bool:
        """Send BGP KEEPALIVE"""
        try:
            message = BGPMessage(BGPMessageType.KEEPALIVE)
            self.socket.send(message.build())
            self.keepalives_sent += 1
            logger.debug("BGP: Sent KEEPALIVE")
            return True
        except Exception as e:
            logger.error(f"Failed to send KEEPALIVE: {e}")
            return False
    
    def advertise_routes(self, routes: List[Dict]) -> bool:
        """
        Advertise routes to BGP peer
        
        Args:
            routes: List of route dictionaries with:
                - prefix: IP prefix (e.g., "192.168.1.0")
                - prefix_len: Prefix length (e.g., 24)
                - next_hop: Next hop IP
                - as_path: List of AS numbers
                - local_pref: Local preference (optional)
        """
        try:
            update = BGPUpdate()
            
            # Group routes by next_hop for efficiency
            routes_by_nh = {}
            for route in routes:
                nh = route.get('next_hop', self.local_ip)
                routes_by_nh.setdefault(nh, []).append(route)
            
            for next_hop, nh_routes in routes_by_nh.items():
                update = BGPUpdate()
                
                # Add path attributes
                # ORIGIN (required)
                update.add_path_attribute(BGPPathAttribute.ORIGIN, b'\x00')  # IGP
                
                # AS_PATH (required)
                if nh_routes[0].get('as_path'):
                    as_path_data = self._build_as_path(nh_routes[0]['as_path'])
                    update.add_path_attribute(BGPPathAttribute.AS_PATH, as_path_data)
                else:
                    # Empty AS_PATH
                    update.add_path_attribute(BGPPathAttribute.AS_PATH, b'')
                
                # NEXT_HOP (required for IPv4)
                next_hop_data = socket.inet_aton(next_hop)
                update.add_path_attribute(BGPPathAttribute.NEXT_HOP, next_hop_data)
                
                # LOCAL_PREF (optional)
                if 'local_pref' in nh_routes[0]:
                    local_pref = struct.pack('!I', nh_routes[0]['local_pref'])
                    update.add_path_attribute(BGPPathAttribute.LOCAL_PREF, local_pref)
                
                # Add NLRI (advertised prefixes)
                for route in nh_routes:
                    update.add_nlri(route['prefix'], route['prefix_len'])
                    self.routes_advertised += 1
                
                # Send UPDATE
                update_data = update.build()
                message = BGPMessage(BGPMessageType.UPDATE, update_data)
                self.socket.send(message.build())
                self.updates_sent += 1
            
            logger.info(f"BGP: Advertised {len(routes)} routes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to advertise routes: {e}")
            return False
    
    def withdraw_routes(self, routes: List[Dict]) -> bool:
        """Withdraw routes from BGP peer"""
        try:
            update = BGPUpdate()
            
            for route in routes:
                update.add_withdrawn_route(route['prefix'], route['prefix_len'])
                self.routes_withdrawn += 1
            
            update_data = update.build()
            message = BGPMessage(BGPMessageType.UPDATE, update_data)
            self.socket.send(message.build())
            self.updates_sent += 1
            
            logger.info(f"BGP: Withdrew {len(routes)} routes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to withdraw routes: {e}")
            return False
    
    def _build_as_path(self, as_list: List[int]) -> bytes:
        """Build AS_PATH attribute"""
        # AS_SEQUENCE type
        as_path = struct.pack('!BB', 2, len(as_list))  # Type 2 = AS_SEQUENCE
        
        for asn in as_list:
            if asn > 65535:
                # 4-byte ASN
                as_path += struct.pack('!I', asn)
            else:
                # 2-byte ASN
                as_path += struct.pack('!H', asn)
        
        return as_path
    
    def close(self):
        """Close BGP session"""
        if self.socket:
            try:
                # Send NOTIFICATION (Cease)
                notify_data = struct.pack('!BB', 6, 0)  # Code 6 = Cease
                message = BGPMessage(BGPMessageType.NOTIFICATION, notify_data)
                self.socket.send(message.build())
            except:
                pass
            
            self.socket.close()
            self.socket = None
            self.state = 'IDLE'
            logger.info("BGP: Session closed")
    
    def get_stats(self) -> Dict:
        """Get BGP statistics"""
        return {
            'state': self.state,
            'routes_advertised': self.routes_advertised,
            'routes_withdrawn': self.routes_withdrawn,
            'updates_sent': self.updates_sent,
            'keepalives_sent': self.keepalives_sent
        }

class BGPTestScenario:
    """BGP Testing Scenarios"""
    
    @staticmethod
    def route_injection_test(session: BGPSession, num_routes: int = 1000,
                            base_prefix: str = "10.0.0.0") -> bool:
        """Inject large number of routes"""
        routes = []
        
        # Generate routes
        base_octets = [int(x) for x in base_prefix.split('.')]
        
        for i in range(num_routes):
            # Increment second octet
            octet2 = (base_octets[1] + (i // 256)) % 256
            octet3 = i % 256
            
            prefix = f"{base_octets[0]}.{octet2}.{octet3}.0"
            
            routes.append({
                'prefix': prefix,
                'prefix_len': 24,
                'next_hop': session.local_ip,
                'as_path': [session.local_asn],
                'local_pref': 100
            })
        
        logger.info(f"BGP Test: Injecting {num_routes} routes")
        return session.advertise_routes(routes)
    
    @staticmethod
    def convergence_test(session: BGPSession, routes: List[Dict],
                        advertise_delay: float = 0.1) -> float:
        """Test routing convergence time"""
        import time
        
        # Advertise routes with timing
        start_time = time.time()
        
        for route in routes:
            session.advertise_routes([route])
            time.sleep(advertise_delay)
        
        convergence_time = time.time() - start_time
        
        logger.info(f"BGP Convergence Test: {len(routes)} routes in {convergence_time:.2f}s")
        return convergence_time
    
    @staticmethod
    def route_flap_test(session: BGPSession, route: Dict, 
                       flap_count: int = 10, interval: float = 1.0):
        """Test route flapping (advertise/withdraw repeatedly)"""
        import time
        
        logger.info(f"BGP Flap Test: {flap_count} flaps of {route['prefix']}/{route['prefix_len']}")
        
        for i in range(flap_count):
            # Advertise
            session.advertise_routes([route])
            time.sleep(interval / 2)
            
            # Withdraw
            session.withdraw_routes([route])
            time.sleep(interval / 2)
        
        logger.info("BGP Flap Test complete")

# Test usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("BGP Route Injection Module Test")
    print("=" * 60)
    
    print("\nFeatures:")
    print("  ✓ BGP OPEN message")
    print("  ✓ BGP UPDATE (advertise/withdraw)")
    print("  ✓ BGP KEEPALIVE")
    print("  ✓ Route injection (1000s of routes)")
    print("  ✓ Convergence testing")
    print("  ✓ Route flapping simulation")
    print("  ✓ AS_PATH manipulation")
    
    print("\nUsage:")
    print("  # Create BGP session")
    print("  bgp = BGPSession('192.168.1.1', 65001, '192.168.1.2', 65002)")
    print("  bgp.connect()")
    print("  bgp.send_open()")
    print("")
    print("  # Advertise routes")
    print("  routes = [")
    print("      {'prefix': '10.1.0.0', 'prefix_len': 24, 'next_hop': '192.168.1.1'},")
    print("      {'prefix': '10.2.0.0', 'prefix_len': 24, 'next_hop': '192.168.1.1'}")
    print("  ]")
    print("  bgp.advertise_routes(routes)")
    print("")
    print("  # Test scenarios")
    print("  BGPTestScenario.route_injection_test(bgp, num_routes=10000)")
    print("  BGPTestScenario.convergence_test(bgp, routes)")
    
    print("\n✓ BGP module ready for routing tests")
