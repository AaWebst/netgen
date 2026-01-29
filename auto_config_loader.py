#!/usr/bin/env python3
"""
VEP1445 Auto-Configuration Loader
Automatically detects interface IPs (DHCP or static) and generates profiles

NO MANUAL CONFIGURATION NEEDED!
"""

import subprocess
import re
import json
import yaml
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class InterfaceDetector:
    """Automatically detect interface configuration"""
    
    @staticmethod
    def get_interface_info(interface_name: str) -> Optional[Dict]:
        """
        Get interface information automatically
        Works with DHCP or static IPs
        """
        info = {
            'name': interface_name,
            'mac': None,
            'ipv4': None,
            'ipv4_cidr': None,
            'netmask': None,
            'network': None,
            'has_ip': False,
            'ipv6': None
        }
        
        try:
            # Get MAC address
            result = subprocess.run(['ip', 'link', 'show', interface_name],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                mac_match = re.search(r'link/ether ([0-9a-f:]+)', result.stdout)
                if mac_match:
                    info['mac'] = mac_match.group(1)
            
            # Get IPv4 address (works for both DHCP and static!)
            result = subprocess.run(['ip', '-4', 'addr', 'show', interface_name],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', result.stdout)
                if ip_match:
                    info['ipv4'] = ip_match.group(1)
                    cidr = int(ip_match.group(2))
                    info['ipv4_cidr'] = f"{info['ipv4']}/{cidr}"
                    info['has_ip'] = True
                    
                    # Calculate netmask from CIDR
                    mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
                    info['netmask'] = '.'.join([str((mask >> (24 - i*8)) & 0xff) for i in range(4)])
                    
                    # Calculate network
                    ip_parts = [int(p) for p in info['ipv4'].split('.')]
                    mask_parts = [int(p) for p in info['netmask'].split('.')]
                    network_parts = [ip_parts[i] & mask_parts[i] for i in range(4)]
                    info['network'] = '.'.join([str(p) for p in network_parts]) + f'/{cidr}'
            
            # Get IPv6 address (optional)
            result = subprocess.run(['ip', '-6', 'addr', 'show', interface_name],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                ipv6_matches = re.findall(r'inet6 ([0-9a-f:]+)/(\d+)', result.stdout)
                for addr, prefix in ipv6_matches:
                    if not addr.startswith('fe80:'):  # Prefer global over link-local
                        info['ipv6'] = addr
                        break
                if not info['ipv6'] and ipv6_matches:
                    info['ipv6'] = ipv6_matches[0][0]  # Use link-local if no global
            
            return info
        
        except Exception as e:
            logger.error(f"Error detecting interface {interface_name}: {e}")
            return None
    
    @staticmethod
    def discover_interfaces() -> List[Dict]:
        """
        Discover all active network interfaces
        NO CONFIGURATION NEEDED - fully automatic!
        """
        interfaces = []
        
        try:
            # Get all interfaces
            result = subprocess.run(['ip', 'link', 'show'],
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return interfaces
            
            # Parse interface names
            for line in result.stdout.split('\n'):
                match = re.match(r'\d+:\s+(\w+):', line)
                if match:
                    iface_name = match.group(1)
                    
                    # Skip loopback and docker interfaces
                    if iface_name in ['lo', 'docker0'] or iface_name.startswith('veth'):
                        continue
                    
                    # Get interface info
                    info = InterfaceDetector.get_interface_info(iface_name)
                    
                    if info and info['has_ip']:
                        interfaces.append(info)
                        logger.info(f"Discovered: {iface_name} - {info['ipv4']} ({info['network']})")
            
            return interfaces
        
        except Exception as e:
            logger.error(f"Error discovering interfaces: {e}")
            return interfaces

class AutoProfileGenerator:
    """Automatically generate traffic profiles from detected interfaces"""
    
    @staticmethod
    def generate_profiles(interfaces: List[Dict]) -> List[Dict]:
        """
        Generate profiles automatically
        NO MANUAL CONFIGURATION!
        """
        if len(interfaces) < 2:
            logger.warning("Need at least 2 interfaces with IPs for bidirectional testing")
            return []
        
        profiles = []
        
        # Define profile templates
        templates = {
            'udp_bulk': {
                'type': 'udp',
                'bandwidth_mbps': 1000,
                'packet_size': 1400,
                'dscp': 0
            },
            'tcp_connections': {
                'type': 'tcp',
                'dst_port': 80,
                'connections_per_sec': 1000,
                'concurrent_connections': 10000
            },
            'http_load': {
                'type': 'http',
                'method': 'GET',
                'url': '/',
                'requests_per_sec': 100
            },
            'voice': {
                'type': 'udp',
                'bandwidth_mbps': 1,
                'packet_size': 200,
                'packets_per_sec': 50,
                'dscp': 46  # EF
            },
            'video': {
                'type': 'udp',
                'bandwidth_mbps': 5,
                'packet_size': 1200,
                'dscp': 34  # AF41
            },
            'imix_standard': {
                'type': 'imix',
                'imix_profile': 'standard',
                'bandwidth_mbps': 100
            }
        }
        
        # Generate profiles for each interface pair
        for i, src in enumerate(interfaces):
            for dst in interfaces[i+1:]:
                for profile_name, template in templates.items():
                    # Forward direction
                    profile = {
                        'name': f'Auto_{src["name"]}_to_{dst["name"]}_{profile_name}',
                        'description': f'{profile_name.replace("_", " ").title()}: {src["network"]} → {dst["network"]}',
                        'src_interface': src['name'],
                        'src_ip': src['ipv4'],
                        'dst_interface': dst['name'],
                        'dst_ip': dst['ipv4'],
                        'enabled': False  # User must enable manually
                    }
                    profile.update(template)
                    profiles.append(profile)
                    
                    # Reverse direction
                    profile_rev = {
                        'name': f'Auto_{dst["name"]}_to_{src["name"]}_{profile_name}',
                        'description': f'{profile_name.replace("_", " ").title()}: {dst["network"]} → {src["network"]}',
                        'src_interface': dst['name'],
                        'src_ip': dst['ipv4'],
                        'dst_interface': src['name'],
                        'dst_ip': src['ipv4'],
                        'enabled': False
                    }
                    profile_rev.update(template)
                    profiles.append(profile_rev)
        
        logger.info(f"Generated {len(profiles)} automatic profiles")
        return profiles

class ConfigLoader:
    """Load configuration - auto-detect OR static override"""
    
    def __init__(self, config_file: str = '/opt/vep1445-traffic-gen/config/static_config.yaml'):
        self.config_file = config_file
        self.config = None
    
    def load(self) -> Dict:
        """
        Load configuration:
        1. Try to load static config file (if exists)
        2. Fall back to auto-detection (DHCP or static IPs)
        """
        # Try static config first (OPTIONAL!)
        try:
            with open(self.config_file, 'r') as f:
                self.config = yaml.safe_load(f)
                logger.info(f"Loaded static configuration from {self.config_file}")
                
                # Validate that IPs are actually configured
                if not self.config.get('interfaces'):
                    logger.warning("Static config exists but no interfaces defined, using auto-detection")
                    return self._auto_detect()
                
                return self.config
        except FileNotFoundError:
            logger.info("No static config found, using auto-detection (DHCP/static IPs)")
            return self._auto_detect()
        except Exception as e:
            logger.error(f"Error loading static config: {e}, falling back to auto-detection")
            return self._auto_detect()
    
    def _auto_detect(self) -> Dict:
        """
        Auto-detect configuration
        WORKS WITH DHCP OR STATIC IPs - NO MANUAL CONFIG NEEDED!
        """
        logger.info("Auto-detecting network configuration...")
        
        # Discover interfaces
        interfaces = InterfaceDetector.discover_interfaces()
        
        if not interfaces:
            logger.error("No interfaces with IP addresses found!")
            return {'interfaces': [], 'profiles': []}
        
        # Generate profiles automatically
        profiles = AutoProfileGenerator.generate_profiles(interfaces)
        
        config = {
            'auto_detected': True,
            'interfaces': interfaces,
            'profiles': profiles,
            'monitoring': {
                'snmp': {'enabled': False, 'agent_count': 0},
                'netflow': {'enabled': False, 'flows_per_second': 0}
            },
            'performance': {
                'tcp_pool_size': 100000,
                'memory_per_connection_kb': 2,
                'batch_size': 64,
                'use_zerocopy': True
            }
        }
        
        return config
    
    def save_auto_detected(self, output_file: str = '/opt/vep1445-traffic-gen/config/auto_detected.yaml'):
        """Save auto-detected config for reference"""
        if self.config and self.config.get('auto_detected'):
            try:
                with open(output_file, 'w') as f:
                    yaml.dump(self.config, f, default_flow_style=False)
                logger.info(f"Saved auto-detected config to {output_file}")
            except Exception as e:
                logger.error(f"Error saving auto-detected config: {e}")

# Main function for testing
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("VEP1445 Auto-Configuration")
    print("=" * 70)
    print()
    print("This tool automatically detects your network configuration.")
    print("Works with DHCP or static IPs - NO MANUAL CONFIGURATION NEEDED!")
    print()
    
    loader = ConfigLoader()
    config = loader.load()
    
    if config.get('auto_detected'):
        print("✓ Configuration auto-detected successfully!")
    else:
        print("✓ Using static configuration")
    
    print()
    print(f"Detected Interfaces: {len(config['interfaces'])}")
    print("-" * 70)
    for iface in config['interfaces']:
        print(f"  {iface['name']:10s} - {iface['ipv4']:15s} ({iface['network']})")
        print(f"             MAC: {iface['mac']}")
    
    print()
    print(f"Generated Profiles: {len(config['profiles'])}")
    print("-" * 70)
    
    # Show first few profiles as examples
    for profile in config['profiles'][:6]:
        status = "ENABLED" if profile.get('enabled') else "disabled"
        print(f"  [{status:8s}] {profile['name']}")
        print(f"              {profile['description']}")
    
    if len(config['profiles']) > 6:
        print(f"  ... and {len(config['profiles']) - 6} more profiles")
    
    print()
    print("=" * 70)
    print()
    
    # Save for reference
    loader.save_auto_detected()
    
    print("Auto-detected configuration saved to:")
    print("  /opt/vep1445-traffic-gen/config/auto_detected.yaml")
    print()
    print("To enable profiles, edit:")
    print("  nano /opt/vep1445-traffic-gen/config/auto_detected.yaml")
    print("  (change 'enabled: false' to 'enabled: true' for desired profiles)")
    print()
