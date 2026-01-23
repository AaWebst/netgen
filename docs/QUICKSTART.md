# VEP1445 Quick Start Guide

## Installation (One-Time Setup)

### Step 1: Copy Files to VEP1445

```bash
# Create directory and copy all files
sudo mkdir -p /opt/vep1445-traffic-gen
cd /opt/vep1445-traffic-gen

# Copy these files:
# - traffic_engine.py
# - web_api.py
# - requirements.txt
# - start_vep1445.sh
# - install.sh
# - vep1445-traffic-gen.service
# - web/ (directory)
```

### Step 2: Run Installation

```bash
sudo chmod +x install.sh
sudo ./install.sh
```

The installer will:
- Install Python dependencies
- Set up directories and permissions
- Configure systemd service
- Check network interfaces

## Running the System

### Option A: Using systemd (Recommended)

```bash
# Start service
sudo systemctl start vep1445-traffic-gen

# Check status
sudo systemctl status vep1445-traffic-gen

# View logs
sudo journalctl -u vep1445-traffic-gen -f

# Stop service
sudo systemctl stop vep1445-traffic-gen

# Enable auto-start on boot
sudo systemctl enable vep1445-traffic-gen
```

### Option B: Manual Start

```bash
cd /opt/vep1445-traffic-gen
sudo ./start_vep1445.sh
```

## Accessing the Web Interface

Open your browser:
```
http://<VEP1445-IP>:5000
```

If running locally:
```
http://localhost:5000
```

## First Time Usage

### 1. Check Interface Status

- Click "Network Interfaces" tab
- Verify all 5 interfaces (eth1-eth5) have IP addresses
- If not, wait a moment for DHCP/discovery to complete
- Or click "DISCOVER" to manually trigger discovery

### 2. Create Your First Traffic Profile

Click "Traffic Profiles" tab → "+ ADD TRAFFIC PROFILE"

**Example: VoIP Traffic from LAN1 to LAN2**
```
Profile Name: LAN1_to_LAN2_VoIP
Source Interface: eth1
Destination Interface: eth2
Destination IP: 192.168.2.100
Bandwidth: 10 Mbps
Packet Size: 160 bytes
Protocol: IPv4
DSCP/QoS: 46 (EF - Voice)
Latency: 20 ms
Jitter: 5 ms
Packet Loss: 0.1%
```

Click "CREATE PROFILE"

### 3. Start Traffic Generation

- Toggle the profile switch to ENABLED (it will turn green)
- Click "▶ START TRAFFIC" button at the top
- System status should change to "ONLINE"
- Watch statistics update in real-time

### 4. Monitor Statistics

- Click "Statistics" tab
- View TX/RX packets, bytes, and dropped packets
- Statistics update every 2 seconds

### 5. Adjust Impairments (Real-Time)

While traffic is running:
- Click "EDIT" on any profile
- Modify latency, jitter, or packet loss
- Changes apply immediately

### 6. Stop Traffic

Click "■ STOP TRAFFIC" button

## Common Traffic Scenarios

### Scenario 1: Voice Traffic (VoIP)
```
Bandwidth: 10 Mbps
Packet Size: 160 bytes
DSCP: 46 (EF)
Latency: 20ms
Jitter: 5ms
Loss: 0.1%
```

### Scenario 2: Video Streaming
```
Bandwidth: 50 Mbps
Packet Size: 1316 bytes
DSCP: 34 (AF41)
Latency: 30ms
Jitter: 10ms
Loss: 0.5%
```

### Scenario 3: Bulk Data Transfer
```
Bandwidth: 100 Mbps
Packet Size: 1500 bytes
DSCP: 0 (Best Effort)
Latency: 0ms
Jitter: 0ms
Loss: 0%
```

### Scenario 4: WAN Simulation
```
Bandwidth: 10 Mbps
Packet Size: 1024 bytes
DSCP: 0
Latency: 100ms
Jitter: 30ms
Loss: 2%
```

## Using Different Protocols

### MPLS Traffic
```
Protocol: MPLS
MPLS Label: 100 (or any value 16-1048575)
```

### VXLAN Overlay
```
Protocol: VXLAN
VNI: 5000 (or any value 1-16777215)
```

### Q-in-Q (Double VLAN)
```
Protocol: Q-in-Q
VLAN Outer: 100
VLAN Inner: 200
```

## RFC2544 Testing

### Running a Throughput Test

1. Create a traffic profile
2. Go to "RFC2544 Testing" tab
3. Select profile
4. Enable "Throughput Test"
5. Click "START RFC2544 TEST"
6. Wait for results (can take several minutes)

### Test Frame Sizes

Standard RFC2544 frame sizes are tested:
- 64, 128, 256, 512, 1024, 1280, 1518 bytes

## Troubleshooting

### Problem: No IP addresses on interfaces

**Solution:**
```bash
# Check if interfaces are up
ip link show

# Bring interfaces up manually
sudo ip link set eth1 up
sudo ip link set eth2 up
# ... etc

# Check DHCP is available on your LANs
# Or manually assign IPs via web interface
```

### Problem: "Permission denied" errors

**Solution:**
```bash
# Ensure running as root/sudo
sudo systemctl start vep1445-traffic-gen

# Or set capabilities
sudo setcap cap_net_raw,cap_net_admin=eip $(which python3)
```

### Problem: Traffic not generating

**Checklist:**
- [ ] Interfaces have IP addresses?
- [ ] Profile is ENABLED (green)?
- [ ] "START TRAFFIC" button clicked?
- [ ] Check system status shows "ONLINE"?
- [ ] Destination IP is reachable on target LAN?

**Debug:**
```bash
# Check logs
tail -f /var/log/vep1445/traffic-gen.log

# Verify process is running
ps aux | grep web_api.py

# Check interface status
ip addr show
```

### Problem: Web interface not loading

**Solution:**
```bash
# Check if service is running
sudo systemctl status vep1445-traffic-gen

# Check if port 5000 is listening
sudo netstat -tlnp | grep 5000

# Check firewall
sudo ufw status
sudo ufw allow 5000/tcp
```

## Saving and Loading Configurations

### Save Current Configuration
Click "💾 SAVE CONFIG" button
- Saves to: `/home/claude/vep1445_runtime_config.json`

### Load Sample Configuration
```bash
# Via API
curl -X POST http://localhost:5000/api/config/load \
  -H "Content-Type: application/json" \
  -d '{"filename": "/opt/vep1445-traffic-gen/sample_config.json"}'

# Or copy sample config
sudo cp sample_config.json /home/claude/vep1445_runtime_config.json
# Then restart service
sudo systemctl restart vep1445-traffic-gen
```

## API Usage (Advanced)

### Get System Status
```bash
curl http://localhost:5000/api/system/status
```

### Create Profile via API
```bash
curl -X POST http://localhost:5000/api/traffic-profiles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test_Profile",
    "src_interface": "eth1",
    "dst_interface": "eth2",
    "dst_ip": "192.168.2.100",
    "bandwidth_mbps": 10,
    "packet_size": 1024,
    "protocol": "ipv4"
  }'
```

### Start Traffic
```bash
curl -X POST http://localhost:5000/api/traffic/start
```

### Get Statistics
```bash
curl http://localhost:5000/api/traffic/stats
```

## Performance Tips

### Maximum Throughput
1. Use larger packet sizes (1500 bytes)
2. Disable impairments (0 latency/jitter/loss)
3. Reduce number of concurrent profiles
4. Use best-effort DSCP (0)

### Accurate Latency Testing
1. Disable other traffic profiles
2. Use moderate bandwidth (<100 Mbps)
3. Use consistent packet sizes
4. Monitor CPU usage

### Testing Multiple Scenarios
1. Create profiles with descriptive names
2. Use traffic profiles tab to organize
3. Enable/disable specific profiles as needed
4. Save configurations for later reuse

## File Locations

| Item | Location |
|------|----------|
| Application | `/opt/vep1445-traffic-gen/` |
| Logs | `/var/log/vep1445/` |
| Config | `/home/claude/vep1445_runtime_config.json` |
| Service | `/etc/systemd/system/vep1445-traffic-gen.service` |
| Web Interface | `/opt/vep1445-traffic-gen/web/` |

## Getting Help

1. **Check logs first:**
   ```bash
   tail -100 /var/log/vep1445/traffic-gen.log
   ```

2. **Verify system status:**
   ```bash
   sudo systemctl status vep1445-traffic-gen
   ```

3. **Test connectivity:**
   ```bash
   ping <destination-ip>
   ```

4. **Check documentation:**
   ```bash
   cat /opt/vep1445-traffic-gen/README.md
   ```

## Next Steps

- Experiment with different protocols (MPLS, VXLAN, Q-in-Q)
- Run RFC2544 benchmarks
- Create complex multi-LAN traffic scenarios
- Adjust impairments to simulate various network conditions
- Export configurations for different test scenarios

---

**Need more detailed information?** See the full README.md
