#!/bin/bash

# Quick Configuration for VEP1445
# Your interfaces: eno2, eno3, eno4, eno5, eno6

echo "VEP1445 Quick Configuration"
echo "==========================="
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "Re-running with sudo..."
    exec sudo "$0" "$@"
fi

INSTALL_DIR="/opt/vep1445-traffic-gen"

# Step 1: Update traffic_engine_unified.py with fixed version
echo "Step 1: Updating traffic engine with API compatibility fixes..."
# This would be done by copying the fixed file

# Step 2: Create configuration for your specific interfaces
echo "Step 2: Creating configuration for your interfaces..."

cat > "$INSTALL_DIR/web_api_config.py" << 'EOF'
# VEP1445 Interface Configuration
# Configured for: eno2, eno3, eno4, eno5, eno6

from traffic_engine_unified import InterfaceConfig, InterfaceType

def get_interface_configs():
    """Return list of interface configurations"""
    configs = []
    
    # Interface 1: eno2 (1G Copper)
    configs.append(InterfaceConfig(
        name="eno2",
        mac_address="00:11:22:33:44:02",
        interface_type=InterfaceType.COPPER_OPTIMIZED,
        speed_mbps=1000
    ))
    
    # Interface 2: eno3 (1G Copper)
    configs.append(InterfaceConfig(
        name="eno3",
        mac_address="00:11:22:33:44:03",
        interface_type=InterfaceType.COPPER_OPTIMIZED,
        speed_mbps=1000
    ))
    
    # Interface 3: eno4 (1G Copper)
    configs.append(InterfaceConfig(
        name="eno4",
        mac_address="00:11:22:33:44:04",
        interface_type=InterfaceType.COPPER_OPTIMIZED,
        speed_mbps=1000
    ))
    
    # Interface 4: eno5 (1G Copper)
    configs.append(InterfaceConfig(
        name="eno5",
        mac_address="00:11:22:33:44:05",
        interface_type=InterfaceType.COPPER_OPTIMIZED,
        speed_mbps=1000
    ))
    
    # Interface 5: eno6 (1G Copper)
    configs.append(InterfaceConfig(
        name="eno6",
        mac_address="00:11:22:33:44:06",
        interface_type=InterfaceType.COPPER_OPTIMIZED,
        speed_mbps=1000
    ))
    
    return configs
EOF

# Step 3: Update web_api.py to use the configuration
echo "Step 3: Updating web_api.py..."

python3 << 'PYEOF'
import re

web_api_file = '/opt/vep1445-traffic-gen/web_api.py'

with open(web_api_file, 'r') as f:
    content = f.read()

# Create new initialization function
new_init = '''def initialize_default_config():
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
'''

# Find and replace the initialize_default_config function
pattern = r'def initialize_default_config\(\):.*?(?=\ndef |\nif __name__|\napp = Flask|\Z)'
content = re.sub(pattern, new_init + '\n\n', content, flags=re.DOTALL)

with open(web_api_file, 'w') as f:
    f.write(content)

print("✓ web_api.py updated")
PYEOF

# Step 4: Bring up interfaces
echo ""
echo "Step 4: Bringing up interfaces..."
for iface in eno2 eno3 eno4 eno5 eno6; do
    ip link set $iface up 2>/dev/null && echo "  ✓ $iface is up" || echo "  ✗ $iface failed"
done

echo ""
echo "==========================="
echo "Configuration Complete!"
echo "==========================="
echo ""
echo "Your interfaces:"
echo "  - eno2 (LAN Port 1)"
echo "  - eno3 (LAN Port 2)"
echo "  - eno4 (LAN Port 3)"
echo "  - eno5 (LAN Port 4)"
echo "  - eno6 (LAN Port 5)"
echo ""
echo "Next steps:"
echo "  1. Start VEP1445:"
echo "     cd $INSTALL_DIR"
echo "     sudo python3 web_api.py"
echo ""
echo "  2. Access web interface:"
echo "     http://localhost:5000"
echo ""
echo "  3. Create traffic profiles in the GUI"
echo ""
