#!/bin/bash

# VEP1445 Interface Configuration Generator
# Run this after unbinding interfaces from DPDK

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}VEP1445 Configuration Generator${NC}"
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "Re-running with sudo..."
    exec sudo "$0" "$@"
fi

INSTALL_DIR="/opt/vep1445-traffic-gen"

if [ ! -d "$INSTALL_DIR" ]; then
    echo "Error: VEP1445 not installed at $INSTALL_DIR"
    exit 1
fi

echo "Detecting network interfaces..."
echo ""

# Get kernel interfaces (exclude loopback and wireless)
INTERFACES=($(ip -o link show | awk -F': ' '{print $2}' | grep -v '^lo$' | grep -v '^wl'))

echo -e "${GREEN}Found ${#INTERFACES[@]} network interfaces:${NC}"
echo ""

# Display interfaces with details
for i in "${!INTERFACES[@]}"; do
    iface="${INTERFACES[$i]}"
    SPEED=$(ethtool $iface 2>/dev/null | grep "Speed:" | awk '{print $2}' | tr -d 'Mb/s' | tr -d 'Gb/s')
    DRIVER=$(ethtool -i $iface 2>/dev/null | grep "driver:" | awk '{print $2}')
    MAC=$(ip link show $iface | grep -oP '(?<=link/ether )[^ ]+')
    STATE=$(ip link show $iface | grep -oP '(?<=state )[^ ]+')
    
    # Determine type
    if [[ "$SPEED" == "10000" ]] || [[ "$SPEED" == "10G"* ]]; then
        TYPE="10G SFP"
        ITYPE="SFP_10G_DPDK"
    else
        TYPE="1G Copper"
        ITYPE="COPPER_OPTIMIZED"
    fi
    
    echo "  [$i] $iface"
    echo "      Type: $TYPE"
    echo "      Speed: $SPEED"
    echo "      Driver: $DRIVER"
    echo "      MAC: $MAC"
    echo "      State: $STATE"
    echo ""
done

echo ""
echo -e "${YELLOW}Select interfaces to use for VEP1445:${NC}"
echo "(Enter interface numbers separated by spaces, e.g., '0 1 2 3 4')"
echo "(Or press Enter to use all interfaces)"
echo ""
read -p "Interfaces to use: " SELECTED

if [ -z "$SELECTED" ]; then
    # Use all interfaces
    SELECTED_IFACES=("${INTERFACES[@]}")
else
    # Use selected interfaces
    SELECTED_IFACES=()
    for idx in $SELECTED; do
        if [ "$idx" -ge 0 ] && [ "$idx" -lt "${#INTERFACES[@]}" ]; then
            SELECTED_IFACES+=("${INTERFACES[$idx]}")
        fi
    done
fi

echo ""
echo -e "${GREEN}Selected ${#SELECTED_IFACES[@]} interfaces:${NC}"
for iface in "${SELECTED_IFACES[@]}"; do
    echo "  - $iface"
done
echo ""

# Generate Python configuration
echo "Generating configuration..."

CONFIG_FILE="$INSTALL_DIR/web_api_config.py"

cat > "$CONFIG_FILE" << 'PYEOF'
# VEP1445 Custom Interface Configuration
# Auto-generated based on detected hardware

from traffic_engine_unified import InterfaceConfig, InterfaceType

def get_interface_configs():
    """Return list of interface configurations"""
    configs = []
    
PYEOF

# Add each interface
for i in "${!SELECTED_IFACES[@]}"; do
    iface="${SELECTED_IFACES[$i]}"
    MAC=$(ip link show $iface | grep -oP '(?<=link/ether )[^ ]+')
    SPEED=$(ethtool $iface 2>/dev/null | grep "Speed:" | awk '{print $2}' | tr -d 'Mb/s' | tr -d 'Gb/s')
    
    # Determine interface type
    if [[ "$SPEED" == "10000" ]] || [[ "$SPEED" == "10G"* ]]; then
        ITYPE="InterfaceType.SFP_10G_OPTIMIZED"  # Use optimized, not DPDK since we unbound
        SPEED_MBPS="10000"
    else
        ITYPE="InterfaceType.COPPER_OPTIMIZED"
        SPEED_MBPS="1000"
    fi
    
    cat >> "$CONFIG_FILE" << PYEOF
    # Interface $((i+1)): $iface
    configs.append(InterfaceConfig(
        name="$iface",
        mac_address="$MAC",
        interface_type=$ITYPE,
        speed_mbps=$SPEED_MBPS
    ))
    
PYEOF
done

cat >> "$CONFIG_FILE" << 'PYEOF'
    return configs
PYEOF

echo "Configuration saved to: $CONFIG_FILE"
echo ""

# Update web_api.py to use custom config
echo "Updating web_api.py..."

# Backup original
cp "$INSTALL_DIR/web_api.py" "$INSTALL_DIR/web_api.py.backup"

# Create new initialization function
cat > /tmp/new_init.py << 'PYEOF'
def initialize_default_config():
    """Initialize with detected interfaces"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Import custom configuration
    import sys
    sys.path.insert(0, '/opt/vep1445-traffic-gen')
    from web_api_config import get_interface_configs
    
    # Add each configured interface
    configs = get_interface_configs()
    for config in configs:
        try:
            engine.add_interface(config)
            logger.info(f"Added interface: {config.name} ({config.interface_type.value})")
        except Exception as e:
            logger.error(f"Failed to add interface {config.name}: {e}")
    
    logger.info(f"Initialized {len(engine.interfaces)} interfaces")
    
    # Try to initialize interfaces with network discovery
    try:
        for name in engine.interfaces.keys():
            logger.info(f"  {name}: ready")
    except Exception as e:
        logger.warning(f"Could not fully initialize interfaces: {e}")
        logger.info("This is normal if running outside actual hardware environment")
PYEOF

# Replace the initialization function in web_api.py
python3 << 'ENDPYTHON'
import re

with open('/opt/vep1445-traffic-gen/web_api.py', 'r') as f:
    content = f.read()

with open('/tmp/new_init.py', 'r') as f:
    new_init = f.read()

# Find and replace the initialize_default_config function
pattern = r'def initialize_default_config\(\):.*?(?=\ndef |\nif __name__|\napp = Flask|\Z)'
content = re.sub(pattern, new_init + '\n\n', content, flags=re.DOTALL)

with open('/opt/vep1445-traffic-gen/web_api.py', 'w') as f:
    f.write(content)

print("Updated web_api.py")
ENDPYTHON

echo ""
echo -e "${GREEN}✓ Configuration complete!${NC}"
echo ""
echo "Interface configuration:"
for iface in "${SELECTED_IFACES[@]}"; do
    SPEED=$(ethtool $iface 2>/dev/null | grep "Speed:" | awk '{print $2}')
    echo "  $iface - $SPEED"
done
echo ""

echo -e "${CYAN}Next steps:${NC}"
echo ""
echo "1. Bring up interfaces:"
for iface in "${SELECTED_IFACES[@]}"; do
    echo "   sudo ip link set $iface up"
done
echo ""
echo "2. Start VEP1445:"
echo "   cd $INSTALL_DIR"
echo "   sudo python3 web_api.py"
echo ""
echo "3. Access web interface:"
echo "   http://localhost:5000"
echo ""

# Offer to bring up interfaces now
read -p "Bring up interfaces now? [Y/n]: " BRINGUP

if [[ ! "$BRINGUP" =~ ^[Nn]$ ]]; then
    echo ""
    echo "Bringing up interfaces..."
    for iface in "${SELECTED_IFACES[@]}"; do
        ip link set "$iface" up
        echo "  ✓ $iface is up"
    done
    echo ""
    echo -e "${GREEN}All interfaces are up!${NC}"
fi

echo ""
read -p "Start VEP1445 now? [Y/n]: " STARTNOW

if [[ ! "$STARTNOW" =~ ^[Nn]$ ]]; then
    echo ""
    echo -e "${GREEN}Starting VEP1445...${NC}"
    echo "Web Interface: http://localhost:5000"
    echo ""
    cd "$INSTALL_DIR"
    exec python3 web_api.py
fi
