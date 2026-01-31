# VEP1445 Quick Start Guide

## Installation

### Method 1: Using Install Script (Recommended)
```bash
# Extract the package
cd /tmp
tar xzf vep1445-RESTORED-FIXED.tar.gz
cd vep1445-RESTORED-FIXED

# Run installer
sudo ./scripts/install.sh
```

The installer will:
- ✅ Install to `/opt/vep1445-traffic-gen`
- ✅ Set correct permissions
- ✅ Install Python dependencies
- ✅ Create systemd service
- ✅ Create default configuration

### Method 2: Manual Installation
```bash
# Extract
tar xzf vep1445-RESTORED-FIXED.tar.gz
cd vep1445-RESTORED-FIXED

# Install dependencies
sudo pip3 install flask flask-cors --break-system-packages

# Run directly
sudo python3 web_api.py
```

## First Run

### Option A: Run as Service
```bash
# Start service
sudo systemctl start vep1445

# Enable on boot
sudo systemctl enable vep1445

# Check status
sudo systemctl status vep1445

# View logs
sudo journalctl -u vep1445 -f
```

### Option B: Run Manually
```bash
cd /opt/vep1445-traffic-gen
sudo python3 web_api.py
```

## Access the Web Interface

Open your browser to:
```
http://YOUR_SERVER_IP:5000
```

Examples:
- Local: http://localhost:5000
- Remote: http://192.168.1.100:5000

## What You'll See

### Interface Cards
On the main page, you'll see interface cards showing:
- Interface name (eno2, eno3, etc.)
- Speed (1G/10G)
- MAC address
- **IP address** (from DHCP or static)
- Subnet mask
- Link status
- **Neighbor information** (from ARP/LLDP)

### Tabs
- **Network Interfaces** - View and manage interfaces
- **Traffic Profiles** - Create and manage traffic profiles
- **Statistics** - View real-time traffic statistics
- **RFC2544** - Run standardized benchmarking tests

## Creating Your First Traffic Profile

1. Click **"Network Interfaces"** tab
2. Note the interface names (eno2, eno3, etc.)
3. Click **"Traffic Profiles"** tab
4. Click **"+ ADD TRAFFIC PROFILE"**
5. Fill in:
   - Profile Name: "My_First_Test"
   - Source Interface: eno2
   - Destination Interface: eno3
   - Protocol: UDP
   - Bandwidth: 100 Mbps
6. Click **"CREATE PROFILE"**
7. Toggle the switch to **ENABLE** the profile
8. Traffic will start automatically!

## Using New Features (API)

### Check Available Features
```bash
curl http://localhost:5000/api/features/status
```

### SNMP Agent Farm
```bash
# Start 10 SNMP agents
curl -X POST http://localhost:5000/api/snmp/start \
  -H "Content-Type: application/json" \
  -d '{
    "base_ip": "192.168.100.1",
    "count": 10
  }'

# Stop SNMP agents
curl -X POST http://localhost:5000/api/snmp/stop
```

### NetFlow Generation
```bash
# Start NetFlow generation
curl -X POST http://localhost:5000/api/netflow/start \
  -H "Content-Type: application/json" \
  -d '{
    "collector_ip": "192.168.1.100",
    "collector_port": 2055,
    "flows_per_sec": 1000,
    "duration": 60
  }'
```

### BGP Route Injection
```bash
# Start BGP session
curl -X POST http://localhost:5000/api/bgp/start \
  -H "Content-Type: application/json" \
  -d '{
    "peer_ip": "192.168.1.1",
    "local_asn": 65000,
    "route_count": 1000
  }'

# Stop BGP session
curl -X POST http://localhost:5000/api/bgp/stop
```

### QoS Testing
```bash
# Run QoS validation test
curl -X POST http://localhost:5000/api/qos/test \
  -H "Content-Type: application/json" \
  -d '{
    "src_ip": "192.168.1.1",
    "dst_ip": "192.168.1.2",
    "duration": 60,
    "scenario": "voice_video_data"
  }'

# Get results
curl http://localhost:5000/api/qos/results
```

### Network Impairments
```bash
# Enable impairments
curl -X POST http://localhost:5000/api/impairments/enable \
  -H "Content-Type: application/json" \
  -d '{
    "latency_ms": 100,
    "jitter_ms": 20,
    "loss_percent": 2,
    "burst_loss_percent": 1
  }'

# Disable impairments
curl -X POST http://localhost:5000/api/impairments/disable
```

## Troubleshooting

### Interfaces Don't Show
```bash
# Check if service is running
sudo systemctl status vep1445

# Check logs
tail -f /opt/vep1445-traffic-gen/logs/vep1445.log

# Test manually
cd /opt/vep1445-traffic-gen
sudo python3 web_api.py
```

### Neighbor Discovery Not Working
```bash
# Check if neighbor_discovery.py exists
ls -la /opt/vep1445-traffic-gen/neighbor_discovery.py

# Check if neighbor-discovery.js exists
ls -la /opt/vep1445-traffic-gen/web/neighbor-discovery.js

# Test API endpoint
curl -X POST http://localhost:5000/api/neighbors/discover \
  -H "Content-Type: application/json" \
  -d '{"interfaces": ["eno2", "eno3"]}'
```

### Permission Errors
```bash
# Make sure running as root
sudo python3 web_api.py

# Or check service
sudo systemctl status vep1445
```

### Dependencies Missing
```bash
# Install Flask
sudo pip3 install flask flask-cors --break-system-packages

# Or without --break-system-packages
pip3 install flask flask-cors
```

## Stopping the System

### If Running as Service
```bash
sudo systemctl stop vep1445
```

### If Running Manually
Press `Ctrl+C` in the terminal

## Uninstallation

```bash
cd /opt/vep1445-traffic-gen
sudo ./scripts/uninstall.sh
```

## Configuration Files

### Runtime Config
```
/home/claude/vep1445_runtime_config.json
```
This file stores interfaces and profiles. Auto-created on first run.

### Example Config
```
/opt/vep1445-traffic-gen/config/example_config.json
```
Reference configuration showing all available options.

## Logs

### Service Logs
```bash
# View live logs
sudo journalctl -u vep1445 -f

# View recent logs
sudo journalctl -u vep1445 -n 100
```

### File Logs
```bash
# Application log
tail -f /opt/vep1445-traffic-gen/logs/vep1445.log

# Error log
tail -f /opt/vep1445-traffic-gen/logs/vep1445-error.log
```

## Getting Help

1. Check README.md in installation directory
2. Check logs for error messages
3. Verify all files are present
4. Ensure dependencies are installed
5. Run manually to see errors: `sudo python3 web_api.py`

## Next Steps

1. ✅ Configure your interfaces via the web GUI
2. ✅ Create traffic profiles
3. ✅ Enable neighbor discovery to see connected devices
4. ✅ Try the new features via API
5. ✅ Run RFC2544 tests
6. ✅ Monitor statistics

Enjoy your VEP1445 Traffic Generator!
