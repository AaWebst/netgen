#!/bin/bash
#
# Fix VEP1445 Permissions
# Run this to fix script permissions and file ownership
#

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  VEP1445 Permission Fix Script                                ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "Re-running with sudo..."
    exec sudo "$0" "$@"
fi

# Detect installation directory
if [ -d "/opt/vep1445-traffic-gen" ]; then
    INSTALL_DIR="/opt/vep1445-traffic-gen"
elif [ -d "/opt/vep1445-complete" ]; then
    INSTALL_DIR="/opt/vep1445-complete"
elif [ -d "$HOME/vep1445-traffic-gen" ]; then
    INSTALL_DIR="$HOME/vep1445-traffic-gen"
else
    echo "❌ Error: VEP1445 installation not found!"
    echo ""
    echo "Expected locations:"
    echo "  - /opt/vep1445-traffic-gen"
    echo "  - /opt/vep1445-complete"
    echo "  - $HOME/vep1445-traffic-gen"
    exit 1
fi

echo "Found VEP1445 at: $INSTALL_DIR"
echo ""

# Fix script permissions
echo "1. Making all scripts executable..."
chmod +x "$INSTALL_DIR"/*.sh 2>/dev/null
chmod +x "$INSTALL_DIR"/scripts/*.sh 2>/dev/null
echo "   ✓ Scripts are now executable"

# Fix Python file permissions
echo "2. Setting Python file permissions..."
chmod 644 "$INSTALL_DIR"/*.py 2>/dev/null
echo "   ✓ Python files readable"

# Fix web file permissions
echo "3. Setting web file permissions..."
chmod 644 "$INSTALL_DIR"/web/*.html 2>/dev/null
chmod 644 "$INSTALL_DIR"/web/*.js 2>/dev/null
chmod 644 "$INSTALL_DIR"/web/*.css 2>/dev/null
echo "   ✓ Web files readable"

# Fix directory permissions
echo "4. Setting directory permissions..."
chmod 755 "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"/web 2>/dev/null
chmod 755 "$INSTALL_DIR"/scripts 2>/dev/null
chmod 755 "$INSTALL_DIR"/docs 2>/dev/null
echo "   ✓ Directories accessible"

# Create log directory
echo "5. Creating log directory..."
mkdir -p /var/log/vep1445
chmod 755 /var/log/vep1445
echo "   ✓ Log directory created"

# Fix ownership (optional, if running as specific user)
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    echo "6. Setting ownership to $SUDO_USER..."
    chown -R $SUDO_USER:$SUDO_USER "$INSTALL_DIR"
    chown -R $SUDO_USER:$SUDO_USER /var/log/vep1445
    echo "   ✓ Ownership set to $SUDO_USER"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ✅ Permission Fix Complete!                                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "You can now run scripts:"
echo "  cd $INSTALL_DIR"
echo "  ./install_allinone.sh"
echo "  ./scripts/quick_config.sh"
echo ""
