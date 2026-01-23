#!/bin/bash

# Quick Fix for VEP1445 Installation
# Fixes the MAP_HUGETLB error and restarts the system

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}VEP1445 Quick Fix${NC}"
echo ""

# Check if we're root
if [ "$EUID" -ne 0 ]; then
    echo "Re-running with sudo..."
    exec sudo "$0" "$@"
fi

INSTALL_DIR="/opt/vep1445-traffic-gen"

if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}Error: $INSTALL_DIR not found${NC}"
    exit 1
fi

echo "Fixing MAP_HUGETLB compatibility issue..."

# Copy the fixed unified engine from source
SOURCE_DIR="/opt/netgen"
if [ -d "$SOURCE_DIR" ] && [ -f "$SOURCE_DIR/traffic_engine_unified.py" ]; then
    echo "Copying fixed traffic_engine_unified.py..."
    cp "$SOURCE_DIR/traffic_engine_unified.py" "$INSTALL_DIR/"
    echo -e "${GREEN}✓ Fixed file copied${NC}"
else
    echo -e "${RED}Error: Source files not found in $SOURCE_DIR${NC}"
    echo "Please ensure you have the latest files"
    exit 1
fi

echo ""
echo "Starting VEP1445..."
cd "$INSTALL_DIR"

# Stop any running instance
pkill -f "python3.*web_api.py" 2>/dev/null || true
sleep 1

# Start the service
echo ""
echo -e "${GREEN}Starting VEP1445 Traffic Generator...${NC}"
echo "Web Interface: http://localhost:5000"
echo ""

python3 web_api.py 2>&1 | tee -a /var/log/vep1445/vep1445.log
