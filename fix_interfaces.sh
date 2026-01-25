#!/bin/bash
#
# Fix VEP1445 Interface Configuration
# Detects real MAC addresses and updates web_api.py
#

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  VEP1445 Interface Configuration Fix                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "Re-running with sudo..."
    exec sudo "$0" "$@"
fi

INSTALL_DIR="/opt/vep1445-traffic-gen"

if [ ! -d "$INSTALL_DIR" ]; then
    echo "❌ Error: $INSTALL_DIR not found!"
    echo "Please run install_allinone.sh first"
    exit 1
fi

echo "Detecting your network interfaces..."
echo ""

# Detect interfaces and their real MAC addresses
declare -A INTERFACE_MACS

for iface in eno2 eno3 eno4 eno5 eno6; do
    if ip link show "$iface" &>/dev/null; then
        MAC=$(ip link show "$iface" | grep -oP '(?<=link/ether )[^ ]+')
        INTERFACE_MACS[$iface]=$MAC
        echo "  ✓ $iface: $MAC"
    else
        echo "  ✗ $iface: not found (will skip)"
    fi
done

echo ""
echo "Creating interface configuration with REAL MAC addresses..."

# Create the configuration file
cat > "$INSTALL_DIR/interface_config.py" << 'EOF'
"""
VEP1445 Interface Configuration
Auto-generated with real MAC addresses from the system
"""

def get_interface_list():
    """Return list of interfaces with real MAC addresses"""
    return [
EOF

# Add each detected interface
for iface in eno2 eno3 eno4 eno5 eno6; do
    if [ -n "${INTERFACE_MACS[$iface]}" ]; then
        cat >> "$INSTALL_DIR/interface_config.py" << EOF
        {
            'name': '$iface',
            'mac': '${INTERFACE_MACS[$iface]}',
            'type': 'COPPER_OPTIMIZED',
            'speed_mbps': 1000
        },
EOF
    fi
done

# Close the Python file
cat >> "$INSTALL_DIR/interface_config.py" << 'EOF'
    ]
EOF

echo "  ✓ Configuration created: $INSTALL_DIR/interface_config.py"
echo ""

# Now update web_api.py to use real MAC addresses
echo "Updating web_api.py to use real MAC addresses..."

# Backup original
cp "$INSTALL_DIR/web_api.py" "$INSTALL_DIR/web_api.py.backup"

# Create new initialize function with real MACs
python3 << PYEOF
import sys
sys.path.insert(0, '$INSTALL_DIR')
from interface_config import get_interface_list

# Read web_api.py
with open('$INSTALL_DIR/web_api.py', 'r') as f:
    content = f.read()

# Create new initialization code
init_code = '''def initialize_default_config():
    """Initialize with real system interfaces"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Load interface configuration
    import sys
    sys.path.insert(0, '/opt/vep1445-traffic-gen')
    from interface_config import get_interface_list
    
    interfaces = get_interface_list()
    
    for iface_config in interfaces:
        try:
            # Get real MAC address from system
            import subprocess
            result = subprocess.run(
                ['ip', 'link', 'show', iface_config['name']],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                import re
                mac_match = re.search(r'link/ether ([0-9a-f:]+)', result.stdout)
                real_mac = mac_match.group(1) if mac_match else iface_config['mac']
            else:
                real_mac = iface_config['mac']
            
            # Create interface config
            config = InterfaceConfig(
                name=iface_config['name'],
                mac_address=real_mac,
                interface_type=InterfaceType.COPPER_OPTIMIZED,
                speed_mbps=iface_config['speed_mbps']
            )
            
            engine.add_interface(config)
            logger.info(f"Added interface: {iface_config['name']} with MAC {real_mac}")
            
        except Exception as e:
            logger.error(f"Failed to add interface {iface_config['name']}: {e}")
    
    logger.info(f"Initialized {len(engine.interfaces)} interfaces")
'''

# Find and replace initialize_default_config
import re
pattern = r'def initialize_default_config\(\):.*?(?=\ndef |\nif __name__|\napp = Flask|\Z)'
content = re.sub(pattern, init_code + '\n\n', content, flags=re.DOTALL)

# Write updated file
with open('$INSTALL_DIR/web_api.py', 'w') as f:
    f.write(content)

print("  ✓ web_api.py updated with real MAC addresses")
PYEOF

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ✅ Interface Configuration Fix Complete!                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Detected interfaces:"
for iface in "${!INTERFACE_MACS[@]}"; do
    echo "  $iface: ${INTERFACE_MACS[$iface]}"
done
echo ""
echo "Next steps:"
echo "  1. Restart VEP1445: sudo systemctl restart vep1445"
echo "  2. Check web GUI: http://localhost:5000"
echo "  3. Interfaces should now show correct MAC addresses"
echo ""
