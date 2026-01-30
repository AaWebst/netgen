#!/usr/bin/env python3
"""
VEP1445 Neighbor Discovery Module
Implements ARP and LLDP discovery for detecting connected devices
"""

import subprocess
import re
import logging
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)


class NeighborDiscovery:
    """Discover neighbors using ARP and LLDP"""
    
    def __init__(self):
        self.arp_cache = {}
        self.lldp_cache = {}
        self.last_scan = {}
        
    def discover_interface(self, interface_name: str) -> Dict:
        """Discover neighbors on a specific interface"""
        result = {
            'interface': interface_name,
            'arp_neighbors': [],
            'lldp_neighbors': [],
            'link_status': self._get_link_status(interface_name),
            'timestamp': time.time()
        }
        
        # Get ARP neighbors
        try:
            arp_neighbors = self._discover_arp(interface_name)
            result['arp_neighbors'] = arp_neighbors
        except Exception as e:
            logger.debug(f"ARP discovery failed on {interface_name}: {e}")
        
        # Get LLDP neighbors
        try:
            lldp_neighbors = self._discover_lldp(interface_name)
            result['lldp_neighbors'] = lldp_neighbors
        except Exception as e:
            logger.debug(f"LLDP discovery failed on {interface_name}: {e}")
        
        # Cache results
        self.last_scan[interface_name] = result
        
        return result
    
    def _get_link_status(self, interface_name: str) -> Dict:
        """Get link status using ethtool or ip command"""
        try:
            # Try ethtool first
            result = subprocess.run(
                ['ethtool', interface_name],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                output = result.stdout
                link_detected = 'Link detected: yes' in output
                speed_match = re.search(r'Speed: (\d+)([MG]b/s)', output)
                duplex_match = re.search(r'Duplex: (\w+)', output)
                
                return {
                    'up': link_detected,
                    'speed': speed_match.group(0) if speed_match else 'Unknown',
                    'duplex': duplex_match.group(1) if duplex_match else 'Unknown'
                }
        except:
            pass
        
        # Fallback to ip command
        try:
            result = subprocess.run(
                ['ip', 'link', 'show', interface_name],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                output = result.stdout
                return {
                    'up': 'UP' in output and 'LOWER_UP' in output,
                    'speed': 'Unknown',
                    'duplex': 'Unknown'
                }
        except:
            pass
        
        return {'up': False, 'speed': 'Unknown', 'duplex': 'Unknown'}
    
    def _discover_arp(self, interface_name: str) -> List[Dict]:
        """Discover neighbors using ARP"""
        neighbors = []
        
        try:
            # Get ARP table
            result = subprocess.run(
                ['ip', 'neigh', 'show', 'dev', interface_name],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    # Parse: 192.168.1.1 lladdr aa:bb:cc:dd:ee:ff REACHABLE
                    parts = line.split()
                    if len(parts) >= 4:
                        ip = parts[0]
                        mac = parts[3] if 'lladdr' in parts[1:3] else None
                        state = parts[-1]
                        
                        if mac and state in ['REACHABLE', 'STALE', 'DELAY']:
                            neighbors.append({
                                'ip': ip,
                                'mac': mac,
                                'state': state,
                                'type': 'arp'
                            })
        
        except Exception as e:
            logger.debug(f"ARP discovery error: {e}")
        
        return neighbors
    
    def _discover_lldp(self, interface_name: str) -> List[Dict]:
        """Discover neighbors using LLDP"""
        neighbors = []
        
        try:
            # Try lldpctl (from lldpd package)
            result = subprocess.run(
                ['lldpctl', interface_name],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                output = result.stdout
                neighbor = self._parse_lldp_output(output)
                if neighbor:
                    neighbors.append(neighbor)
        
        except FileNotFoundError:
            logger.debug("lldpctl not found - install lldpd for LLDP support")
        except Exception as e:
            logger.debug(f"LLDP discovery error: {e}")
        
        return neighbors
    
    def _parse_lldp_output(self, output: str) -> Optional[Dict]:
        """Parse lldpctl output"""
        neighbor = {'type': 'lldp'}
        
        # Extract system name
        match = re.search(r'SysName:\s+(.+)', output)
        if match:
            neighbor['system_name'] = match.group(1).strip()
        
        # Extract system description
        match = re.search(r'SysDescr:\s+(.+)', output)
        if match:
            neighbor['system_desc'] = match.group(1).strip()
        
        # Extract port ID
        match = re.search(r'PortID:\s+(.+)', output)
        if match:
            neighbor['port_id'] = match.group(1).strip()
        
        # Extract port description
        match = re.search(r'PortDescr:\s+(.+)', output)
        if match:
            neighbor['port_desc'] = match.group(1).strip()
        
        # Extract chassis ID (MAC)
        match = re.search(r'ChassisID:\s+(.+)', output)
        if match:
            neighbor['chassis_id'] = match.group(1).strip()
        
        return neighbor if len(neighbor) > 1 else None
    
    def get_best_neighbor_info(self, interface_name: str) -> str:
        """Get the most useful neighbor information for display"""
        if interface_name not in self.last_scan:
            return "No scan data"
        
        scan = self.last_scan[interface_name]
        
        # Prefer LLDP info (more detailed)
        if scan['lldp_neighbors']:
            lldp = scan['lldp_neighbors'][0]
            if 'system_name' in lldp:
                port_info = f":{lldp.get('port_id', '')}" if 'port_id' in lldp else ""
                return f"{lldp['system_name']}{port_info}"
            elif 'system_desc' in lldp:
                return lldp['system_desc'][:30]
        
        # Fall back to ARP
        if scan['arp_neighbors']:
            arp = scan['arp_neighbors'][0]
            return f"{arp['ip']} ({arp['mac'][:8]}...)"
        
        # Check link status
        if scan['link_status']['up']:
            return "Link UP (no neighbors)"
        else:
            return "Link DOWN"


# Global instance
neighbor_discovery = NeighborDiscovery()
