#!/bin/bash

# VEP1445 All-In-One Unified Installer
# Installs complete system with proper permissions and minimal sudo requirements

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
INSTALL_MODE="user"  # or "system"
INSTALL_DIR=""
LOG_DIR=""
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                                ║
║     VEP1445 All-In-One Unified Traffic Generator              ║
║                                                                ║
║     Copper (1G) + SFP (10G) | Single GUI Control              ║
║                                                                ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo ""
echo -e "${CYAN}Installation Mode Selection${NC}"
echo ""
echo "Choose installation location:"
echo ""
echo "  1) ${GREEN}User Home Directory${NC} (Recommended for testing/development)"
echo "     Location: ~/vep1445-traffic-gen"
echo "     Requires sudo: Only for network setup and performance config"
echo "     Best for: Development, testing, easy updates"
echo ""
echo "  2) ${YELLOW}System Directory${NC} (Recommended for production)"
echo "     Location: /opt/vep1445-traffic-gen"
echo "     Requires sudo: For installation and running"
echo "     Best for: Production, systemd service, multi-user"
echo ""
read -p "Enter choice [1-2] (default: 1): " MODE_CHOICE
MODE_CHOICE=${MODE_CHOICE:-1}

case $MODE_CHOICE in
    1)
        INSTALL_MODE="user"
        INSTALL_DIR="$HOME/vep1445-traffic-gen"
        LOG_DIR="$HOME/vep1445-traffic-gen/logs"
        echo -e "${GREEN}Selected: User Home Directory mode${NC}"
        ;;
    2)
        INSTALL_MODE="system"
        INSTALL_DIR="/opt/vep1445-traffic-gen"
        LOG_DIR="/var/log/vep1445"
        echo -e "${YELLOW}Selected: System Directory mode${NC}"
        
        if [ "$EUID" -ne 0 ]; then
            echo -e "${YELLOW}System mode requires root privileges${NC}"
            echo "Re-running with sudo..."
            exec sudo "$0" "$@"
        fi
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${CYAN}Installation Summary:${NC}"
echo "  Installation Directory: $INSTALL_DIR"
echo "  Log Directory: $LOG_DIR"
echo "  Installation Mode: $INSTALL_MODE"
echo "  Current User: $CURRENT_USER"
echo ""
read -p "Continue with installation? [y/N]: " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Installation cancelled"
    exit 0
fi

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Starting All-In-One Installation                             ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================

echo -e "${CYAN}[1/10] Checking system prerequisites...${NC}"

# Check OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "  OS: $NAME $VERSION"
else
    echo -e "${YELLOW}  Warning: Could not detect OS${NC}"
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}  ✗ Python 3 not found${NC}"
    echo "  Install with: sudo apt-get install python3 python3-pip"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "  Python: $PYTHON_VERSION"

PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}  ✗ Python 3.8+ required (found $PYTHON_VERSION)${NC}"
    exit 1
fi

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}  ⚠ pip3 not found, installing...${NC}"
    if [ "$INSTALL_MODE" = "system" ]; then
        apt-get install -y python3-pip > /dev/null 2>&1
    else
        echo -e "${RED}  ✗ Please install pip3: sudo apt-get install python3-pip${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}  ✓ Prerequisites OK${NC}"

# ============================================================================
# Step 2: Create Directories
# ============================================================================

echo ""
echo -e "${CYAN}[2/10] Creating directory structure...${NC}"

mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/web"
mkdir -p "$LOG_DIR"
mkdir -p "$INSTALL_DIR/config"
mkdir -p "$INSTALL_DIR/scripts"

if [ "$INSTALL_MODE" = "user" ]; then
    chmod 755 "$INSTALL_DIR"
    chmod 755 "$LOG_DIR"
else
    chown -R $SUDO_USER:$SUDO_USER "$INSTALL_DIR" 2>/dev/null || true
fi

echo "  Created: $INSTALL_DIR"
echo "  Created: $LOG_DIR"
echo -e "${GREEN}  ✓ Directories created${NC}"

# ============================================================================
# Step 3: Copy Files
# ============================================================================

echo ""
echo -e "${CYAN}[3/10] Copying application files...${NC}"

# Check if files exist in current directory
if [ ! -f "traffic_engine_unified.py" ]; then
    echo -e "${RED}  ✗ traffic_engine_unified.py not found in current directory${NC}"
    echo "  Please run this script from the directory containing all VEP1445 files"
    exit 1
fi

# Copy Python files
cp -v traffic_engine_unified.py "$INSTALL_DIR/" 2>&1 | sed 's/^/  /'
cp -v web_api.py "$INSTALL_DIR/" 2>&1 | sed 's/^/  /'

# Copy web files
cp -v web/index.html "$INSTALL_DIR/web/" 2>&1 | sed 's/^/  /'

# Copy configuration files
cp -v requirements_highperf.txt "$INSTALL_DIR/" 2>&1 | sed 's/^/  /'
cp -v sample_config.json "$INSTALL_DIR/config/" 2>&1 | sed 's/^/  /'

# Copy scripts
cp -v setup_performance.sh "$INSTALL_DIR/scripts/" 2>&1 | sed 's/^/  /'
chmod +x "$INSTALL_DIR/scripts/setup_performance.sh"

# Copy documentation
for doc in DEPLOYMENT_UNIFIED.md README_HIGHPERF.md PERFORMANCE_GUIDE.md \
           README.md QUICKSTART.md COMPLETE_FILE_LIST.md FILE_STRUCTURE.md; do
    if [ -f "$doc" ]; then
        cp -v "$doc" "$INSTALL_DIR/" 2>&1 | sed 's/^/  /'
    fi
done

echo -e "${GREEN}  ✓ Files copied${NC}"

# ============================================================================
# Step 4: Install Python Dependencies
# ============================================================================

echo ""
echo -e "${CYAN}[4/10] Installing Python dependencies...${NC}"

cd "$INSTALL_DIR"

if [ "$INSTALL_MODE" = "user" ]; then
    # User mode: install to user packages
    pip3 install --user -q -r requirements_highperf.txt
    echo "  Installed to user Python packages (~/.local)"
else
    # System mode: install globally
    pip3 install -q -r requirements_highperf.txt
    echo "  Installed to system Python packages"
fi

echo -e "${GREEN}  ✓ Dependencies installed${NC}"

# ============================================================================
# Step 5: Create Startup Scripts
# ============================================================================

echo ""
echo -e "${CYAN}[5/10] Creating startup scripts...${NC}"

# Create main startup script
cat > "$INSTALL_DIR/start.sh" << EOF
#!/bin/bash
# VEP1445 Startup Script

cd "$INSTALL_DIR"

# Check if running as root (needed for raw sockets)
if [ "\$EUID" -ne 0 ]; then
    echo "VEP1445 requires root privileges for raw socket access"
    echo "Restarting with sudo..."
    exec sudo "\$0" "\$@"
fi

# Start the application
echo "Starting VEP1445 Traffic Generator..."
echo "Web Interface: http://0.0.0.0:5000"
echo "Logs: $LOG_DIR"
echo ""

python3 web_api.py 2>&1 | tee -a "$LOG_DIR/vep1445.log"
EOF

chmod +x "$INSTALL_DIR/start.sh"

# Create stop script
cat > "$INSTALL_DIR/stop.sh" << EOF
#!/bin/bash
# VEP1445 Stop Script

echo "Stopping VEP1445 Traffic Generator..."
pkill -f "python3.*web_api.py"
echo "VEP1445 stopped"
EOF

chmod +x "$INSTALL_DIR/stop.sh"

# Create status script
cat > "$INSTALL_DIR/status.sh" << EOF
#!/bin/bash
# VEP1445 Status Script

if pgrep -f "python3.*web_api.py" > /dev/null; then
    echo "VEP1445 is running"
    echo ""
    echo "Process Info:"
    ps aux | grep "python3.*web_api.py" | grep -v grep
    echo ""
    echo "Web Interface: http://localhost:5000"
else
    echo "VEP1445 is not running"
fi
EOF

chmod +x "$INSTALL_DIR/status.sh"

echo "  Created: start.sh"
echo "  Created: stop.sh"
echo "  Created: status.sh"
echo -e "${GREEN}  ✓ Startup scripts created${NC}"

# ============================================================================
# Step 6: Network Capabilities (for user mode)
# ============================================================================

echo ""
echo -e "${CYAN}[6/10] Configuring network capabilities...${NC}"

if [ "$INSTALL_MODE" = "user" ]; then
    # Grant Python capability to create raw sockets without sudo
    PYTHON_PATH=$(which python3)
    
    if command -v setcap &> /dev/null; then
        echo "  Granting raw socket capability to Python..."
        sudo setcap cap_net_raw,cap_net_admin=eip "$PYTHON_PATH" || {
            echo -e "${YELLOW}  ⚠ Could not set capabilities${NC}"
            echo "  You'll need to run with sudo: sudo ./start.sh"
        }
        echo -e "${GREEN}  ✓ Network capabilities configured${NC}"
    else
        echo -e "${YELLOW}  ⚠ setcap not available${NC}"
        echo "  You'll need to run with sudo: sudo ./start.sh"
    fi
else
    echo "  System mode - will run with root privileges"
    echo -e "${GREEN}  ✓ Network capabilities OK${NC}"
fi

# ============================================================================
# Step 7: Create Desktop Shortcut (user mode only)
# ============================================================================

if [ "$INSTALL_MODE" = "user" ]; then
    echo ""
    echo -e "${CYAN}[7/10] Creating desktop shortcut...${NC}"
    
    DESKTOP_DIR="$HOME/Desktop"
    if [ -d "$DESKTOP_DIR" ]; then
        cat > "$DESKTOP_DIR/VEP1445.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=VEP1445 Traffic Generator
Comment=Start VEP1445 Unified Traffic Generator
Exec=$INSTALL_DIR/start.sh
Icon=network-server
Terminal=true
Categories=Network;System;
EOF
        chmod +x "$DESKTOP_DIR/VEP1445.desktop"
        echo -e "${GREEN}  ✓ Desktop shortcut created${NC}"
    else
        echo "  No desktop directory found, skipping"
    fi
else
    echo ""
    echo -e "${CYAN}[7/10] Skipping desktop shortcut (system mode)${NC}"
fi

# ============================================================================
# Step 8: Create Systemd Service (system mode only)
# ============================================================================

if [ "$INSTALL_MODE" = "system" ]; then
    echo ""
    echo -e "${CYAN}[8/10] Installing systemd service...${NC}"
    
    cat > /etc/systemd/system/vep1445.service << EOF
[Unit]
Description=VEP1445 Unified Traffic Generator
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/python3 $INSTALL_DIR/web_api.py
Restart=on-failure
RestartSec=10
StandardOutput=append:$LOG_DIR/vep1445.log
StandardError=append:$LOG_DIR/vep1445-error.log

# Network capabilities
AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN
CapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    
    echo -e "${GREEN}  ✓ Systemd service installed${NC}"
    echo "  Enable: sudo systemctl enable vep1445"
    echo "  Start:  sudo systemctl start vep1445"
else
    echo ""
    echo -e "${CYAN}[8/10] Skipping systemd service (user mode)${NC}"
fi

# ============================================================================
# Step 9: Check Network Interfaces
# ============================================================================

echo ""
echo -e "${CYAN}[9/10] Detecting network interfaces...${NC}"

# Detect copper interfaces
COPPER_COUNT=0
for i in {1..10}; do
    if ip link show eth$i &> /dev/null 2>&1; then
        echo "  ✓ Found: eth$i (copper)"
        ((COPPER_COUNT++))
    fi
done

# Detect SFP interfaces
SFP_COUNT=0
for i in {1..5}; do
    if ip link show sfp$i &> /dev/null 2>&1; then
        echo "  ✓ Found: sfp$i (SFP)"
        ((SFP_COUNT++))
    fi
done

# Detect other naming conventions
for iface in $(ip -o link show | awk -F': ' '{print $2}' | grep -E '^(enp|ens|eno)'); do
    SPEED=$(ethtool $iface 2>/dev/null | grep "Speed:" | awk '{print $2}')
    if [ ! -z "$SPEED" ]; then
        echo "  ℹ Found: $iface ($SPEED)"
    fi
done

if [ $COPPER_COUNT -eq 0 ] && [ $SFP_COUNT -eq 0 ]; then
    echo -e "${YELLOW}  ⚠ No expected interfaces found${NC}"
    echo "  You may need to adjust interface names in web_api.py"
else
    echo -e "${GREEN}  ✓ Found $COPPER_COUNT copper + $SFP_COUNT SFP interfaces${NC}"
fi

# ============================================================================
# Step 10: Performance Configuration
# ============================================================================

echo ""
echo -e "${CYAN}[10/10] Performance configuration...${NC}"

read -p "Configure system for high performance now? [y/N]: " PERF_CONFIG

if [[ "$PERF_CONFIG" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Select performance mode:"
    echo "  1) High-Performance (copper ports, 500Mbps-2Gbps)"
    echo "  2) DPDK (SFP ports, 2-10Gbps+) - requires reboot"
    echo "  3) Skip for now"
    read -p "Choice [1-3]: " PERF_CHOICE
    
    case $PERF_CHOICE in
        1)
            if [ -f "$INSTALL_DIR/scripts/setup_performance.sh" ]; then
                if [ "$INSTALL_MODE" = "user" ]; then
                    sudo "$INSTALL_DIR/scripts/setup_performance.sh" --mode high
                else
                    "$INSTALL_DIR/scripts/setup_performance.sh" --mode high
                fi
            fi
            ;;
        2)
            if [ -f "$INSTALL_DIR/scripts/setup_performance.sh" ]; then
                if [ "$INSTALL_MODE" = "user" ]; then
                    sudo "$INSTALL_DIR/scripts/setup_performance.sh" --mode dpdk
                else
                    "$INSTALL_DIR/scripts/setup_performance.sh" --mode dpdk
                fi
                echo -e "${YELLOW}  ⚠ Reboot required for DPDK mode${NC}"
            fi
            ;;
        *)
            echo "  Skipped - you can run later: ./scripts/setup_performance.sh"
            ;;
    esac
else
    echo "  Skipped - you can run later: ./scripts/setup_performance.sh"
fi

echo -e "${GREEN}  ✓ Performance configuration complete${NC}"

# ============================================================================
# Installation Complete
# ============================================================================

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║          Installation Complete!                                ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Installation Summary:${NC}"
echo "  Location: $INSTALL_DIR"
echo "  Logs: $LOG_DIR"
echo "  Mode: $INSTALL_MODE"
if [ "$INSTALL_MODE" = "user" ]; then
    echo "  Owner: $CURRENT_USER"
else
    echo "  Owner: root"
fi
echo ""

echo -e "${CYAN}Quick Start:${NC}"
echo ""

if [ "$INSTALL_MODE" = "user" ]; then
    echo "  ${GREEN}Start VEP1445:${NC}"
    echo "    cd $INSTALL_DIR"
    echo "    ./start.sh"
    echo ""
    echo "  ${GREEN}Stop VEP1445:${NC}"
    echo "    ./stop.sh"
    echo ""
    echo "  ${GREEN}Check Status:${NC}"
    echo "    ./status.sh"
    echo ""
    echo "  ${GREEN}Or use Desktop shortcut:${NC}"
    echo "    Double-click 'VEP1445' icon on desktop"
else
    echo "  ${GREEN}Start VEP1445:${NC}"
    echo "    sudo systemctl start vep1445"
    echo ""
    echo "  ${GREEN}Enable auto-start:${NC}"
    echo "    sudo systemctl enable vep1445"
    echo ""
    echo "  ${GREEN}Check Status:${NC}"
    echo "    sudo systemctl status vep1445"
    echo ""
    echo "  ${GREEN}View Logs:${NC}"
    echo "    sudo journalctl -u vep1445 -f"
fi

echo ""
echo -e "${CYAN}Web Interface:${NC}"
echo "  http://localhost:5000"
echo "  or"
echo "  http://$(hostname -I | awk '{print $1}'):5000"
echo ""

echo -e "${CYAN}Documentation:${NC}"
echo "  Quick Start:  cat $INSTALL_DIR/DEPLOYMENT_UNIFIED.md"
echo "  Full Docs:    cat $INSTALL_DIR/README_HIGHPERF.md"
echo "  File List:    cat $INSTALL_DIR/COMPLETE_FILE_LIST.md"
echo ""

echo -e "${CYAN}System Configuration:${NC}"
echo "  Detected Copper Ports: $COPPER_COUNT"
echo "  Detected SFP Ports: $SFP_COUNT"
echo ""

if [ "$INSTALL_MODE" = "user" ]; then
    echo -e "${YELLOW}Note:${NC} User mode requires sudo for first start (raw socket access)"
    echo "After granting capabilities, you can run without sudo"
fi

echo ""
echo -e "${GREEN}Ready to generate traffic!${NC}"
echo ""

# Return to original directory
cd "$CURRENT_DIR"
