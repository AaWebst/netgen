#!/bin/bash
# VEP1445 Uninstallation Script

set -e

echo "=============================================="
echo "VEP1445 Traffic Generator - Uninstallation"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

INSTALL_DIR="/opt/vep1445-traffic-gen"

# Confirm uninstallation
read -p "Are you sure you want to uninstall VEP1445? This will remove all files. (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Uninstallation cancelled."
    exit 0
fi

echo ""

# Stop service if running
echo "🛑 Stopping service..."
systemctl stop vep1445 2>/dev/null || true
systemctl disable vep1445 2>/dev/null || true
echo "✅ Service stopped"
echo ""

# Remove systemd service
echo "🗑️  Removing systemd service..."
rm -f /etc/systemd/system/vep1445.service
systemctl daemon-reload
echo "✅ Service removed"
echo ""

# Backup before removal
if [ -d "$INSTALL_DIR" ]; then
    BACKUP_DIR="/tmp/vep1445_backup_$(date +%Y%m%d_%H%M%S)"
    echo "📦 Creating backup at: $BACKUP_DIR"
    cp -r "$INSTALL_DIR" "$BACKUP_DIR"
    echo "✅ Backup created"
    echo ""
    
    # Remove installation directory
    echo "🗑️  Removing installation directory..."
    rm -rf "$INSTALL_DIR"
    echo "✅ Installation directory removed"
else
    echo "⚠️  Installation directory not found"
fi

echo ""
echo "=============================================="
echo "✅ Uninstallation Complete!"
echo "=============================================="
echo ""
echo "Backup saved to: $BACKUP_DIR"
echo "Runtime config preserved: /home/claude/vep1445_runtime_config.json"
echo ""
echo "To completely remove all data:"
echo "  rm -rf $BACKUP_DIR"
echo "  rm /home/claude/vep1445_runtime_config.json"
echo ""
