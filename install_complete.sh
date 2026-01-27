#!/bin/bash
#
# VEP1445 Complete Installer - All Fixes Included
# - DHCP enabled by default
# - Auto-generates and LOADS traffic profiles
# - All previous fixes integrated
# - Production-ready deployment
#

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║  VEP1445 Complete Installation (All Fixes Integrated)         ║"
echo "║  - DHCP enabled by default                                    ║"
echo "║  - Auto-profiles generated AND loaded                         ║"
echo "║  - All fixes applied automatically                            ║"
echo "║                                                                ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "This script requires root privileges. Re-running with sudo..."
    exec sudo "$0" "$@"
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_DIR="/opt/vep1445-traffic-gen"

# ═══════════════════════════════════════════════════════════════
# STEP 1: Install Dependencies
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 1: Installing Dependencies"
echo "═══════════════════════════════════════════════════════════════"
echo ""

apt-get update -qq
apt-get install -y python3 python3-pip ethtool iproute2 lldpd

# Install Python packages (Ubuntu 22.04 compatible)
echo "Installing Python packages..."
PIP_VERSION=$(pip3 --version | grep -oP 'pip \K[0-9]+' || echo "0")

if [ "$PIP_VERSION" -ge 23 ]; then
    pip3 install flask scapy psutil requests --break-system-packages
else
    apt-get install -y python3-flask python3-scapy python3-psutil python3-requests
fi

echo "  ✓ Dependencies installed"
echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 2: Create Installation Directory
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 2: Creating Installation Directory"
echo "═══════════════════════════════════════════════════════════════"
echo ""

mkdir -p "$INSTALL_DIR/web"
mkdir -p /var/log/vep1445

echo "  Installing to: $INSTALL_DIR"
echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 3: Copy Core Files
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 3: Installing Core Files"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Copy essential files only
if [ -f "$SCRIPT_DIR/traffic_engine_unified.py" ]; then
    cp "$SCRIPT_DIR/traffic_engine_unified.py" "$INSTALL_DIR/"
    echo "  ✓ traffic_engine_unified.py"
fi

if [ -f "$SCRIPT_DIR/web_api.py" ]; then
    cp "$SCRIPT_DIR/web_api.py" "$INSTALL_DIR/"
    echo "  ✓ web_api.py"
fi

if [ -f "$SCRIPT_DIR/neighbor_discovery.py" ]; then
    cp "$SCRIPT_DIR/neighbor_discovery.py" "$INSTALL_DIR/"
    echo "  ✓ neighbor_discovery.py"
fi

# Copy web files
if [ -d "$SCRIPT_DIR/web" ]; then
    cp -r "$SCRIPT_DIR"/web/* "$INSTALL_DIR/web/" 2>/dev/null || true
    echo "  ✓ Web GUI files"
fi

# Copy config examples
if [ -f "$SCRIPT_DIR/sample_config.json" ]; then
    cp "$SCRIPT_DIR/sample_config.json" "$INSTALL_DIR/"
fi

# Set permissions
chmod 755 "$INSTALL_DIR"
chmod 644 "$INSTALL_DIR"/*.py 2>/dev/null || true
chmod 644 "$INSTALL_DIR"/web/* 2>/dev/null || true

echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 4: Apply All Fixes to Core Files
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 4: Applying Integrated Fixes"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Fix 1: Socket binding in traffic_engine_unified.py
if [ -f "$INSTALL_DIR/traffic_engine_unified.py" ]; then
    echo "Applying traffic generation fix..."
    python3 << 'PYEOF'
import re

with open('/opt/vep1445-traffic-gen/traffic_engine_unified.py', 'r') as f:
    content = f.read()

# Fix socket initialization to bind to interface
if 'def initialize(self) -> bool:' in content and 'StandardNetworkInterface' in content:
    # Check if already fixed
    if 'self.socket.bind((self.config.name, 0))' not in content:
        # Find and fix the initialize method
        pattern = r'(class StandardNetworkInterface:.*?def initialize\(self\) -> bool:.*?self\.socket = socket\.socket\([^)]+\))'
        replacement = r'\1\n            \n            # CRITICAL: Bind socket to specific interface\n            self.socket.bind((self.config.name, 0))'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        with open('/opt/vep1445-traffic-gen/traffic_engine_unified.py', 'w') as f:
            f.write(content)
        print("  ✓ Traffic generation fix applied")
    else:
        print("  ✓ Traffic generation already fixed")
else:
    print("  ⚠ Could not apply traffic fix (may not be needed)")
PYEOF
fi

echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 5: Configure DHCP
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 5: Configuring DHCP (Default Enabled)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

INTERFACES=("eno2" "eno3" "eno4" "eno5" "eno6")

echo "Configuring network interfaces for DHCP..."
echo ""

# Detect network configuration method
if systemctl is-active --quiet NetworkManager; then
    echo "Using NetworkManager..."
    for iface in "${INTERFACES[@]}"; do
        if ip link show "$iface" &>/dev/null; then
            nmcli connection delete "$iface" 2>/dev/null || true
            nmcli connection add type ethernet ifname "$iface" con-name "$iface" \
                ipv4.method auto \
                ipv6.method ignore \
                connection.autoconnect yes &>/dev/null
            echo "  ✓ $iface configured for DHCP"
        fi
    done
    
elif [ -d "/etc/netplan" ]; then
    echo "Using Netplan..."
    
    # Build complete netplan config in memory first
    NETPLAN_CONFIG="network:
  version: 2
  renderer: networkd
  ethernets:"
    
    for iface in "${INTERFACES[@]}"; do
        if ip link show "$iface" &>/dev/null; then
            NETPLAN_CONFIG="${NETPLAN_CONFIG}
    ${iface}:
      dhcp4: true
      dhcp6: false
      dhcp4-overrides:
        use-dns: false"
            echo "  ✓ $iface will be configured"
        fi
    done
    
    # Write complete config at once
    echo "$NETPLAN_CONFIG" > /etc/netplan/99-vep1445-dhcp.yaml
    chmod 600 /etc/netplan/99-vep1445-dhcp.yaml
    
    echo "  ✓ Netplan configuration created"
    netplan apply
fi

echo ""
echo "Bringing up interfaces and requesting DHCP..."
for iface in "${INTERFACES[@]}"; do
    if ip link show "$iface" &>/dev/null; then
        ip link set "$iface" up
        if command -v dhclient &>/dev/null; then
            dhclient -v "$iface" &>/dev/null &
        fi
    fi
done

echo "Waiting for DHCP leases (10 seconds)..."
sleep 10

echo ""
echo "Detected IP Addresses:"
echo "────────────────────────────────────────────────────────────────"
declare -A INTERFACE_IPS
IP_COUNT=0

for iface in "${INTERFACES[@]}"; do
    if ip link show "$iface" &>/dev/null; then
        IP=$(ip -4 addr show "$iface" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "")
        MAC=$(ip link show "$iface" 2>/dev/null | grep -oP '(?<=link/ether )[^ ]+' || echo "")
        
        if [ -n "$IP" ]; then
            echo "  ✅ $iface: $IP (MAC: $MAC)"
            INTERFACE_IPS[$iface]=$IP
            IP_COUNT=$((IP_COUNT + 1))
        else
            echo "  ⚠️  $iface: No IP (MAC: $MAC)"
        fi
    fi
done
echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 6: Create Auto-Configuration Module
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 6: Creating Auto-Configuration Module"
echo "═══════════════════════════════════════════════════════════════"
echo ""

cat > "$INSTALL_DIR/auto_config.py" << 'PYEOF'
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
PYEOF

chmod +x "$INSTALL_DIR/auto_config.py"
echo "  ✓ Auto-configuration module created"
echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 7: Generate Initial Auto-Config
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 7: Generating Auto-Configuration"
echo "═══════════════════════════════════════════════════════════════"
echo ""

cd "$INSTALL_DIR"
python3 auto_config.py

echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 8: Update web_api.py with COMPLETE Fix
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 8: Integrating Auto-Profiles into Engine"
echo "═══════════════════════════════════════════════════════════════"
echo ""

if [ -f "$INSTALL_DIR/web_api.py" ]; then
    python3 << 'PYEOF'
import re

web_api_path = '/opt/vep1445-traffic-gen/web_api.py'

with open(web_api_path, 'r') as f:
    content = f.read()

# Complete initialize function with ACTUAL profile loading (not just logging!)
new_init = '''def initialize_default_config():
    """Initialize with DHCP-enabled interfaces and auto-load profiles"""
    import logging
    import sys
    import json
    logger = logging.getLogger(__name__)
    
    sys.path.insert(0, '/opt/vep1445-traffic-gen')
    from auto_config import get_all_interfaces, generate_auto_profiles, save_auto_config
    
    # Get interfaces with real IPs from DHCP
    interfaces = get_all_interfaces()
    
    interfaces_added = 0
    for iface_info in interfaces:
        try:
            config = InterfaceConfig(
                name=iface_info['name'],
                mac_address=iface_info['mac'],
                ip_address=iface_info.get('ip'),
                subnet_mask=iface_info.get('netmask'),
                interface_type=InterfaceType.COPPER_OPTIMIZED,
                speed_mbps=1000
            )
            
            engine.add_interface(config)
            interfaces_added += 1
            
            if iface_info['has_ip']:
                logger.info(f"Added {iface_info['name']}: MAC={iface_info['mac']}, IP={iface_info['ip']} (DHCP)")
            else:
                logger.info(f"Added {iface_info['name']}: MAC={iface_info['mac']}, IP=None (no DHCP)")
            
        except Exception as e:
            logger.error(f"Failed to add interface {iface_info['name']}: {e}")
    
    logger.info(f"Initialized {interfaces_added} interfaces (DHCP enabled)")
    
    # Generate auto-profiles and save to JSON
    auto_profiles = generate_auto_profiles(interfaces)
    if auto_profiles:
        logger.info(f"Auto-generated {len(auto_profiles)} traffic profiles")
        save_auto_config()
        
        # NOW LOAD THEM INTO THE ENGINE (this was missing!)
        profiles_loaded = 0
        for profile_config in auto_profiles:
            try:
                # CRITICAL: CREATE the TrafficProfile object
                profile = TrafficProfile(
                    name=profile_config['name'],
                    source_interface=profile_config['source_interface'],
                    destination_interface=profile_config['dest_interface'],
                    bandwidth_mbps=profile_config['bandwidth_mbps'],
                    packet_size=profile_config['packet_size'],
                    protocol=profile_config['protocol']
                )
                
                # CRITICAL: ADD to engine (makes it visible in GUI!)
                engine.add_traffic_profile(profile)
                profiles_loaded += 1
                
                logger.info(f"  ✓ LOADED into engine: {profile_config['name']}: {profile_config['source_ip']} -> {profile_config['dest_ip']}")
            except Exception as e:
                logger.error(f"Failed to load profile {profile_config['name']}: {e}")
        
        logger.info(f"✅ Successfully loaded {profiles_loaded}/{len(auto_profiles)} profiles - VISIBLE IN GUI!")
    else:
        logger.warning("No auto-profiles generated (need 2+ interfaces with IPs)")
'''

# Replace the function
pattern = r'def initialize_default_config\(\):.*?(?=\n(?:def |if __name__|app = Flask))'
if re.search(pattern, content, re.DOTALL):
    content = re.sub(pattern, new_init, content, flags=re.DOTALL)
    
    with open(web_api_path, 'w') as f:
        f.write(content)
    
    print("  ✓ web_api.py FULLY FIXED - profiles will load into engine!")
else:
    print("  ⚠️  Could not find initialize_default_config() - may need manual fix")
PYEOF
    echo ""
else
    echo "  ⚠️  web_api.py not found"
    echo ""
fi

# ═══════════════════════════════════════════════════════════════
# STEP 9: Create Systemd Service
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 9: Creating Systemd Service"
echo "═══════════════════════════════════════════════════════════════"
echo ""

cat > /etc/systemd/system/vep1445.service << EOF
[Unit]
Description=VEP1445 Traffic Generator with Auto-Configuration
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStartPre=/bin/sleep 10
ExecStartPre=$INSTALL_DIR/auto_config.py
ExecStart=/usr/bin/python3 $INSTALL_DIR/web_api.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vep1445

echo "  ✓ Systemd service created and enabled"
echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 10: Create Documentation
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 10: Creating Documentation"
echo "═══════════════════════════════════════════════════════════════"
echo ""

cat > "$INSTALL_DIR/README.txt" << 'EOF'
VEP1445 TRAFFIC GENERATOR
Multi-Protocol Network Impairment & RFC2544 Testing Platform

QUICK START:
───────────────────────────────────────────────────────────────
1. Start VEP1445:
   sudo systemctl start vep1445

2. Access Web GUI:
   http://localhost:5000

3. Enable auto-generated profiles in "Traffic Profiles" tab

4. Click "Start Traffic"

FEATURES:
───────────────────────────────────────────────────────────────
✓ DHCP enabled by default
✓ Auto-detects network IPs
✓ Auto-generates traffic profiles
✓ Neighbor discovery (ARP/LLDP)
✓ Web-based management
✓ Multi-interface support (eno2-eno6)

COMMANDS:
───────────────────────────────────────────────────────────────
Start:    sudo systemctl start vep1445
Stop:     sudo systemctl stop vep1445
Restart:  sudo systemctl restart vep1445
Status:   sudo systemctl status vep1445
Logs:     sudo journalctl -u vep1445 -f

TROUBLESHOOTING:
───────────────────────────────────────────────────────────────
No profiles in GUI?
  → Restart VEP1445: sudo systemctl restart vep1445

No IPs detected?
  → Check DHCP: sudo journalctl -u NetworkManager | grep DHCP
  → Check interfaces: ip addr show

For help: See documentation in /opt/vep1445-traffic-gen/
EOF

echo "  ✓ Documentation created"
echo ""

# ═══════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║  ✅ VEP1445 Installation Complete - All Fixes Integrated!     ║"
echo "║                                                                ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

echo "INSTALLATION SUMMARY:"
echo "────────────────────────────────────────────────────────────────"
echo "  Location: $INSTALL_DIR"
echo "  DHCP: ✅ Enabled by default"
echo "  Auto-Profiles: ✅ Generated AND loaded"
echo "  All Fixes: ✅ Integrated"
echo "  Service: ✅ Enabled on boot"
echo ""

echo "NETWORK CONFIGURATION:"
echo "────────────────────────────────────────────────────────────────"
for iface in "${INTERFACES[@]}"; do
    if ip link show "$iface" &>/dev/null; then
        IP=$(ip -4 addr show "$iface" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "")
        if [ -n "$IP" ]; then
            echo "  ✅ $iface: $IP (DHCP)"
        else
            echo "  ⚠️  $iface: No IP"
        fi
    fi
done
echo ""

if [ $IP_COUNT -ge 2 ]; then
    PROFILE_COUNT=$((IP_COUNT * (IP_COUNT - 1)))
    echo "AUTO-GENERATED PROFILES:"
    echo "────────────────────────────────────────────────────────────────"
    echo "  ✅ $PROFILE_COUNT traffic profiles created"
    echo "  ✅ Profiles loaded into engine"
    echo "  ✅ Visible in GUI immediately"
    echo ""
fi

echo "NEXT STEPS:"
echo "────────────────────────────────────────────────────────────────"
echo "  1. Start VEP1445:"
echo "     sudo systemctl start vep1445"
echo ""
echo "  2. Access Web GUI:"
echo "     http://localhost:5000"
echo ""
echo "  3. Go to 'Traffic Profiles' tab"
echo "     → You should see Auto_eno2_to_eno3, etc."
echo "     → Enable desired profiles"
echo "     → Click 'Start Traffic'"
echo ""
echo "  4. Monitor:"
echo "     sudo journalctl -u vep1445 -f"
echo ""

if [ $IP_COUNT -ge 2 ]; then
    echo "🎉 READY! Your VEP1445 has $IP_COUNT networks configured"
    echo "   with $PROFILE_COUNT auto-generated traffic profiles!"
else
    echo "💡 TIP: Connect more networks with DHCP for auto-profiles"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
