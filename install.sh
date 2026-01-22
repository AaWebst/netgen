#!/bin/bash

# VEP1445 Traffic Generator Installation Script
# This script installs and configures the VEP1445 traffic generation system

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     VEP1445 Multi-LAN Traffic Generator Installation          ║"
echo "║                                                                ║"
echo "║  Network Impairment & RFC2544 Testing Platform                ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Configuration
INSTALL_DIR="/opt/vep1445-traffic-gen"
LOG_DIR="/var/log/vep1445"
CURRENT_DIR=$(pwd)

echo -e "${CYAN}[1/8] Checking system requirements...${NC}"

# Check OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "  OS: $NAME $VERSION"
else
    echo -e "${YELLOW}  Warning: Could not detect OS version${NC}"
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo "  Python: $PYTHON_VERSION"
    
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        echo -e "${RED}ERROR: Python 3.8+ required. Found: $PYTHON_VERSION${NC}"
        exit 1
    fi
else
    echo -e "${RED}ERROR: Python 3 not found${NC}"
    echo "Install with: sudo apt-get install python3 python3-pip"
    exit 1
fi

echo -e "${GREEN}✓ System requirements OK${NC}"

echo -e "\n${CYAN}[2/8] Installing system dependencies...${NC}"

apt-get update -qq
apt-get install -y -qq python3-pip python3-dev build-essential > /dev/null 2>&1 || {
    echo -e "${RED}ERROR: Failed to install system dependencies${NC}"
    exit 1
}

echo -e "${GREEN}✓ System dependencies installed${NC}"

echo -e "\n${CYAN}[3/8] Creating directories...${NC}"

mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$INSTALL_DIR/web"

echo -e "${GREEN}✓ Directories created${NC}"

echo -e "\n${CYAN}[4/8] Copying application files...${NC}"

# Copy files
cp -v traffic_engine.py "$INSTALL_DIR/" 2>&1 | sed 's/^/  /'
cp -v web_api.py "$INSTALL_DIR/" 2>&1 | sed 's/^/  /'
cp -v requirements.txt "$INSTALL_DIR/" 2>&1 | sed 's/^/  /'
cp -v start_vep1445.sh "$INSTALL_DIR/" 2>&1 | sed 's/^/  /'
cp -rv web/* "$INSTALL_DIR/web/" 2>&1 | sed 's/^/  /'

chmod +x "$INSTALL_DIR/start_vep1445.sh"

echo -e "${GREEN}✓ Files copied${NC}"

echo -e "\n${CYAN}[5/8] Installing Python dependencies...${NC}"

cd "$INSTALL_DIR"
pip3 install -q -r requirements.txt || {
    echo -e "${RED}ERROR: Failed to install Python dependencies${NC}"
    exit 1
}

echo -e "${GREEN}✓ Python dependencies installed${NC}"

echo -e "\n${CYAN}[6/8] Setting up network capabilities...${NC}"

PYTHON_PATH=$(readlink -f $(which python3))
setcap cap_net_raw,cap_net_admin=eip "$PYTHON_PATH" || {
    echo -e "${YELLOW}  Warning: Could not set capabilities (will need to run as root)${NC}"
}

echo -e "${GREEN}✓ Network capabilities configured${NC}"

echo -e "\n${CYAN}[7/8] Installing systemd service...${NC}"

cp "$CURRENT_DIR/vep1445-traffic-gen.service" /etc/systemd/system/

systemctl daemon-reload
systemctl enable vep1445-traffic-gen.service

echo -e "${GREEN}✓ Systemd service installed${NC}"

echo -e "\n${CYAN}[8/8] Checking network interfaces...${NC}"

INTERFACES=("eth1" "eth2" "eth3" "eth4" "eth5")
FOUND=0

for iface in "${INTERFACES[@]}"; do
    if ip link show "$iface" &> /dev/null; then
        echo "  ✓ $iface found"
        ((FOUND++))
    else
        echo "  ✗ $iface not found"
    fi
done

if [ $FOUND -eq 0 ]; then
    echo -e "${YELLOW}"
    echo "  ⚠ Warning: No expected interfaces found"
    echo "  You may need to adjust interface names in $INSTALL_DIR/web_api.py"
    echo "  Edit the initialize_default_config() function"
    echo -e "${NC}"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗"
echo "║              Installation Complete!                            ║"
echo "╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo ""
echo "  1. Start the service:"
echo -e "     ${YELLOW}sudo systemctl start vep1445-traffic-gen${NC}"
echo ""
echo "  2. Check service status:"
echo -e "     ${YELLOW}sudo systemctl status vep1445-traffic-gen${NC}"
echo ""
echo "  3. Access web interface:"
echo -e "     ${YELLOW}http://<your-vep1445-ip>:5000${NC}"
echo "     or"
echo -e "     ${YELLOW}http://localhost:5000${NC}"
echo ""
echo "  4. View logs:"
echo -e "     ${YELLOW}tail -f /var/log/vep1445/traffic-gen.log${NC}"
echo ""
echo -e "${CYAN}Manual start (alternative):${NC}"
echo -e "  ${YELLOW}cd $INSTALL_DIR && sudo ./start_vep1445.sh${NC}"
echo ""
echo -e "${CYAN}Documentation:${NC}"
echo -e "  ${YELLOW}cat $INSTALL_DIR/README.md${NC}"
echo ""
echo -e "${GREEN}Installation directory: $INSTALL_DIR${NC}"
echo -e "${GREEN}Log directory: $LOG_DIR${NC}"
echo ""

# Return to original directory
cd "$CURRENT_DIR"
