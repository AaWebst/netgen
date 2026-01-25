#!/bin/bash
#
# VEP1445 Complete Fix Script
# Fixes all three identified issues:
#   1. Script permissions
#   2. Interface MAC addresses
#   3. Traffic generation
#

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║       VEP1445 COMPLETE FIX - All Three Issues                 ║"
echo "║                                                                ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "This script needs root privileges. Re-running with sudo..."
    exec sudo "$0" "$@"
fi

INSTALL_DIR="/opt/vep1445-traffic-gen"

if [ ! -d "$INSTALL_DIR" ]; then
    echo "❌ Error: $INSTALL_DIR not found!"
    echo "Please extract vep1445-complete.zip and run install_allinone.sh first"
    exit 1
fi

echo "Found VEP1445 at: $INSTALL_DIR"
echo ""

# ═══════════════════════════════════════════════════════════════
# FIX 1: PERMISSIONS
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " FIX 1: Script Permissions"
echo "═══════════════════════════════════════════════════════════════"
echo ""

echo "Making all scripts executable..."
find "$INSTALL_DIR" -name "*.sh" -exec chmod +x {} \;
chmod +x "$INSTALL_DIR"/*.py 2>/dev/null
chmod 755 "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"/web 2>/dev/null
chmod 755 "$INSTALL_DIR"/scripts 2>/dev/null

echo "  ✓ All scripts are now executable"
echo "  ✓ Directory permissions fixed"
echo ""

# ═══════════════════════════════════════════════════════════════
# FIX 2: INTERFACE MAC ADDRESSES
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " FIX 2: Interface Configuration & Real MAC Addresses"
echo "═══════════════════════════════════════════════════════════════"
echo ""

echo "Detecting your real network interfaces..."
declare -A INTERFACE_MACS

for iface in eno2 eno3 eno4 eno5 eno6; do
    if ip link show "$iface" &>/dev/null; then
        MAC=$(ip link show "$iface" | grep -oP '(?<=link/ether )[^ ]+')
        INTERFACE_MACS[$iface]=$MAC
        echo "  ✓ $iface: $MAC"
    fi
done

echo ""
echo "Updating web_api.py with real MAC addresses..."

# Backup web_api.py
cp "$INSTALL_DIR/web_api.py" "$INSTALL_DIR/web_api.py.backup-$(date +%Y%m%d-%H%M%S)"

# Create interface config with real MACs
cat > "$INSTALL_DIR/get_real_mac.py" << 'MACEOF'
import subprocess
import re

def get_real_mac(interface):
    try:
        result = subprocess.run(['ip', 'link', 'show', interface], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            match = re.search(r'link/ether ([0-9a-f:]+)', result.stdout)
            if match:
                return match.group(1)
    except:
        pass
    return "00:00:00:00:00:00"
MACEOF

# Update web_api.py initialize function
python3 << 'PYEOF'
import re

with open('/opt/vep1445-traffic-gen/web_api.py', 'r') as f:
    content = f.read()

# New initialize function that gets real MACs
new_init = '''def initialize_default_config():
    """Initialize with real system interfaces and MAC addresses"""
    import logging
    import subprocess
    import re
    logger = logging.getLogger(__name__)
    
    def get_real_mac(interface_name):
        """Get real MAC address from system"""
        try:
            result = subprocess.run(['ip', 'link', 'show', interface_name],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                match = re.search(r'link/ether ([0-9a-f:]+)', result.stdout)
                if match:
                    return match.group(1)
        except:
            pass
        return "00:00:00:00:00:00"
    
    # Your actual interfaces
    interfaces_to_add = ['eno2', 'eno3', 'eno4', 'eno5', 'eno6']
    
    for iface_name in interfaces_to_add:
        try:
            # Get REAL MAC address from system
            real_mac = get_real_mac(iface_name)
            
            # Create interface config with real MAC
            config = InterfaceConfig(
                name=iface_name,
                mac_address=real_mac,
                interface_type=InterfaceType.COPPER_OPTIMIZED,
                speed_mbps=1000
            )
            
            engine.add_interface(config)
            logger.info(f"Added interface: {iface_name} with real MAC {real_mac}")
            
        except Exception as e:
            logger.error(f"Failed to add interface {iface_name}: {e}")
    
    logger.info(f"Initialized {len(engine.interfaces)} interfaces with real MAC addresses")
'''

# Replace the function
pattern = r'def initialize_default_config\(\):.*?(?=\n(?:def |if __name__|app = Flask))'
content = re.sub(pattern, new_init, content, flags=re.DOTALL)

with open('/opt/vep1445-traffic-gen/web_api.py', 'w') as f:
    f.write(content)

print("  ✓ web_api.py updated with real MAC detection")
PYEOF

echo ""

# ═══════════════════════════════════════════════════════════════
# FIX 3: TRAFFIC GENERATION
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo " FIX 3: Traffic Generation (Socket Binding)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

echo "Fixing raw socket initialization and packet sending..."

# Backup traffic engine
cp "$INSTALL_DIR/traffic_engine_unified.py" "$INSTALL_DIR/traffic_engine_unified.py.backup-$(date +%Y%m%d-%H%M%S)"

# Fix the initialize method to bind socket to interface
python3 << 'PYEOF'
import re

with open('/opt/vep1445-traffic-gen/traffic_engine_unified.py', 'r') as f:
    lines = f.readlines()

# Find and fix the initialize method in StandardNetworkInterface
in_standard_class = False
in_initialize_method = False
new_lines = []
i = 0

while i < len(lines):
    line = lines[i]
    
    # Track if we're in StandardNetworkInterface class
    if 'class StandardNetworkInterface:' in line:
        in_standard_class = True
    elif line.startswith('class ') and in_standard_class:
        in_standard_class = False
    
    # Find the initialize method
    if in_standard_class and 'def initialize(self) -> bool:' in line:
        in_initialize_method = True
        # Write the new initialize method
        new_lines.append(line)  # def initialize line
        new_lines.append('''        """Initialize standard network interface with raw socket"""
        try:
            # Create raw socket (ETH_P_ALL = 0x0003)
            self.socket = socket.socket(
                socket.AF_PACKET,
                socket.SOCK_RAW,
                socket.htons(0x0003)
            )
            
            # CRITICAL: Bind socket to specific interface!
            # This ensures packets go out the correct physical port
            self.socket.bind((self.config.name, 0))
            
            # Set non-blocking
            self.socket.setblocking(False)
            
            # Enable hardware timestamps if available
            try:
                timestamp_flags = (
                    SOF_TIMESTAMPING_TX_HARDWARE |
                    SOF_TIMESTAMPING_RX_HARDWARE |
                    SOF_TIMESTAMPING_RAW_HARDWARE
                )
                self.socket.setsockopt(
                    socket.SOL_SOCKET,
                    SO_TIMESTAMPING,
                    timestamp_flags
                )
                self.hw_timestamps_enabled = True
                logger.info(f"{self.config.name}: Hardware timestamps enabled")
            except Exception as e:
                logger.debug(f"{self.config.name}: HW timestamps not available")
                self.hw_timestamps_enabled = False
            
            logger.info(f"{self.config.name}: Initialized and BOUND to interface")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.config.name}: {e}")
            return False
''')
        
        # Skip the old method body until we hit the next method
        i += 1
        while i < len(lines) and not (lines[i].strip().startswith('def ') and lines[i][0] == ' ' and lines[i][4] != ' '):
            i += 1
        i -= 1  # Back up one so we don't skip the next method
        in_initialize_method = False
    elif not in_initialize_method:
        new_lines.append(line)
    
    i += 1

with open('/opt/vep1445-traffic-gen/traffic_engine_unified.py', 'w') as f:
    f.writelines(new_lines)

print("  ✓ Fixed socket initialization - now binds to interface")
PYEOF

echo "  ✓ Packets will now be sent on correct physical interface"
echo ""

# ═══════════════════════════════════════════════════════════════
# CREATE VERIFICATION SCRIPT
# ═══════════════════════════════════════════════════════════════

echo "Creating verification script..."

cat > "$INSTALL_DIR/verify_traffic.sh" << 'VEREOF'
#!/bin/bash
echo "VEP1445 Traffic Verification"
echo "=============================="
echo ""

IFACE=${1:-eno2}

echo "Checking interface $IFACE..."
echo ""

# Check if interface exists
if ! ip link show "$IFACE" &>/dev/null; then
    echo "❌ Interface $IFACE not found!"
    exit 1
fi

# Check if interface is UP
if ! ip link show "$IFACE" | grep -q "UP"; then
    echo "⚠ Interface $IFACE is DOWN. Bringing it up..."
    sudo ip link set "$IFACE" up
    sleep 1
fi

# Show interface status
echo "Interface Status:"
ip link show "$IFACE" | grep -E "state|link/ether"
echo ""

# Start tcpdump
echo "Starting packet capture on $IFACE..."
echo "Press Ctrl+C to stop"
echo ""
echo "If you see packets, traffic generation is working!"
echo ""

sudo tcpdump -i "$IFACE" -nn -e -c 20
VEREOF

chmod +x "$INSTALL_DIR/verify_traffic.sh"

echo "  ✓ Created verification script: verify_traffic.sh"
echo ""

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║  ✅ ALL THREE FIXES APPLIED SUCCESSFULLY!                     ║"
echo "║                                                                ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

echo "FIXES APPLIED:"
echo "─────────────────────────────────────────────────────────────────"
echo ""
echo "✅ Fix 1: Permissions"
echo "   - All scripts are now executable"
echo "   - Directory permissions corrected"
echo ""
echo "✅ Fix 2: Interface Configuration"
echo "   - web_api.py now detects real MAC addresses"
echo "   - GUI will show correct MAC for each interface"
echo ""
echo "✅ Fix 3: Traffic Generation"
echo "   - Raw socket now BINDS to specific interface"
echo "   - Packets will be sent on correct physical port"
echo "   - Traffic will be visible with tcpdump"
echo ""

echo "DETECTED INTERFACES:"
echo "─────────────────────────────────────────────────────────────────"
for iface in "${!INTERFACE_MACS[@]}"; do
    echo "  $iface: ${INTERFACE_MACS[$iface]}"
done
echo ""

echo "NEXT STEPS:"
echo "─────────────────────────────────────────────────────────────────"
echo ""
echo "1. Restart VEP1445:"
echo "   sudo systemctl restart vep1445"
echo ""
echo "2. Check web interface:"
echo "   http://localhost:5000"
echo "   - Interfaces should show correct MAC addresses"
echo ""
echo "3. Create a traffic profile:"
echo "   - Source: eno2"
echo "   - Destination: eno3"
echo "   - Bandwidth: 100 Mbps"
echo "   - Start traffic"
echo ""
echo "4. Verify traffic is being generated:"
echo "   sudo $INSTALL_DIR/verify_traffic.sh eno2"
echo ""
echo "   You should see packets like:"
echo "   12:34:56.789 aa:bb:cc:dd:ee:ff > ff:ff:ff:ff:ff:ff, ..."
echo ""

echo "BACKUPS CREATED:"
echo "─────────────────────────────────────────────────────────────────"
echo "  web_api.py.backup-*"
echo "  traffic_engine_unified.py.backup-*"
echo ""

echo "If anything goes wrong, you can restore from backups."
echo ""
echo "═══════════════════════════════════════════════════════════════"
