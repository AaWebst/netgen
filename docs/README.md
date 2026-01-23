# VEP1445 Multi-LAN Traffic Generator & Network Impairment System

A comprehensive network traffic generation and impairment tool designed for the VEP1445 hardware platform with 5 LAN ports. This system provides advanced capabilities for generating traffic across multiple networks with precise control over bandwidth, protocols, and network impairments.

## Features

### Core Capabilities
- **Multi-Interface Support**: Manages 5 network interfaces (LAN1-LAN5)
- **Auto-Configuration**: DHCP client and ARP-based network discovery
- **Self-Assigning IP Addresses**: Automatically assigns IPs based on discovered network topology

### Protocol Support
- **IPv4**: Full IPv4 packet generation with DSCP/QoS control
- **IPv6**: IPv6 packet generation with traffic class support
- **MPLS**: Multi-Protocol Label Switching with configurable labels
- **VXLAN**: Virtual Extensible LAN with VNI configuration
- **Q-in-Q (802.1ad)**: Double VLAN tagging support

### Traffic Control
- Configurable bandwidth (0.1 Mbps to 10 Gbps)
- Packet size control (64 to 9000 bytes)
- DSCP/QoS marking (0-63)
- Per-profile traffic generation

### Network Impairments
- **Latency**: Add delay to packets (0-10000 ms)
- **Jitter**: Introduce timing variance (0-1000 ms)
- **Packet Loss**: Simulate packet drops (0-100%)
- Real-time impairment adjustments

### RFC2544 Testing
- **Throughput Test**: Find maximum throughput with <0.001% loss
- **Latency Test**: Measure average, min, and max latency
- **Frame Loss Rate Test**: Test loss at various load percentages
- **Back-to-Back Test**: Measure burst capacity

### Web Interface
- Real-time monitoring dashboard
- Interactive configuration
- Live statistics
- Professional NOC-style UI

## System Requirements

### Hardware
- VEP1445 or compatible multi-port network device
- 5 network interfaces (eth1-eth5)
- Minimum 2GB RAM
- x86_64 or ARM64 processor

### Software
- Linux (Ubuntu 20.04+ recommended)
- Python 3.8+
- Root/sudo access (required for raw socket operations)

## Installation

### 1. Clone or Copy Files

Copy all files to your VEP1445 system:
```bash
# Create project directory
mkdir -p /opt/vep1445-traffic-gen
cd /opt/vep1445-traffic-gen

# Copy files (assuming they're in current directory)
cp traffic_engine.py .
cp web_api.py .
cp requirements.txt .
cp -r web/ .
```

### 2. Install Python Dependencies

```bash
# Install system packages
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev build-essential

# Install Python dependencies
sudo pip3 install -r requirements.txt
```

### 3. Configure Network Interfaces

Ensure your network interfaces are up:
```bash
# Bring up all interfaces
sudo ip link set eth1 up
sudo ip link set eth2 up
sudo ip link set eth3 up
sudo ip link set eth4 up
sudo ip link set eth5 up
```

### 4. Grant Network Capabilities (Alternative to running as root)

```bash
# Allow the Python interpreter to create raw sockets
sudo setcap cap_net_raw,cap_net_admin=eip $(readlink -f $(which python3))
```

## Running the System

### Start the Application

```bash
# Run with sudo (required for raw socket access)
sudo python3 web_api.py
```

The system will:
1. Initialize 5 network interfaces (eth1-eth5)
2. Attempt DHCP on each interface
3. Fall back to ARP-based auto-IP assignment if DHCP fails
4. Start the web server on port 5000

### Access the Web Interface

Open your browser and navigate to:
```
http://<VEP1445-IP-ADDRESS>:5000
```

Or if running locally:
```
http://localhost:5000
```

## Usage Guide

### 1. Network Discovery

The system automatically discovers your network topology when started:
- Listens for ARP packets on each interface
- Attempts DHCP to obtain IP addresses
- Auto-assigns IPs based on discovered networks
- Displays discovered hosts in the web interface

### 2. Creating Traffic Profiles

1. Click the "Traffic Profiles" tab
2. Click "+ ADD TRAFFIC PROFILE"
3. Configure your profile:
   - **Profile Name**: Descriptive name (e.g., "LAN1_to_LAN2_Voice")
   - **Source/Destination**: Select interfaces
   - **Destination IP**: Target IP address
   - **Bandwidth**: Traffic rate in Mbps
   - **Packet Size**: Packet size in bytes
   - **Protocol**: IPv4, IPv6, MPLS, VXLAN, or Q-in-Q
   - **QoS**: DSCP value (0-63)
   - **Impairments**: Latency, jitter, packet loss

4. Click "CREATE PROFILE"

### 3. Starting Traffic Generation

1. Enable desired traffic profiles using the toggle switches
2. Click "▶ START TRAFFIC" in the main controls
3. Monitor real-time statistics in the dashboard

### 4. Network Impairments

Adjust impairments in real-time:
- **Latency**: Fixed delay added to packets
- **Jitter**: Random variation in latency (±jitter value)
- **Packet Loss**: Percentage of packets randomly dropped

Example use cases:
- Simulate WAN conditions: 50ms latency, 10ms jitter, 0.1% loss
- Test VoIP quality: 20ms latency, 5ms jitter, 0% loss
- Simulate congested network: 100ms latency, 30ms jitter, 2% loss

### 5. RFC2544 Testing

1. Go to "RFC2544 Testing" tab
2. Select a traffic profile to test
3. Choose test types:
   - Throughput
   - Latency
   - Frame Loss Rate
   - Back-to-Back
4. Click "START RFC2544 TEST"
5. Results will appear when complete

## API Reference

### REST API Endpoints

All endpoints are available at `http://<host>:5000/api/`

#### Interfaces

**GET /api/interfaces**
- Get all network interfaces and their status

**POST /api/interfaces**
- Add a new network interface
- Body: `{name, mac_address, ip_address?, subnet_mask?, ...}`

**GET /api/interfaces/<name>**
- Get specific interface details

**POST /api/interfaces/<name>/discover**
- Re-run network discovery on interface

#### Traffic Profiles

**GET /api/traffic-profiles**
- Get all traffic profiles

**POST /api/traffic-profiles**
- Create new traffic profile
- Body: Profile configuration object

**PUT /api/traffic-profiles/<name>**
- Update existing profile
- Body: Fields to update

**DELETE /api/traffic-profiles/<name>**
- Delete traffic profile

#### Traffic Control

**POST /api/traffic/start**
- Start traffic generation

**POST /api/traffic/stop**
- Stop traffic generation

**GET /api/traffic/stats**
- Get real-time traffic statistics

#### Configuration

**GET /api/config**
- Get complete system configuration

**POST /api/config**
- Save configuration to file

**POST /api/config/load**
- Load configuration from file

#### System

**GET /api/system/status**
- Get overall system status

## Configuration Examples

### Example 1: Inter-LAN Traffic with QoS

```json
{
  "name": "LAN1_to_LAN2_VoIP",
  "src_interface": "eth1",
  "dst_interface": "eth2",
  "dst_ip": "192.168.2.100",
  "bandwidth_mbps": 10,
  "packet_size": 160,
  "protocol": "ipv4",
  "dscp": 46,
  "latency_ms": 20,
  "jitter_ms": 5,
  "packet_loss_percent": 0.1
}
```

### Example 2: VXLAN Overlay Traffic

```json
{
  "name": "VXLAN_Overlay",
  "src_interface": "eth3",
  "dst_interface": "eth4",
  "dst_ip": "10.0.0.100",
  "bandwidth_mbps": 100,
  "packet_size": 1400,
  "protocol": "vxlan",
  "vni": 5000,
  "dscp": 0,
  "latency_ms": 0,
  "jitter_ms": 0,
  "packet_loss_percent": 0
}
```

### Example 3: Q-in-Q Service Provider Traffic

```json
{
  "name": "QinQ_Provider",
  "src_interface": "eth1",
  "dst_interface": "eth5",
  "dst_ip": "172.16.0.50",
  "bandwidth_mbps": 1000,
  "packet_size": 1518,
  "protocol": "qinq",
  "vlan_outer": 100,
  "vlan_inner": 200,
  "dscp": 32
}
```

### Example 4: MPLS Traffic

```json
{
  "name": "MPLS_LSP",
  "src_interface": "eth2",
  "dst_interface": "eth3",
  "dst_ip": "10.255.0.1",
  "bandwidth_mbps": 500,
  "packet_size": 1024,
  "protocol": "mpls",
  "mpls_label": 100,
  "dscp": 40
}
```

## Troubleshooting

### No IP Addresses Assigned

**Problem**: Interfaces show "Not assigned" for IP addresses

**Solutions**:
1. Ensure network cables are connected
2. Check if DHCP server is available on each LAN
3. Verify interfaces are up: `ip link show`
4. Manually trigger discovery: Use web interface "DISCOVER" button
5. Check system logs: `journalctl -u vep1445-traffic-gen`

### Permission Denied Errors

**Problem**: "Operation not permitted" when creating raw sockets

**Solutions**:
1. Run with sudo: `sudo python3 web_api.py`
2. Or grant capabilities: `sudo setcap cap_net_raw,cap_net_admin=eip $(which python3)`

### Traffic Not Generating

**Problem**: Traffic profiles enabled but no packets sent

**Solutions**:
1. Verify both source and destination interfaces have IP addresses
2. Check that "START TRAFFIC" button has been clicked
3. Review system status in dashboard
4. Check firewall rules: `sudo iptables -L`

### High Packet Loss

**Problem**: Unexpected packet drops

**Possible Causes**:
1. Hardware/driver limitations
2. Bandwidth exceeds interface capacity
3. Intentional impairment settings
4. System resource constraints

**Solutions**:
1. Reduce total bandwidth across all profiles
2. Check CPU/memory usage
3. Review packet_loss_percent settings
4. Ensure packet size matches MTU

### Web Interface Not Loading

**Problem**: Cannot access web interface

**Solutions**:
1. Verify Flask is running: `ps aux | grep web_api.py`
2. Check port 5000 is not in use: `sudo netstat -tlnp | grep 5000`
3. Try different port: Edit `web_api.py` and change `app.run(port=5000)` to different port
4. Check firewall: `sudo ufw status`

## Advanced Configuration

### Custom Interface Names

If your system uses different interface names:

Edit `web_api.py`:
```python
def initialize_default_config():
    # Change interface names here
    for i in range(1, 6):
        config = InterfaceConfig(
            name=f"enp0s{i}",  # Change from eth{i} to your naming scheme
            mac_address=f"00:11:22:33:44:{i:02x}"
        )
        engine.add_interface(config)
```

### Changing Web Server Port

Edit `web_api.py`, last line:
```python
app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)
```

### Persistent Configuration

The system saves configuration to:
```
/home/claude/vep1445_runtime_config.json
```

To backup configuration:
```bash
sudo cp /home/claude/vep1445_runtime_config.json /backup/location/
```

To restore:
```bash
sudo cp /backup/location/vep1445_runtime_config.json /home/claude/
# Then use "LOAD CONFIG" in web interface
```

## Performance Tuning

### Maximum Throughput

For line-rate traffic generation:

1. **Increase packet size**: Larger packets = fewer PPS required
2. **Reduce impairments**: Latency/jitter processing adds overhead
3. **Use kernel bypass** (advanced): Consider DPDK integration
4. **CPU affinity**: Pin traffic threads to specific cores

### Minimizing Latency

For precise latency measurements:

1. Disable power management:
```bash
sudo cpupower frequency-set -g performance
```

2. Use real-time kernel (optional):
```bash
sudo apt-get install linux-lowlatency
```

3. Increase process priority:
```bash
sudo nice -n -20 python3 web_api.py
```

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Web Interface                         │
│              (React-like UI, Port 5000)                  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/REST API
┌──────────────────────▼──────────────────────────────────┐
│                   Flask Web API                          │
│                  (web_api.py)                            │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              Traffic Engine Core                         │
│              (traffic_engine.py)                         │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │   Network   │  │   Traffic    │  │  Impairment    │ │
│  │  Discovery  │  │  Generator   │  │    Engine      │ │
│  └─────────────┘  └──────────────┘  └────────────────┘ │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ARP Listener │  │DHCP Client   │  │RFC2544 Tester  │ │
│  └─────────────┘  └──────────────┘  └────────────────┘ │
└────────┬────────┬────────┬────────┬────────┬───────────┘
         │        │        │        │        │
      ┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐
      │eth1 │ │eth2 │ │eth3 │ │eth4 │ │eth5 │
      │LAN1 │ │LAN2 │ │LAN3 │ │LAN4 │ │LAN5 │
      └─────┘ └─────┘ └─────┘ └─────┘ └─────┘
```

## Protocol Details

### IPv4 Packet Structure
```
[IPv4 Header (20 bytes)] + [Payload]
- Version: 4
- DSCP: Configurable
- TTL: 64
- Protocol: UDP (17)
```

### MPLS Packet Structure
```
[MPLS Header (4 bytes)] + [IPv4 Header] + [Payload]
- Label: Configurable (20 bits)
- EXP: 0 (3 bits)
- Bottom of Stack: 1
- TTL: 64
```

### VXLAN Packet Structure
```
[VXLAN Header (8 bytes)] + [Inner Ethernet] + [Inner IP] + [Payload]
- Flags: 0x08 (Valid VNI)
- VNI: Configurable (24 bits)
```

### Q-in-Q Packet Structure
```
[Outer 802.1ad Tag] + [Inner 802.1Q Tag] + [IP Header] + [Payload]
- Outer EtherType: 0x88a8
- Inner EtherType: 0x8100
- Configurable VLANs
```

## Security Considerations

⚠️ **Important Security Notes**:

1. **Raw Socket Access**: Requires root/elevated privileges
2. **Network Security**: Can generate significant traffic
3. **Production Use**: Isolate on management network
4. **Access Control**: No built-in authentication (use firewall rules)
5. **Rate Limiting**: No built-in limits (configure wisely)

### Recommended Security Practices

```bash
# Limit web interface to localhost only
# Edit web_api.py: app.run(host='127.0.0.1', ...)

# Use firewall to restrict access
sudo ufw allow from 192.168.1.0/24 to any port 5000

# Run in isolated network segment
# Connect VEP1445 only to test LANs, not production
```

## License

This software is provided as-is for network testing and development purposes.

## Support

For issues, questions, or contributions:
1. Check this README thoroughly
2. Review logs: `/var/log/syslog` or `journalctl`
3. Verify system requirements
4. Test with simple configuration first

## Version History

- **v1.0.0** (2025-01-21): Initial release
  - Multi-LAN traffic generation
  - Protocol support (IPv4/6, MPLS, VXLAN, Q-in-Q)
  - Network impairments
  - RFC2544 testing
  - Web-based GUI

## Known Limitations

1. **Raw Socket Performance**: Python raw sockets may not achieve line rate on 10GbE
   - Consider DPDK for higher performance
2. **RFC2544 Implementation**: Simplified version, not fully compliant
3. **IPv6**: Basic support, may need enhancements for production
4. **Statistics**: Receive counters require additional implementation
5. **Multicast**: Not currently supported

## Future Enhancements

- [ ] DPDK integration for hardware acceleration
- [ ] SNMP support for remote monitoring
- [ ] syslog integration
- [ ] Configuration templates library
- [ ] Scheduled traffic profiles
- [ ] Bandwidth graphing
- [ ] Packet capture integration
- [ ] CLI interface
- [ ] API authentication
- [ ] Multi-user support

---

**Built for VEP1445 Multi-LAN Testing Platform**
