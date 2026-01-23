#!/bin/bash

# VEP1445 Interface Detection and Configuration
# Detects actual network interfaces on the system

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}VEP1445 Interface Detection${NC}"
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "Re-running with sudo..."
    exec sudo "$0" "$@"
fi

echo "Detecting network interfaces..."
echo ""

echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Kernel Driver Interfaces (Normal Linux)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

# Find kernel interfaces
for iface in $(ip -o link show | awk -F': ' '{print $2}' | grep -v '^lo$'); do
    SPEED=$(ethtool $iface 2>/dev/null | grep "Speed:" | awk '{print $2}' || echo "Unknown")
    DRIVER=$(ethtool -i $iface 2>/dev/null | grep "driver:" | awk '{print $2}' || echo "Unknown")
    STATE=$(ip link show $iface | grep -oP '(?<=state )[^ ]+' || echo "UNKNOWN")
    
    echo -e "${GREEN}Interface: $iface${NC}"
    echo "  Driver: $DRIVER"
    echo "  Speed: $SPEED"
    echo "  State: $STATE"
    echo ""
done

echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}DPDK-Bound Interfaces (Kernel Bypass)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

if command -v dpdk-devbind.py &> /dev/null; then
    dpdk-devbind.py --status | grep -A 50 "Network devices using DPDK-compatible driver"
else
    echo "DPDK not installed or dpdk-devbind.py not in PATH"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Recommended Configuration${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo ""

# Count interfaces
KERNEL_COUNT=$(ip -o link show | awk -F': ' '{print $2}' | grep -v '^lo$' | wc -l)
DPDK_COUNT=$(dpdk-devbind.py --status 2>/dev/null | grep -c "drv=vfio-pci" || echo 0)

echo "Found:"
echo "  - $KERNEL_COUNT kernel-driven interfaces"
echo "  - $DPDK_COUNT DPDK-bound interfaces"
echo ""

# Get the actual interface that's up
MGMT_IFACE=$(ip -o link show | awk -F': ' '{print $2}' | grep -v '^lo$' | head -1)

echo -e "${YELLOW}Current VEP1445 Configuration Issue:${NC}"
echo "  VEP1445 is configured for: eth1-eth5, sfp1-sfp2"
echo "  Your system has: $MGMT_IFACE and DPDK-bound interfaces"
echo ""
echo -e "${YELLOW}You need to update web_api.py to match YOUR interfaces${NC}"
echo ""

# Create a configuration file
CONFIG_FILE="/tmp/vep1445_interface_config.py"

cat > "$CONFIG_FILE" << 'EOF'
# VEP1445 Interface Configuration for Your System
# Copy this configuration to web_api.py

def initialize_default_config():
    """Initialize with detected interfaces"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Option 1: Use kernel interface (if available)
    # Uncomment and adjust interface name:
    # config = InterfaceConfig(
    #     name="eno1",  # YOUR KERNEL INTERFACE NAME
    #     mac_address="00:11:22:33:44:01",
    #     interface_type=InterfaceType.COPPER_OPTIMIZED,
    #     speed_mbps=1000
    # )
    # engine.add_interface(config)
    
    # Option 2: Use DPDK interfaces
    # For each DPDK-bound interface, create a config:
    
    # Example for 10G SFP (adjust PCI addresses):
    # config = InterfaceConfig(
    #     name="dpdk0",
    #     mac_address="00:11:22:33:55:01",
    #     interface_type=InterfaceType.SFP_10G_DPDK,
    #     speed_mbps=10000,
    #     pci_address="0000:05:00.0"  # YOUR ACTUAL PCI ADDRESS
    # )
    # engine.add_interface(config)
    
    logger.info(f"Initialized {len(engine.interfaces)} interfaces")
EOF

echo "Configuration template created: $CONFIG_FILE"
echo ""

echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Next Steps${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
echo "1. Decide which interfaces to use:"
echo ""
echo "   Option A: Use kernel interface (eno1)"
echo "   - Unbind from DPDK: dpdk-devbind.py -u 0000:02:00.2"
echo "   - Bind to kernel: dpdk-devbind.py -b igb 0000:02:00.2"
echo "   - Configure in web_api.py as 'eno1'"
echo ""
echo "   Option B: Use DPDK interfaces"
echo "   - Keep DPDK bindings"
echo "   - Configure in web_api.py with PCI addresses"
echo "   - Requires EAL initialization"
echo ""
echo "2. Edit /opt/vep1445-traffic-gen/web_api.py"
echo "   - Replace initialize_default_config() function"
echo "   - Use actual interface names from above"
echo ""
echo "3. Restart VEP1445"
echo "   sudo systemctl restart vep1445"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}IMPORTANT QUESTION:${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
echo ""
echo "What do you want VEP1445 to do?"
echo ""
echo "A) Generate test traffic between interfaces (traffic generator)"
echo "   - Creates synthetic packets for testing"
echo "   - Tests network performance"
echo "   - Does NOT route real traffic"
echo ""
echo "B) Route real traffic between LANs (router/gateway)"
echo "   - Forward packets between networks"
echo "   - Need different software (iptables, Linux routing)"
echo "   - VEP1445 is NOT designed for this"
echo ""
echo "Please clarify your use case!"
echo ""
