#!/bin/bash
# VEP1445 Installation Script
# Installs the VEP1445 Traffic Generator with proper permissions and configuration

set -e

echo "=============================================="
echo "VEP1445 Traffic Generator - Installation"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

INSTALL_DIR="/opt/vep1445-traffic-gen"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"

echo "Installation directory: $INSTALL_DIR"
echo "Source directory: $CURRENT_DIR"
echo ""

# Backup existing installation
if [ -d "$INSTALL_DIR" ]; then
    BACKUP_DIR="${INSTALL_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
    echo "⚠️  Existing installation found"
    echo "📦 Backing up to: $BACKUP_DIR"
    mv "$INSTALL_DIR" "$BACKUP_DIR"
    echo "✅ Backup complete"
    echo ""
fi

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p "$INSTALL_DIR"/{web,protocols,monitoring,testing,config,docs,scripts,logs}

# Copy files
echo "📋 Copying files..."

# Main files
cp "$CURRENT_DIR/web_api.py" "$INSTALL_DIR/"
cp "$CURRENT_DIR/traffic_engine_unified.py" "$INSTALL_DIR/"
cp "$CURRENT_DIR/neighbor_discovery.py" "$INSTALL_DIR/"
cp "$CURRENT_DIR/README.md" "$INSTALL_DIR/"

# Web files
cp -r "$CURRENT_DIR/web/"* "$INSTALL_DIR/web/"

# Protocol files
cp -r "$CURRENT_DIR/protocols/"* "$INSTALL_DIR/protocols/"

# Monitoring files
cp -r "$CURRENT_DIR/monitoring/"* "$INSTALL_DIR/monitoring/"

# Testing files
cp -r "$CURRENT_DIR/testing/"* "$INSTALL_DIR/testing/"

# Config files
if [ -d "$CURRENT_DIR/config" ]; then
    cp -r "$CURRENT_DIR/config/"* "$INSTALL_DIR/config/" 2>/dev/null || true
fi

# Documentation
if [ -d "$CURRENT_DIR/docs" ]; then
    cp -r "$CURRENT_DIR/docs/"* "$INSTALL_DIR/docs/" 2>/dev/null || true
fi

# Scripts
if [ -d "$CURRENT_DIR/scripts" ]; then
    cp -r "$CURRENT_DIR/scripts/"* "$INSTALL_DIR/scripts/" 2>/dev/null || true
fi

echo "✅ Files copied"
echo ""

# Set permissions
echo "🔒 Setting permissions..."

# Ownership
chown -R root:root "$INSTALL_DIR"

# Directories
find "$INSTALL_DIR" -type d -exec chmod 755 {} \;

# Python files
find "$INSTALL_DIR" -type f -name "*.py" -exec chmod 644 {} \;

# Make main script executable
chmod 755 "$INSTALL_DIR/web_api.py"

# Scripts executable
find "$INSTALL_DIR/scripts" -type f -name "*.sh" -exec chmod 755 {} \; 2>/dev/null || true

# Web files readable
find "$INSTALL_DIR/web" -type f -exec chmod 644 {} \;

# Config files
find "$INSTALL_DIR/config" -type f -exec chmod 644 {} \; 2>/dev/null || true

# Logs directory writable
chmod 777 "$INSTALL_DIR/logs"

echo "✅ Permissions set"
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install flask flask-cors --break-system-packages 2>/dev/null || \
pip3 install flask flask-cors || \
echo "⚠️  Could not install dependencies automatically. Please run: pip3 install flask flask-cors"
echo ""

# Create systemd service (optional)
echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/vep1445.service << 'EOF'
[Unit]
Description=VEP1445 Traffic Generator & Network Impairment System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vep1445-traffic-gen
ExecStart=/usr/bin/python3 /opt/vep1445-traffic-gen/web_api.py
Restart=on-failure
RestartSec=5s
StandardOutput=append:/opt/vep1445-traffic-gen/logs/vep1445.log
StandardError=append:/opt/vep1445-traffic-gen/logs/vep1445-error.log

[Install]
WantedBy=multi-user.target
EOF

chmod 644 /etc/systemd/system/vep1445.service
systemctl daemon-reload
echo "✅ Systemd service created"
echo ""

# Create default runtime config if it doesn't exist
if [ ! -f /home/claude/vep1445_runtime_config.json ]; then
    echo "📝 Creating default runtime configuration..."
    cat > /home/claude/vep1445_runtime_config.json << 'EOF'
{
  "interfaces": {},
  "traffic_profiles": {}
}
EOF
    chmod 644 /home/claude/vep1445_runtime_config.json
    echo "✅ Default config created"
    echo ""
fi

# Installation complete
echo "=============================================="
echo "✅ Installation Complete!"
echo "=============================================="
echo ""
echo "Installation directory: $INSTALL_DIR"
echo ""
echo "Next steps:"
echo ""
echo "1. Test the web interface:"
echo "   cd $INSTALL_DIR"
echo "   sudo python3 web_api.py"
echo ""
echo "2. Open browser to:"
echo "   http://$(hostname -I | awk '{print $1}'):5000"
echo "   or"
echo "   http://localhost:5000"
echo ""
echo "3. (Optional) Enable service to start on boot:"
echo "   sudo systemctl enable vep1445"
echo "   sudo systemctl start vep1445"
echo ""
echo "4. View service logs:"
echo "   sudo journalctl -u vep1445 -f"
echo "   or"
echo "   tail -f $INSTALL_DIR/logs/vep1445.log"
echo ""
echo "Documentation: $INSTALL_DIR/README.md"
echo ""
echo "=============================================="
