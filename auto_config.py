#!/usr/bin/env python3
"""
VEP1445 Enhanced Auto-Configuration Module
Automatically detects IPs and creates multiple traffic profile types:
- UDP bulk traffic
- TCP simulation (for future support)
- Voice & Video optimized profiles
"""

import subprocess
import re
import json
import os
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

def generate_auto_profiles(interfaces: List[Dict], profile_types: List[str] = None) -> List[Dict]:
    """
    Generate traffic profiles between all networks with IPs
    
    Args:
        interfaces: List of interface info dicts
        profile_types: List of profile types to generate
                      Options: ['udp', 'tcp', 'voice', 'video']
                      Default: ['udp', 'voice', 'video']
    """
    if profile_types is None:
        profile_types = ['udp', 'voice', 'video']
    
    profiles = []
    
    # Get interfaces with IPs
    active_interfaces = [iface for iface in interfaces if iface['has_ip']]
    
    if len(active_interfaces) < 2:
        logger.warning("Not enough interfaces with IPs to create auto-profiles")
        return profiles
    
    # Profile templates
    profile_templates = {
        'udp': {
            'suffix': 'UDP',
            'description': 'UDP bulk traffic',
            'bandwidth_mbps': 100,
            'packet_size': 1400,
            'protocol': 'ipv4',  # Currently engine uses 'ipv4' for UDP
            'dscp': 0
        },
        'tcp': {
            'suffix': 'TCP',
            'description': 'TCP simulation (future support)',
            'bandwidth_mbps': 100,
            'packet_size': 1400,
            'protocol': 'ipv4',  # Will use TCP when supported
            'dscp': 0
        },
        'voice': {
            'suffix': 'Voice',
            'description': 'Voice traffic (G.711)',
            'bandwidth_mbps': 1,
            'packet_size': 200,  # Typical VoIP packet
            'protocol': 'ipv4',
            'dscp': 46  # EF (Expedited Forwarding) for voice
        },
        'video': {
            'suffix': 'Video',
            'description': 'Video conferencing',
            'bandwidth_mbps': 5,
            'packet_size': 1200,  # Typical video packet
            'protocol': 'ipv4',
            'dscp': 34  # AF41 for video
        }
    }
    
    # Create profiles for each interface pair and each type
    for i, src in enumerate(active_interfaces):
        for dst in active_interfaces[i+1:]:
            for ptype in profile_types:
                if ptype not in profile_templates:
                    continue
                
                template = profile_templates[ptype]
                
                # Forward profile
                profiles.append({
                    'name': f'Auto_{src["name"]}_to_{dst["name"]}_{template["suffix"]}',
                    'description': f'Auto: {src["network"]} → {dst["network"]} - {template["description"]}',
                    'source_interface': src['name'],
                    'source_ip': src['ip'],
                    'dest_interface': dst['name'],
                    'dest_ip': dst['ip'],
                    'bandwidth_mbps': template['bandwidth_mbps'],
                    'packet_size': template['packet_size'],
                    'protocol': template['protocol'],
                    'dscp': template.get('dscp', 0),
                    'enabled': False
                })
                
                # Reverse profile
                profiles.append({
                    'name': f'Auto_{dst["name"]}_to_{src["name"]}_{template["suffix"]}',
                    'description': f'Auto: {dst["network"]} → {src["network"]} - {template["description"]}',
                    'source_interface': dst['name'],
                    'source_ip': dst['ip'],
                    'dest_interface': src['name'],
                    'dest_ip': src['ip'],
                    'bandwidth_mbps': template['bandwidth_mbps'],
                    'packet_size': template['packet_size'],
                    'protocol': template['protocol'],
                    'dscp': template.get('dscp', 0),
                    'enabled': False
                })
    
    logger.info(f"Generated {len(profiles)} auto-profiles ({len(profile_types)} types × {len(active_interfaces)*(len(active_interfaces)-1)} directions)")
    return profiles

def save_auto_config(config_path: str = None):
    """Save auto-configuration"""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_config.json')
    interfaces = get_all_interfaces()
    
    # Generate all profile types
    profiles = generate_auto_profiles(interfaces, profile_types=['udp', 'tcp', 'voice', 'video'])
    
    config = {
        'auto_generated': True,
        'profile_types': ['udp', 'tcp', 'voice', 'video'],
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
    import sys
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # optional: pull in requests only if we are going to POST
    try:
        import requests as _req
        HAS_REQUESTS = True
    except ImportError:
        HAS_REQUESTS = False

    interfaces = get_all_interfaces()

    print("=" * 63)
    print("  VEP1445 Auto-Config  --  Detect / Save / Load")
    print("=" * 63)
    print()
    print("Detected Interfaces:")
    for iface in interfaces:
        if iface['has_ip']:
            print(f"  {iface['name']}: {iface['ip']} ({iface['network']})")
        else:
            print(f"  {iface['name']}: No IP")

    profiles = generate_auto_profiles(interfaces, profile_types=['udp', 'tcp', 'voice', 'video'])

    if not profiles:
        print("\n[!] No profiles generated -- need at least 2 interfaces with IPs.")
        sys.exit(1)

    # -- print summary --
    print(f"\nGenerated {len(profiles)} auto-profiles:")
    by_type = {}
    for p in profiles:
        ptype = p['name'].split('_')[-1]
        by_type.setdefault(ptype, []).append(p)
    for ptype, plist in sorted(by_type.items()):
        print(f"\n  {ptype} profiles ({len(plist)}):")
        for p in plist[:4]:
            print(f"    {p['name']}: {p['source_ip']} -> {p['dest_ip']} ({p['bandwidth_mbps']} Mbps, DSCP {p.get('dscp', 0)})")
        if len(plist) > 4:
            print(f"    ... and {len(plist)-4} more")

    # -- step 1: save JSON next to this script --
    if save_auto_config():
        print("\n[ok] auto_config.json saved")
    else:
        print("\n[!!] Failed to save auto_config.json")

    # -- step 2: POST every profile into the live API --
    if not HAS_REQUESTS:
        print("\n[!] 'requests' not installed -- skipping API load.")
        print("    Install:  pip3 install requests --break-system-packages")
        sys.exit(0)

    API_URL = "http://localhost:5000/api/traffic-profiles"

    # quick connectivity check
    try:
        _req.get("http://localhost:5000/api/system/status", timeout=2)
    except Exception:
        print("\n[!!] Cannot reach http://localhost:5000 -- is web_api.py running?")
        print("     Start it:  sudo python3 web_api.py")
        sys.exit(1)

    print(f"\nLoading {len(profiles)} profiles into the running instance...")
    success = 0
    failed  = 0

    for p in profiles:
        # Map auto_config field names -> API field names
        payload = {
            'name':            p['name'],
            'src_interface':   p['source_interface'],
            'dst_interface':   p['dest_interface'],
            'dst_ip':          p['dest_ip'],
            'bandwidth_mbps':  p['bandwidth_mbps'],
            'packet_size':     p['packet_size'],
            'protocol':        p['protocol'],
            'dscp':            p.get('dscp', 0),
            'enabled':         False
        }
        try:
            r = _req.post(API_URL, json=payload, timeout=5)
            result = r.json()
            if r.status_code in (200, 201) and result.get('success'):
                print(f"  [ok] {p['name']}")
                success += 1
            else:
                print(f"  [!!] {p['name']} -- {result.get('error', r.text[:80])}")
                failed += 1
        except Exception as e:
            print(f"  [!!] {p['name']} -- {e}")
            failed += 1

    print()
    print("-" * 63)
    print(f"  Results: {success} loaded, {failed} failed")
    if success:
        print("\n  Refresh http://localhost:5000  -->  Traffic Profiles tab")
    else:
        print("\n  No profiles were loaded into the API")
    sys.exit(0 if success else 1)
