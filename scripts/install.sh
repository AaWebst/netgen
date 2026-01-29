#!/bin/bash
# VEP1445 Installation Script
# Installs all files with correct permissions and structure

set -e

echo "==========================================="
echo "VEP1445 Traffic Generator - Installation"
echo "==========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run as root (sudo)"
    exit 1
fi

INSTALL_DIR="/opt/vep1445-traffic-gen"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "Installation directory: $INSTALL_DIR"
echo "Source directory: $CURRENT_DIR"
echo ""

# Backup existing installation
if [ -d "$INSTALL_DIR" ]; then
    BACKUP_DIR="${INSTALL_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
    echo "Backing up existing installation to: $BACKUP_DIR"
    mv "$INSTALL_DIR" "$BACKUP_DIR"
fi

# Create directory structure
echo "Creating directory structure..."
mkdir -p "$INSTALL_DIR"/{protocols/{tcp,http,dns,ipv6,sip,bgp},monitoring/{snmp,netflow},testing/{qos,impairments,pcap,imix},utils,docs,config,scripts,logs}

# Copy files
echo "Copying files..."

# Main engine
cp -v "$CURRENT_DIR/vep1445_engine.py" "$INSTALL_DIR/"

# Protocols
cp -v "$CURRENT_DIR/protocols/tcp/"*.py "$INSTALL_DIR/protocols/tcp/" 2>/dev/null || true
cp -v "$CURRENT_DIR/protocols/http/"*.py "$INSTALL_DIR/protocols/http/" 2>/dev/null || true
cp -v "$CURRENT_DIR/protocols/dns/"*.py "$INSTALL_DIR/protocols/dns/" 2>/dev/null || true
cp -v "$CURRENT_DIR/protocols/ipv6/"*.py "$INSTALL_DIR/protocols/ipv6/" 2>/dev/null || true
cp -v "$CURRENT_DIR/protocols/sip/"*.py "$INSTALL_DIR/protocols/sip/" 2>/dev/null || true
cp -v "$CURRENT_DIR/protocols/bgp/"*.py "$INSTALL_DIR/protocols/bgp/" 2>/dev/null || true

# Monitoring
cp -v "$CURRENT_DIR/monitoring/snmp/"*.py "$INSTALL_DIR/monitoring/snmp/" 2>/dev/null || true
cp -v "$CURRENT_DIR/monitoring/netflow/"*.py "$INSTALL_DIR/monitoring/netflow/" 2>/dev/null || true

# Testing
cp -v "$CURRENT_DIR/testing/qos/"*.py "$INSTALL_DIR/testing/qos/" 2>/dev/null || true
cp -v "$CURRENT_DIR/testing/impairments/"*.py "$INSTALL_DIR/testing/impairments/" 2>/dev/null || true
cp -v "$CURRENT_DIR/testing/pcap/"*.py "$INSTALL_DIR/testing/pcap/" 2>/dev/null || true
cp -v "$CURRENT_DIR/testing/imix/"*.py "$INSTALL_DIR/testing/imix/" 2>/dev/null || true

# Config and docs
cp -v "$CURRENT_DIR/config/"*.yaml "$INSTALL_DIR/config/" 2>/dev/null || true
cp -v "$CURRENT_DIR/docs/"*.txt "$INSTALL_DIR/docs/" 2>/dev/null || true

# Scripts
cp -v "$CURRENT_DIR/scripts/"*.sh "$INSTALL_DIR/scripts/" 2>/dev/null || true

echo ""
echo "Setting permissions..."

# Set ownership
chown -R root:root "$INSTALL_DIR"

# Set directory permissions (755 = rwxr-xr-x)
find "$INSTALL_DIR" -type d -exec chmod 755 {} \;

# Set file permissions
# Python files: 644 (rw-r--r--)
find "$INSTALL_DIR" -type f -name "*.py" -exec chmod 644 {} \;

# Main engine: 755 (executable)
chmod 755 "$INSTALL_DIR/vep1445_engine.py"

# Scripts: 755 (executable)
find "$INSTALL_DIR/scripts" -type f -name "*.sh" -exec chmod 755 {} \;

# Config files: 644 (read-only for non-root)
find "$INSTALL_DIR/config" -type f -exec chmod 644 {} \;

# Docs: 644
find "$INSTALL_DIR/docs" -type f -exec chmod 644 {} \;

# Logs directory: 777 (writable by all)
chmod 777 "$INSTALL_DIR/logs"

echo ""
echo "Creating Python package markers..."
find "$INSTALL_DIR" -type d -name "protocols" -o -name "monitoring" -o -name "testing" -o -name "tcp" -o -name "http" -o -name "dns" -o -name "ipv6" -o -name "sip" -o -name "bgp" -o -name "snmp" -o -name "netflow" -o -name "qos" -o -name "impairments" -o -name "pcap" -o -name "imix" | while read dir; do
    touch "$dir/__init__.py"
    chmod 644 "$dir/__init__.py"
done

echo ""
echo "Creating systemd service..."

cat > /etc/systemd/system/vep1445.service << 'EOF'
[Unit]
Description=VEP1445 Traffic Generator
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vep1445-traffic-gen
ExecStart=/usr/bin/python3 /opt/vep1445-traffic-gen/vep1445_engine.py
Restart=on-failure
RestartSec=5s
StandardOutput=append:/opt/vep1445-traffic-gen/logs/vep1445.log
StandardError=append:/opt/vep1445-traffic-gen/logs/vep1445-error.log

[Install]
WantedBy=multi-user.target
EOF

chmod 644 /etc/systemd/system/vep1445.service
systemctl daemon-reload

echo ""
echo "==========================================="
echo "Installation Complete!"
echo "==========================================="
echo ""
echo "Installation directory: $INSTALL_DIR"
echo ""
echo "Next steps:"
echo "  1. Edit config file:"
echo "     nano $INSTALL_DIR/config/static_config.yaml"
echo ""
echo "  2. Test the engine:"
echo "     cd $INSTALL_DIR"
echo "     python3 vep1445_engine.py"
echo ""
echo "  3. Enable service (optional):"
echo "     systemctl enable vep1445"
echo "     systemctl start vep1445"
echo ""
echo "  4. View logs:"
echo "     tail -f $INSTALL_DIR/logs/vep1445.log"
echo ""
echo "Documentation: $INSTALL_DIR/docs/"
echo ""
