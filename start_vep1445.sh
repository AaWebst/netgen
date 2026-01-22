#!/bin/bash

# VEP1445 Traffic Generator Startup Script
# This script initializes the system and starts the web interface

set -e

# Configuration
PROJECT_DIR="/opt/vep1445-traffic-gen"
LOG_DIR="/var/log/vep1445"
LOG_FILE="${LOG_DIR}/traffic-gen.log"
PID_FILE="/var/run/vep1445-traffic-gen.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${CYAN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    echo "[ERROR] $1" >> "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "[SUCCESS] $1" >> "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "[WARNING] $1" >> "$LOG_FILE"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    error "This script must be run as root (sudo)"
    exit 1
fi

# Create log directory
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"

log "VEP1445 Traffic Generator Starting..."
log "=================================================="

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    error "Project directory not found: $PROJECT_DIR"
    error "Please install the application first"
    exit 1
fi

cd "$PROJECT_DIR"

# Check for required files
log "Checking required files..."
REQUIRED_FILES=("traffic_engine.py" "web_api.py" "requirements.txt" "web/index.html")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        error "Required file missing: $file"
        exit 1
    fi
done
success "All required files present"

# Check Python version
log "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    error "Python 3.8 or higher required. Found: $PYTHON_VERSION"
    exit 1
fi
success "Python version: $PYTHON_VERSION"

# Install/check dependencies
log "Checking Python dependencies..."
if ! python3 -c "import flask" 2>/dev/null; then
    log "Installing dependencies..."
    pip3 install -r requirements.txt || {
        error "Failed to install dependencies"
        exit 1
    }
    success "Dependencies installed"
else
    success "Dependencies already installed"
fi

# Check network interfaces
log "Checking network interfaces..."
INTERFACES=("eth1" "eth2" "eth3" "eth4" "eth5")
FOUND_INTERFACES=0

for iface in "${INTERFACES[@]}"; do
    if ip link show "$iface" &> /dev/null; then
        log "  ✓ $iface found"
        # Bring interface up if it's down
        if ! ip link show "$iface" | grep -q "state UP"; then
            log "    Bringing $iface up..."
            ip link set "$iface" up || warning "Could not bring $iface up"
        fi
        ((FOUND_INTERFACES++))
    else
        warning "  ✗ $iface not found (this may be normal if using different naming)"
    fi
done

if [ $FOUND_INTERFACES -eq 0 ]; then
    warning "No expected interfaces found. You may need to adjust interface names in web_api.py"
else
    success "Found $FOUND_INTERFACES network interfaces"
fi

# Grant network capabilities to Python (if not running as root)
log "Setting network capabilities..."
PYTHON_PATH=$(readlink -f $(which python3))
setcap cap_net_raw,cap_net_admin=eip "$PYTHON_PATH" 2>/dev/null || {
    warning "Could not set capabilities (running as root, so not needed)"
}

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        error "VEP1445 Traffic Generator already running (PID: $OLD_PID)"
        error "Stop it first with: kill $OLD_PID"
        exit 1
    else
        log "Removing stale PID file"
        rm -f "$PID_FILE"
    fi
fi

# Display startup information
log "=================================================="
log "Starting VEP1445 Traffic Generator"
log "Project Directory: $PROJECT_DIR"
log "Log File: $LOG_FILE"
log "Web Interface: http://0.0.0.0:5000"
log "API Endpoint: http://0.0.0.0:5000/api/"
log "=================================================="

# Start the application
log "Launching web API server..."

# Start in background and capture PID
nohup python3 web_api.py >> "$LOG_FILE" 2>&1 &
APP_PID=$!

# Save PID
echo $APP_PID > "$PID_FILE"

# Wait a moment and check if it's still running
sleep 2
if ps -p $APP_PID > /dev/null 2>&1; then
    success "VEP1445 Traffic Generator started successfully (PID: $APP_PID)"
    success "Web interface available at: http://localhost:5000"
    log "View logs: tail -f $LOG_FILE"
    log "Stop service: kill $APP_PID  or  systemctl stop vep1445-traffic-gen"
else
    error "Failed to start VEP1445 Traffic Generator"
    error "Check logs: $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi

exit 0
