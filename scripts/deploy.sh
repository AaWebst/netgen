#!/bin/bash

# VEP1445 Simple Deployment Script
# Handles git clone naming and sets up the system

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                                ║
║     VEP1445 Quick Deploy                                       ║
║                                                                ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if we're in the right directory
if [ ! -f "install_allinone.sh" ]; then
    echo -e "${RED}Error: install_allinone.sh not found${NC}"
    echo "Please run this script from the netgen directory"
    echo ""
    echo "If you just cloned from git:"
    echo "  cd /opt/netgen"
    echo "  sudo bash deploy.sh"
    exit 1
fi

CURRENT_DIR=$(pwd)
CURRENT_NAME=$(basename "$CURRENT_DIR")

echo -e "${CYAN}Current directory: $CURRENT_DIR${NC}"
echo -e "${CYAN}Directory name: $CURRENT_NAME${NC}"
echo ""

# If we're in /opt/netgen, offer to run installer from here
if [ "$CURRENT_DIR" = "/opt/netgen" ]; then
    echo -e "${GREEN}✓ You're in /opt/netgen${NC}"
    echo ""
    echo "The installer will:"
    echo "  1. Keep files in /opt/netgen (no copy needed)"
    echo "  2. Set up startup scripts"
    echo "  3. Install dependencies"
    echo "  4. Configure performance"
    echo ""
    read -p "Run installer now? [Y/n]: " RUN_INSTALLER
    
    if [[ ! "$RUN_INSTALLER" =~ ^[Nn]$ ]]; then
        chmod +x install_allinone.sh
        
        # Run installer with system mode pre-selected
        echo ""
        echo -e "${CYAN}Running installer...${NC}"
        echo -e "${YELLOW}Tip: Choose 'System Directory' mode since you're already in /opt${NC}"
        echo ""
        
        exec ./install_allinone.sh
    fi
else
    echo -e "${YELLOW}You're in: $CURRENT_DIR${NC}"
    echo ""
    echo "Run the installer:"
    echo "  chmod +x install_allinone.sh"
    echo "  ./install_allinone.sh"
fi
