#!/usr/bin/env python3
"""
VEP1445 Auto-Configuration Module
Automatically detects IPs on interfaces and creates traffic profiles
"""

import subprocess
import re
import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

def get_interface_info(interface_name: str) -> Dict:
    """Get MAC and IP address for interface"""
    info = {
        'name': interface_name,
        'mac': '00:00:00:00:00:00',
        'ip': None,
        'netmask': None,
        'network': None,
        'has_ip': False
    }
    
    try:
        # Get MAC address
        result = subprocess.run(['ip', 'link', 'show', interface_name],
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            mac_match = re.search(r'link/ether ([0-9a-f:]+)', result.stdout)
            if mac_match:
                info['mac'] = mac_match.group(1)
        
        # Get IP address
        result = subprocess.run(['ip', '-4', 'addr', 'show', interface_name],
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', result.stdout)
            if ip_match:
                info['ip'] = ip_match.group(1)
                cidr = int(ip_match.group(2))
                info['has_ip'] = True
                
                # Convert CIDR to netmask
                mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
                info['netmask'] = '.'.join([str((mask >> (24 - i*8)) & 0xff) for i in range(4)])
                
                # Calculate network address
                ip_parts = [int(p) for p in info['ip'].split('.')]
                mask_parts = [int(p) for p in info['netmask'].split('.')]
                network_parts = [ip_parts[i] & mask_parts[i] for i in range(4)]
                info['network'] = '.'.join([str(p) for p in network_parts]) + f'/{cidr}'
    
    except Exception as e:
        logger.error(f"Error getting info for {interface_name}: {e}")
    
    return info

def get_all_interfaces() -> List[Dict]:
    """Get info for all VEP1445 interfaces"""
    interfaces = []
    for iface in ['eno2', 'eno3', 'eno4', 'eno5', 'eno6']:
        try:
            info = get_interface_info(iface)
            interfaces.append(info)
        except:
            pass
    return interfaces

def generate_auto_profiles(interfaces: List[Dict]) -> List[Dict]:
    """Generate traffic profiles between all networks with IPs"""
    profiles = []
    
    # Get interfaces with IPs
    active_interfaces = [iface for iface in interfaces if iface['has_ip']]
    
    if len(active_interfaces) < 2:
        logger.warning("Not enough interfaces with IPs to create auto-profiles")
        return profiles
    
    # Create bidirectional traffic profiles between each pair
    for i, src in enumerate(active_interfaces):
        for dst in active_interfaces[i+1:]:
            # Forward profile
            profiles.append({
                'name': f'Auto_{src["name"]}_to_{dst["name"]}',
                'description': f'Auto-generated: {src["network"]} -> {dst["network"]}',
                'source_interface': src['name'],
                'source_ip': src['ip'],
                'dest_interface': dst['name'],
                'dest_ip': dst['ip'],
                'bandwidth_mbps': 100,
                'packet_size': 1400,
                'protocol': 'UDP',
                'enabled': False
            })
            
            # Reverse profile
            profiles.append({
                'name': f'Auto_{dst["name"]}_to_{src["name"]}',
                'description': f'Auto-generated: {dst["network"]} -> {src["network"]}',
                'source_interface': dst['name'],
                'source_ip': dst['ip'],
                'dest_interface': src['name'],
                'dest_ip': src['ip'],
                'bandwidth_mbps': 100,
                'packet_size': 1400,
                'protocol': 'UDP',
                'enabled': False
            })
    
    logger.info(f"Generated {len(profiles)} auto-profiles")
    return profiles

def save_auto_config(config_path: str = '/opt/vep1445-traffic-gen/auto_config.json'):
    """Save auto-configuration"""
    interfaces = get_all_interfaces()
    profiles = generate_auto_profiles(interfaces)
    
    config = {
        'auto_generated': True,
        'interfaces': interfaces,
        'auto_profiles': profiles
    }
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save auto-config: {e}")
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    interfaces = get_all_interfaces()
    
    print("Detected Interfaces:")
    for iface in interfaces:
        if iface['has_ip']:
            print(f"  {iface['name']}: {iface['ip']} ({iface['network']})")
        else:
            print(f"  {iface['name']}: No IP")
    
    profiles = generate_auto_profiles(interfaces)
    if profiles:
        print(f"\nGenerated {len(profiles)} auto-profiles")
        for profile in profiles:
            print(f"  {profile['name']}: {profile['source_ip']} -> {profile['dest_ip']}")
    
    if save_auto_config():
        print("\n✓ Auto-configuration saved")
