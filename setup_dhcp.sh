#!/bin/bash
#
# VEP1445 DHCP Client Setup
# Enables DHCP on traffic generation interfaces
#

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  VEP1445 DHCP Client Setup                                    ║"
echo "║  Configure interfaces to obtain IP addresses via DHCP         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "Re-running with sudo..."
    exec sudo "$0" "$@"
fi

# Configuration
INTERFACES=("eno2" "eno3" "eno4" "eno5" "eno6")

echo "This will configure your VEP1445 interfaces to obtain IP addresses via DHCP."
echo ""
echo "Interfaces to configure:"
for iface in "${INTERFACES[@]}"; do
    echo "  - $iface"
done
echo ""

read -p "Continue? [Y/n]: " CONTINUE
if [[ "$CONTINUE" =~ ^[Nn]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " Step 1: Configure Network Manager / Netplan"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Detect if using NetworkManager or netplan
if systemctl is-active --quiet NetworkManager; then
    echo "Detected: NetworkManager"
    echo ""
    
    for iface in "${INTERFACES[@]}"; do
        if ip link show "$iface" &>/dev/null; then
            echo "Configuring $iface for DHCP via NetworkManager..."
            
            # Create NetworkManager connection
            nmcli connection delete "$iface" 2>/dev/null
            nmcli connection add type ethernet ifname "$iface" con-name "$iface" \
                ipv4.method auto \
                ipv6.method ignore \
                connection.autoconnect yes
            
            echo "  ✓ $iface configured for DHCP"
        fi
    done
    
elif [ -d "/etc/netplan" ]; then
    echo "Detected: Netplan"
    echo ""
    
    # Create netplan config
    cat > /etc/netplan/99-vep1445.yaml << 'EOF'
network:
  version: 2
  renderer: networkd
  ethernets:
EOF
    
    for iface in "${INTERFACES[@]}"; do
        if ip link show "$iface" &>/dev/null; then
            cat >> /etc/netplan/99-vep1445.yaml << EOF
    $iface:
      dhcp4: true
      dhcp6: false
EOF
            echo "  ✓ Added $iface to netplan config"
        fi
    done
    
    echo ""
    echo "Applying netplan configuration..."
    netplan apply
    echo "  ✓ Netplan applied"
    
else
    echo "Detected: Traditional /etc/network/interfaces"
    echo ""
    
    # Backup existing config
    cp /etc/network/interfaces /etc/network/interfaces.backup
    
    # Add DHCP configuration
    for iface in "${INTERFACES[@]}"; do
        if ip link show "$iface" &>/dev/null; then
            # Remove existing config for this interface
            sed -i "/iface $iface/d" /etc/network/interfaces
            
            # Add DHCP config
            cat >> /etc/network/interfaces << EOF

auto $iface
iface $iface inet dhcp
EOF
            echo "  ✓ Added $iface to /etc/network/interfaces"
        fi
    done
    
    echo ""
    echo "Restarting networking..."
    systemctl restart networking
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " Step 2: Bring Up Interfaces"
echo "═══════════════════════════════════════════════════════════════"
echo ""

for iface in "${INTERFACES[@]}"; do
    if ip link show "$iface" &>/dev/null; then
        echo "Bringing up $iface..."
        ip link set "$iface" up
        
        # Request DHCP
        if command -v dhclient &>/dev/null; then
            dhclient -v "$iface" &
        elif command -v dhcpcd &>/dev/null; then
            dhcpcd "$iface" &
        fi
        
        sleep 2
    fi
done

echo ""
echo "Waiting for DHCP leases..."
sleep 5

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " Step 3: Check IP Addresses Obtained"
echo "═══════════════════════════════════════════════════════════════"
echo ""

SUCCESS=0
TOTAL=0

for iface in "${INTERFACES[@]}"; do
    if ip link show "$iface" &>/dev/null; then
        TOTAL=$((TOTAL + 1))
        IP=$(ip -4 addr show "$iface" | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
        
        if [ -n "$IP" ]; then
            echo "  ✅ $iface: $IP"
            SUCCESS=$((SUCCESS + 1))
        else
            echo "  ⚠️  $iface: No IP address (DHCP failed or no DHCP server)"
        fi
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " Step 4: Update VEP1445 Configuration"
echo "═══════════════════════════════════════════════════════════════"
echo ""

INSTALL_DIR="/opt/vep1445-traffic-gen"

if [ -f "$INSTALL_DIR/web_api.py" ]; then
    echo "Creating IP address detection function..."
    
    cat > "$INSTALL_DIR/get_interface_info.py" << 'PYEOF'
"""
Get real interface information including IP addresses
"""
import subprocess
import re

def get_interface_info(interface_name):
    """Get MAC and IP address for interface"""
    info = {
        'name': interface_name,
        'mac': '00:00:00:00:00:00',
        'ip': None,
        'netmask': None
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
                # Convert CIDR to netmask
                mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
                info['netmask'] = '.'.join([str((mask >> (24 - i*8)) & 0xff) for i in range(4)])
    
    except Exception as e:
        pass
    
    return info

def get_all_interfaces():
    """Get info for all VEP1445 interfaces"""
    interfaces = []
    for iface in ['eno2', 'eno3', 'eno4', 'eno5', 'eno6']:
        info = get_interface_info(iface)
        interfaces.append(info)
    return interfaces
PYEOF
    
    echo "  ✓ Created get_interface_info.py"
    
    # Update web_api.py to use IP addresses
    echo "Updating web_api.py to detect IP addresses..."
    
    python3 << 'PYEOF'
import re

with open('/opt/vep1445-traffic-gen/web_api.py', 'r') as f:
    content = f.read()

# New initialize function that includes IP addresses
new_init = '''def initialize_default_config():
    """Initialize with real system interfaces including IP addresses"""
    import logging
    logger = logging.getLogger(__name__)
    
    import sys
    sys.path.insert(0, '/opt/vep1445-traffic-gen')
    from get_interface_info import get_all_interfaces
    
    interfaces = get_all_interfaces()
    
    for iface_info in interfaces:
        try:
            # Create interface config with real MAC and IP
            config = InterfaceConfig(
                name=iface_info['name'],
                mac_address=iface_info['mac'],
                ip_address=iface_info['ip'],
                subnet_mask=iface_info['netmask'],
                interface_type=InterfaceType.COPPER_OPTIMIZED,
                speed_mbps=1000
            )
            
            engine.add_interface(config)
            
            if iface_info['ip']:
                logger.info(f"Added {iface_info['name']}: MAC={iface_info['mac']}, IP={iface_info['ip']}")
            else:
                logger.info(f"Added {iface_info['name']}: MAC={iface_info['mac']}, IP=None (no DHCP)")
            
        except Exception as e:
            logger.error(f"Failed to add interface {iface_info['name']}: {e}")
    
    logger.info(f"Initialized {len(engine.interfaces)} interfaces")
'''

# Replace the function
pattern = r'def initialize_default_config\(\):.*?(?=\n(?:def |if __name__|app = Flask))'
content = re.sub(pattern, new_init, content, flags=re.DOTALL)

with open('/opt/vep1445-traffic-gen/web_api.py', 'w') as f:
    f.write(content)

print("  ✓ web_api.py updated to detect IP addresses")
PYEOF
    
    echo "  ✓ VEP1445 will now use real IP addresses"
else
    echo "  ⚠️  VEP1445 not installed at $INSTALL_DIR"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ✅ DHCP Setup Complete!                                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

echo "Results:"
echo "────────────────────────────────────────────────────────────────"
echo "  $SUCCESS out of $TOTAL interfaces obtained IP addresses"
echo ""

if [ $SUCCESS -eq 0 ]; then
    echo "⚠️  WARNING: No interfaces obtained IP addresses!"
    echo ""
    echo "Possible reasons:"
    echo "  - No DHCP server on the connected networks"
    echo "  - Cables not connected"
    echo "  - DHCP server not responding"
    echo "  - Need to wait longer for DHCP"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check cables are connected"
    echo "  2. Verify DHCP server is running on each LAN"
    echo "  3. Check DHCP server logs"
    echo "  4. Wait a bit longer, then check: ip addr show"
fi

echo "Interface Summary:"
echo "────────────────────────────────────────────────────────────────"
for iface in "${INTERFACES[@]}"; do
    if ip link show "$iface" &>/dev/null; then
        IP=$(ip -4 addr show "$iface" | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
        MAC=$(ip link show "$iface" | grep -oP '(?<=link/ether )[^ ]+')
        STATE=$(ip link show "$iface" | grep -oP '(?<=state )[^ ]+')
        
        echo "$iface:"
        echo "  MAC:   $MAC"
        echo "  IP:    ${IP:-None (no DHCP)}"
        echo "  State: $STATE"
        echo ""
    fi
done

echo "Next Steps:"
echo "────────────────────────────────────────────────────────────────"
echo "  1. Restart VEP1445 to use new IP addresses:"
echo "     sudo systemctl restart vep1445"
echo ""
echo "  2. Check web GUI shows IP addresses:"
echo "     http://localhost:5000"
echo ""
echo "  3. Create traffic profiles using real IPs:"
echo "     Source IP: (auto-filled from interface)"
echo "     Dest IP: IP on destination LAN"
echo ""

if [ $SUCCESS -gt 0 ]; then
    echo "  4. Your interfaces now have IPs - traffic will work!"
fi

echo ""
echo "To re-request DHCP manually:"
echo "  sudo dhclient -r eno2 && sudo dhclient eno2"
echo ""
