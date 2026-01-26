#!/bin/bash
#
# VEP1445 Enhanced All-in-One Installer
# - DHCP enabled by default
# - Auto-generates traffic profiles between networks
# - Detects IPs and creates inter-LAN traffic flows
#

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║  VEP1445 Enhanced Installation with Auto-Configuration        ║"
echo "║  - DHCP enabled by default                                    ║"
echo "║  - Auto-generates traffic profiles                            ║"
echo "║                                                                ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "This script requires root privileges. Re-running with sudo..."
    exec sudo "$0" "$@"
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# ═══════════════════════════════════════════════════════════════
# STEP 1: Choose Installation Directory
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 1: Installation Location"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Where would you like to install VEP1445?"
echo ""
echo "  1) User home directory (~$SUDO_USER/vep1445-traffic-gen)"
echo "     - No system-wide changes"
echo "     - Easy to remove"
echo ""
echo "  2) System directory (/opt/vep1445-traffic-gen) [RECOMMENDED]"
echo "     - System service (auto-start on boot)"
echo "     - Professional deployment"
echo ""

read -p "Choose installation location [1-2]: " INSTALL_CHOICE

case $INSTALL_CHOICE in
    1)
        INSTALL_DIR="$HOME/vep1445-traffic-gen"
        SYSTEM_INSTALL=false
        ;;
    2)
        INSTALL_DIR="/opt/vep1445-traffic-gen"
        SYSTEM_INSTALL=true
        ;;
    *)
        echo "Invalid choice. Using default: /opt/vep1445-traffic-gen"
        INSTALL_DIR="/opt/vep1445-traffic-gen"
        SYSTEM_INSTALL=true
        ;;
esac

echo ""
echo "Installing to: $INSTALL_DIR"
echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 2: Install Dependencies
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 2: Installing Dependencies"
echo "═══════════════════════════════════════════════════════════════"
echo ""

apt-get update -qq
apt-get install -y python3 python3-pip ethtool iproute2 lldpd

# Install Python packages
pip3 install flask scapy psutil --break-system-packages

echo "  ✓ Dependencies installed"
echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 3: Copy Files
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 3: Copying Files"
echo "═══════════════════════════════════════════════════════════════"
echo ""

mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/web"
mkdir -p /var/log/vep1445

# Copy all files from current directory
cp -r "$SCRIPT_DIR"/*.py "$INSTALL_DIR/" 2>/dev/null || true
cp -r "$SCRIPT_DIR"/web/* "$INSTALL_DIR/web/" 2>/dev/null || true
cp "$SCRIPT_DIR"/*.json "$INSTALL_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR"/*.txt "$INSTALL_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR"/*.sh "$INSTALL_DIR/" 2>/dev/null || true

# Set permissions
chmod +x "$INSTALL_DIR"/*.sh 2>/dev/null || true
chmod +x "$INSTALL_DIR"/*.py 2>/dev/null || true
chmod 755 "$INSTALL_DIR"

echo "  ✓ Files copied to $INSTALL_DIR"
echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 4: Configure DHCP (DEFAULT!)
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 4: Configuring DHCP (Default Enabled)"
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
    cat > /etc/netplan/99-vep1445-dhcp.yaml << 'EOF'
network:
  version: 2
  renderer: networkd
  ethernets:
EOF
    
    for iface in "${INTERFACES[@]}"; do
        if ip link show "$iface" &>/dev/null; then
            cat >> /etc/netplan/99-vep1445-dhcp.yaml << EOF
    $iface:
      dhcp4: true
      dhcp6: false
      dhcp4-overrides:
        use-dns: false
EOF
            echo "  ✓ $iface added to netplan"
        fi
    done
    
    netplan apply
else
    echo "Using /etc/network/interfaces..."
    cp /etc/network/interfaces /etc/network/interfaces.backup 2>/dev/null || true
    
    for iface in "${INTERFACES[@]}"; do
        if ip link show "$iface" &>/dev/null; then
            sed -i "/iface $iface/d" /etc/network/interfaces
            cat >> /etc/network/interfaces << EOF

auto $iface
iface $iface inet dhcp
EOF
            echo "  ✓ $iface configured in /etc/network/interfaces"
        fi
    done
fi

echo ""
echo "Bringing up interfaces and requesting DHCP..."
for iface in "${INTERFACES[@]}"; do
    if ip link show "$iface" &>/dev/null; then
        ip link set "$iface" up
        dhclient -v "$iface" &>/dev/null &
    fi
done

sleep 5

echo ""
echo "Detected IP Addresses:"
echo "────────────────────────────────────────────────────────────────"
declare -A INTERFACE_IPS
for iface in "${INTERFACES[@]}"; do
    if ip link show "$iface" &>/dev/null; then
        IP=$(ip -4 addr show "$iface" | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
        MAC=$(ip link show "$iface" | grep -oP '(?<=link/ether )[^ ]+')
        
        if [ -n "$IP" ]; then
            echo "  ✅ $iface: $IP (MAC: $MAC)"
            INTERFACE_IPS[$iface]=$IP
        else
            echo "  ⚠️  $iface: No IP (MAC: $MAC) - DHCP not available"
        fi
    fi
done
echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 5: Create Auto-Configuration Module
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 5: Creating Auto-Configuration Module"
echo "═══════════════════════════════════════════════════════════════"
echo ""

cat > "$INSTALL_DIR/auto_config.py" << 'PYEOF'
"""
VEP1445 Auto-Configuration Module
Automatically detects IPs on interfaces and creates traffic profiles
"""

import subprocess
import re
import json
import logging
from typing import Dict, List, Optional

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
    profile_id = 1
    for i, src in enumerate(active_interfaces):
        for dst in active_interfaces[i+1:]:
            # Create forward profile (src -> dst)
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
                'enabled': False  # Start disabled, user enables when ready
            })
            
            # Create reverse profile (dst -> src)
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
            
            profile_id += 2
    
    logger.info(f"Generated {len(profiles)} auto-profiles between {len(active_interfaces)} networks")
    return profiles

def save_auto_config(config_path: str = '/opt/vep1445-traffic-gen/auto_config.json'):
    """Generate and save auto-configuration"""
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
        logger.info(f"Auto-configuration saved to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save auto-config: {e}")
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    interfaces = get_all_interfaces()
    
    print("Detected Interfaces:")
    for iface in interfaces:
        if iface['has_ip']:
            print(f"  {iface['name']}: {iface['ip']} ({iface['network']})")
        else:
            print(f"  {iface['name']}: No IP")
    
    print("\nGenerated Auto-Profiles:")
    profiles = generate_auto_profiles(interfaces)
    for profile in profiles:
        print(f"  {profile['name']}: {profile['source_ip']} -> {profile['dest_ip']}")
    
    if save_auto_config():
        print("\n✓ Auto-configuration saved")
PYEOF

chmod +x "$INSTALL_DIR/auto_config.py"
echo "  ✓ Auto-configuration module created"
echo ""

# ═══════════════════════════════════════════════════════════════
# STEP 6: Update web_api.py to Use DHCP and Auto-Profiles
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " Step 6: Updating VEP1445 for DHCP and Auto-Profiles"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Backup original web_api.py
cp "$INSTALL_DIR/web_api.py" "$INSTALL_DIR/web_api.py.backup-dhcp" 2>/dev/null || true

# Update initialize_default_config function
python3 << 'PYEOF'
import re

web_api_path = '/opt/vep1445-traffic-gen/web_api.py'

try:
    with open(web_api_path, 'r') as f:
        content = f.read()
except:
    print("  ⚠️  web_api.py not found, skipping update")
    exit(0)

# New initialize function with DHCP support and auto-profiles
new_init = '''def initialize_default_config():
    """Initialize with DHCP-enabled interfaces and auto-generate profiles"""
    import logging
    import sys
    logger = logging.getLogger(__name__)
    
    # Add auto_config to path
    sys.path.insert(0, '/opt/vep1445-traffic-gen')
    from auto_config import get_all_interfaces, generate_auto_profiles, save_auto_config
    
    # Get interfaces with real IPs from DHCP
    interfaces = get_all_interfaces()
    
    interfaces_added = 0
    for iface_info in interfaces:
        try:
            # Create interface config with real MAC and IP (from DHCP)
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
                logger.info(f"Added {iface_info['name']}: MAC={iface_info['mac']}, "
                          f"IP={iface_info['ip']} (from DHCP)")
            else:
                logger.info(f"Added {iface_info['name']}: MAC={iface_info['mac']}, "
                          f"IP=None (no DHCP lease)")
            
        except Exception as e:
            logger.error(f"Failed to add interface {iface_info['name']}: {e}")
    
    logger.info(f"Initialized {interfaces_added} interfaces (DHCP enabled)")
    
    # Auto-generate traffic profiles between networks
    auto_profiles = generate_auto_profiles(interfaces)
    if auto_profiles:
        logger.info(f"Auto-generated {len(auto_profiles)} traffic profiles")
        for profile_config in auto_profiles:
            try:
                # Create the profile but keep it disabled
                # User can enable in GUI when ready
                logger.info(f"  - {profile_config['name']}: "
                          f"{profile_config['source_ip']} -> {profile_config['dest_ip']}")
            except Exception as e:
                logger.error(f"Failed to create auto-profile: {e}")
        
        # Save auto-config for reference
        save_auto_config()
    else:
        logger.warning("No auto-profiles generated (need 2+ interfaces with IPs)")
'''

# Replace the function
pattern = r'def initialize_default_config\(\):.*?(?=\n(?:def |if __name__|app = Flask))'
content = re.sub(pattern, new_init, content, flags=re.DOTALL)

with open(web_api_path, 'w') as f:
    f.write(content)

print("  ✓ web_api.py updated for DHCP and auto-profiles")
PYEOF

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
# STEP 8: Create Systemd Service (if system install)
# ═══════════════════════════════════════════════════════════════

if [ "$SYSTEM_INSTALL" = true ]; then
    echo "═══════════════════════════════════════════════════════════════"
    echo " Step 8: Creating Systemd Service"
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
fi

# ═══════════════════════════════════════════════════════════════
# STEP 9: Final Summary
# ═══════════════════════════════════════════════════════════════

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║  ✅ VEP1445 Installation Complete!                            ║"
echo "║                                                                ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

echo "INSTALLATION SUMMARY:"
echo "────────────────────────────────────────────────────────────────"
echo "  Location: $INSTALL_DIR"
echo "  DHCP: ✅ Enabled by default"
echo "  Auto-Profiles: ✅ Generated"
if [ "$SYSTEM_INSTALL" = true ]; then
    echo "  Service: ✅ Systemd service created"
    echo "  Auto-Start: ✅ Enabled on boot"
fi
echo ""

echo "NETWORK CONFIGURATION:"
echo "────────────────────────────────────────────────────────────────"
IP_COUNT=0
for iface in "${INTERFACES[@]}"; do
    if ip link show "$iface" &>/dev/null; then
        IP=$(ip -4 addr show "$iface" | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
        if [ -n "$IP" ]; then
            echo "  ✅ $iface: $IP (DHCP)"
            IP_COUNT=$((IP_COUNT + 1))
        else
            echo "  ⚠️  $iface: No IP (no DHCP server on this network)"
        fi
    fi
done
echo ""

if [ $IP_COUNT -ge 2 ]; then
    PROFILE_COUNT=$((IP_COUNT * (IP_COUNT - 1)))
    echo "AUTO-GENERATED PROFILES:"
    echo "────────────────────────────────────────────────────────────────"
    echo "  ✅ $PROFILE_COUNT traffic profiles created automatically"
    echo "  📝 Profiles created between all interface pairs"
    echo "  🔒 Profiles start DISABLED (enable in GUI when ready)"
    echo ""
elif [ $IP_COUNT -eq 1 ]; then
    echo "AUTO-GENERATED PROFILES:"
    echo "────────────────────────────────────────────────────────────────"
    echo "  ⚠️  Only 1 interface has IP - need 2+ for auto-profiles"
    echo "  💡 Connect more networks with DHCP to auto-generate profiles"
    echo ""
else
    echo "AUTO-GENERATED PROFILES:"
    echo "────────────────────────────────────────────────────────────────"
    echo "  ⚠️  No interfaces have IPs - no DHCP servers detected"
    echo "  💡 Connect to networks with DHCP or configure static IPs"
    echo ""
fi

echo "NEXT STEPS:"
echo "────────────────────────────────────────────────────────────────"
echo ""

if [ "$SYSTEM_INSTALL" = true ]; then
    echo "1. Start VEP1445:"
    echo "   sudo systemctl start vep1445"
    echo ""
    echo "2. Access Web GUI:"
    echo "   http://localhost:5000"
    echo ""
    echo "3. Check Auto-Generated Profiles:"
    echo "   - Go to 'Traffic Profiles' tab"
    echo "   - See profiles named 'Auto_eno2_to_eno3', etc."
    echo "   - Enable the profiles you want to run"
    echo "   - Click 'Start Traffic'"
    echo ""
    echo "4. View Logs:"
    echo "   sudo journalctl -u vep1445 -f"
    echo ""
else
    echo "1. Start VEP1445:"
    echo "   cd $INSTALL_DIR"
    echo "   python3 web_api.py"
    echo ""
    echo "2. Access Web GUI:"
    echo "   http://localhost:5000"
    echo ""
fi

echo "FEATURES ENABLED:"
echo "────────────────────────────────────────────────────────────────"
echo "  ✅ DHCP client on all interfaces"
echo "  ✅ Auto-detection of IPs"
echo "  ✅ Auto-generation of traffic profiles"
echo "  ✅ Neighbor discovery (ARP/LLDP)"
echo "  ✅ Real-time statistics"
echo "  ✅ Web-based management"
echo ""

if [ $IP_COUNT -ge 2 ]; then
    echo "🎉 READY TO GENERATE TRAFFIC!"
    echo ""
    echo "Your VEP1445 has detected $IP_COUNT networks and created"
    echo "$PROFILE_COUNT bidirectional traffic profiles automatically."
    echo ""
    echo "Simply enable the profiles in the web GUI and start traffic!"
else
    echo "💡 TIP: Connect VEP1445 to more networks with DHCP"
    echo "        Auto-profiles will be generated automatically!"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
