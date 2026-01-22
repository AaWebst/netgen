# VEP1445 Unified Deployment Guide
## Copper LAN Ports (1G) + SFP 10G Ports - Single GUI Control

This guide covers deploying the VEP1445 with **mixed interface types**: 5 copper LAN ports (1Gbps) and 2 SFP 10G ports, controlled from a single web interface.

---

## System Architecture

```
VEP1445 Unified Traffic Generator
│
├── Copper Ports (Optimized Mode)
│   ├── eth1 (LAN1) ─── 1 Gbps ─── Optimized raw sockets
│   ├── eth2 (LAN2) ─── 1 Gbps ─── Hardware timestamps
│   ├── eth3 (LAN3) ─── 1 Gbps ─── Zero-copy TX/RX
│   ├── eth4 (LAN4) ─── 1 Gbps ─── Batch processing
│   └── eth5 (LAN5) ─── 1 Gbps ─── Low latency
│
└── SFP Ports (DPDK Mode)
    ├── sfp1 ────────── 10 Gbps ─── DPDK kernel bypass
    └── sfp2 ────────── 10 Gbps ─── Ultra-low latency
    
    Single Web GUI: http://<vep1445-ip>:5000
```

---

## Interface Capabilities

| Port | Type | Speed | Mode | Max Bandwidth | Hardware Timestamps | Use Case |
|------|------|-------|------|---------------|-------------------|----------|
| eth1-5 | Copper | 1G | Optimized | 1 Gbps | ✓ | LAN testing, standard traffic |
| sfp1-2 | SFP+ | 10G | DPDK | 10 Gbps | ✓ | High-speed, line-rate testing |

---

## Quick Start (All-in-One Deployment)

### Step 1: Installation

```bash
# Copy all files to VEP1445
cd /opt
sudo mkdir vep1445-traffic-gen
cd vep1445-traffic-gen

# Copy these key files:
# - traffic_engine_unified.py  (unified engine)
# - web_api.py                 (updated API)
# - web/index.html             (updated GUI)
# - requirements_highperf.txt
# - setup_performance.sh
# - All other support files

# Install dependencies
sudo pip3 install -r requirements_highperf.txt
```

### Step 2: Configure Performance

**For Copper Ports Only (No DPDK):**
```bash
sudo ./setup_performance.sh --mode high
```

**For Copper + SFP with DPDK (Recommended):**
```bash
# This configures copper ports AND sets up DPDK for SFP ports
sudo ./setup_performance.sh --mode dpdk

# Reboot for CPU isolation
sudo reboot

# After reboot, bind SFP ports to DPDK
sudo /opt/dpdk-23.11/usertools/dpdk-devbind.py --status

# Bind sfp1 and sfp2 (replace PCI addresses with your actual addresses)
sudo /opt/dpdk-23.11/usertools/dpdk-devbind.py --bind=vfio-pci 0000:03:00.0  # sfp1
sudo /opt/dpdk-23.11/usertools/dpdk-devbind.py --bind=vfio-pci 0000:03:00.1  # sfp2
```

### Step 3: Start System

```bash
# Start the unified system
sudo python3 web_api.py

# Or with systemd
sudo systemctl start vep1445-traffic-gen
```

### Step 4: Access Web Interface

```
http://<vep1445-ip>:5000
```

You'll see:
- **5 copper interfaces** (eth1-eth5) marked as "1G"
- **2 SFP interfaces** (sfp1-sfp2) marked as "10G" with "⚡ DPDK" indicator

---

## Usage Examples

### Example 1: LAN-to-LAN Traffic (Copper)

**Scenario**: Test traffic between two LANs at 500 Mbps

```json
{
  "name": "LAN1_to_LAN2",
  "src_interface": "eth1",
  "dst_interface": "eth2",
  "dst_ip": "192.168.2.100",
  "bandwidth_mbps": 500,
  "packet_size": 1500,
  "protocol": "ipv4",
  "dscp": 0
}
```

### Example 2: High-Speed Backbone (SFP)

**Scenario**: 10Gbps line-rate test between SFP ports

```json
{
  "name": "SFP_LineRate",
  "src_interface": "sfp1",
  "dst_interface": "sfp2",
  "dst_ip": "10.0.0.2",
  "bandwidth_mbps": 10000,
  "packet_size": 1500,
  "protocol": "ipv4",
  "dscp": 0
}
```

### Example 3: Mixed Copper-to-SFP

**Scenario**: Aggregate LAN traffic to high-speed uplink

```json
{
  "name": "LAN_to_Uplink",
  "src_interface": "eth1",
  "dst_interface": "sfp1",
  "dst_ip": "10.0.1.100",
  "bandwidth_mbps": 900,
  "packet_size": 1500,
  "protocol": "ipv4",
  "dscp": 46
}
```

### Example 4: Multi-Stream Test

Create **7 concurrent traffic profiles**:

1. **eth1 → eth2**: 400 Mbps (VoIP traffic)
2. **eth2 → eth3**: 600 Mbps (Video streaming)
3. **eth3 → eth4**: 800 Mbps (Data transfer)
4. **eth4 → eth5**: 500 Mbps (Bulk data)
5. **eth5 → sfp1**: 900 Mbps (Uplink aggregation)
6. **sfp1 → sfp2**: 10000 Mbps (Backbone test)
7. **sfp2 → eth1**: 800 Mbps (Downlink)

All managed from **single web interface**!

---

## Interface Management in Web GUI

### Visual Indicators

**Copper Ports (eth1-eth5)**:
- Badge: `1G` in cyan
- Border: Standard cyan glow on hover
- No DPDK indicator

**SFP Ports (sfp1-sfp2)**:
- Badge: `10G` in purple (animated pulse)
- Border: Purple left border, purple glow on hover
- DPDK indicator: `⚡ DPDK` in orange (animated glow)

### Interface Information Displayed

For each interface:
- Name (eth1, sfp1, etc.)
- Speed badge (1G or 10G)
- Interface type (copper_optimized, sfp_10g_dpdk)
- MAC address
- IP address (if assigned)
- Max bandwidth capability
- Hardware timestamp status

---

## Traffic Profile Creation

### Creating Profiles in Web GUI

1. Go to "Traffic Profiles" tab
2. Click "+ ADD TRAFFIC PROFILE"
3. Select interfaces from dropdowns (shows speed and DPDK status):
   - `eth1 (1G)` for copper
   - `sfp1 (10G) [DPDK]` for SFP
4. Configure traffic parameters
5. **Important**: Bandwidth is validated against interface max
   - Copper: Max 1000 Mbps
   - SFP: Max 10000 Mbps

### Bandwidth Validation

The system automatically validates:
- ✓ eth1 → eth2 at 500 Mbps: **Valid**
- ✓ sfp1 → sfp2 at 8000 Mbps: **Valid**
- ✗ eth1 → eth2 at 2000 Mbps: **Warning** (exceeds 1G limit)
- ✓ eth1 → sfp1 at 950 Mbps: **Valid** (limited by source)

---

## Performance Characteristics

### Copper Ports (Optimized Mode)

**Capabilities**:
- Throughput: Up to 1 Gbps per port
- Latency: ~10-50 μs
- Timestamp precision: ~100 ns (hardware)
- Concurrent streams: 5+ per port
- Impairments: Full support (latency, jitter, loss)

**Best for**:
- LAN testing
- Standard network protocols
- Moderate throughput requirements
- Network impairment simulation

### SFP Ports (DPDK Mode)

**Capabilities**:
- Throughput: Up to 10 Gbps per port (line rate)
- Latency: <1 μs
- Timestamp precision: ~20 ns (hardware)
- Packet rate: 14.8 Mpps (64-byte frames)
- Concurrent streams: 10+ per port
- Impairments: Full support

**Best for**:
- High-speed backbone testing
- Line-rate 10G testing
- Ultra-low latency applications
- RFC2544 benchmarking at 10G

---

## Configuration Files

### Default Interface Configuration

The system auto-detects and configures:

```python
# Copper ports (eth1-eth5)
InterfaceType.COPPER_OPTIMIZED
- Speed: 1000 Mbps
- Mode: Optimized raw sockets
- HW Timestamps: Enabled (if supported)

# SFP ports (sfp1-sfp2)  
InterfaceType.SFP_10G_DPDK
- Speed: 10000 Mbps
- Mode: DPDK kernel bypass
- HW Timestamps: Enabled
```

### Modifying Interface Assignments

Edit `web_api.py` in the `initialize_default_config()` function:

```python
# Change number of copper ports
for i in range(1, 8):  # Now eth1-eth7
    config = InterfaceConfig(
        name=f"eth{i}",
        interface_type=InterfaceType.COPPER_OPTIMIZED,
        speed_mbps=1000
    )
    engine.add_interface(config)

# Change number of SFP ports
for i in range(1, 5):  # Now sfp1-sfp4
    config = InterfaceConfig(
        name=f"sfp{i}",
        interface_type=InterfaceType.SFP_10G_DPDK,
        speed_mbps=10000
    )
    engine.add_interface(config)
```

---

## Monitoring and Statistics

### Per-Interface Statistics

Each interface shows:
- TX/RX packets
- TX/RX bytes
- Dropped packets
- Interface type
- Speed
- Hardware timestamp status

### Accessing Statistics

**Web GUI**:
- "Statistics" tab shows per-profile stats
- Real-time updates every 2 seconds
- Aggregated view of all interfaces

**API**:
```bash
# Get all interface stats
curl http://localhost:5000/api/traffic/stats

# Get interface capabilities
curl http://localhost:5000/api/capabilities
```

---

## Troubleshooting

### Copper Ports Not Working

**Check**:
```bash
# Verify interfaces are up
ip link show eth1

# Check if optimized
ethtool -k eth1 | grep -E "offload|scatter-gather"

# Test basic connectivity
ping -I eth1 192.168.1.1
```

**Fix**:
```bash
# Bring up interface
sudo ip link set eth1 up

# Enable offloads
sudo ethtool -K eth1 gso on tso on gro on

# Optimize ring buffers
sudo ethtool -G eth1 rx 4096 tx 4096
```

### SFP Ports Not in DPDK Mode

**Check**:
```bash
# Check DPDK binding status
sudo /opt/dpdk-23.11/usertools/dpdk-devbind.py --status

# Look for your SFP ports
```

**Fix**:
```bash
# Find PCI address
lspci | grep Ethernet

# Bind to DPDK
sudo /opt/dpdk-23.11/usertools/dpdk-devbind.py --bind=vfio-pci <PCI_ADDR>

# Verify
sudo /opt/dpdk-23.11/usertools/dpdk-devbind.py --status
```

### DPDK Initialization Failed

**Symptoms**: SFP ports show as "sfp_10g_optimized" instead of "sfp_10g_dpdk"

**This means**: DPDK failed to initialize, system fell back to optimized mode

**Check**:
```bash
# Hugepages allocated?
cat /proc/meminfo | grep Huge

# DPDK modules loaded?
lsmod | grep -E "vfio|uio"

# Check DPDK logs
dmesg | grep -i dpdk
```

**Fix**:
```bash
# Allocate hugepages
echo 1024 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# Load modules
sudo modprobe vfio-pci

# Restart system
sudo systemctl restart vep1445-traffic-gen
```

### Mixed Traffic Not Working

**Issue**: Traffic from copper to SFP (or vice versa) not flowing

**Check**:
- Routing/switching between networks
- IP addressing compatibility
- Firewall rules

**Note**: The VEP1445 generates packets but doesn't route - ensure your network infrastructure can handle cross-subnet traffic

---

## Advanced: Custom Interface Mappings

### Non-Standard Interface Names

If your system uses different names (e.g., `enp2s0` instead of `eth1`):

```python
# Edit web_api.py
def initialize_default_config():
    # Custom copper ports
    copper_ports = ['enp2s0', 'enp3s0', 'enp4s0', 'enp5s0', 'enp6s0']
    for i, port_name in enumerate(copper_ports, 1):
        config = InterfaceConfig(
            name=port_name,
            mac_address=f"00:11:22:33:44:{i:02x}",
            interface_type=InterfaceType.COPPER_OPTIMIZED,
            speed_mbps=1000
        )
        engine.add_interface(config)
    
    # Custom SFP ports
    sfp_ports = ['ens1f0', 'ens1f1']
    for i, port_name in enumerate(sfp_ports, 1):
        config = InterfaceConfig(
            name=port_name,
            mac_address=f"00:11:22:33:55:{i:02x}",
            interface_type=InterfaceType.SFP_10G_DPDK,
            speed_mbps=10000
        )
        engine.add_interface(config)
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All copper ports connected to LANs
- [ ] SFP modules installed in sfp1, sfp2
- [ ] SFP fiber/DAC cables connected
- [ ] System has internet access for installation
- [ ] Root/sudo access available

### Installation

- [ ] All files copied to `/opt/vep1445-traffic-gen`
- [ ] Dependencies installed (`requirements_highperf.txt`)
- [ ] Performance configured (`setup_performance.sh`)
- [ ] DPDK installed and configured (for SFP)
- [ ] Hugepages allocated (1024 pages minimum)
- [ ] SFP ports bound to DPDK driver

### Verification

- [ ] Web interface accessible at port 5000
- [ ] All 7 interfaces visible in GUI
- [ ] Copper ports show "1G" badge
- [ ] SFP ports show "10G" badge with "⚡ DPDK"
- [ ] Hardware timestamps enabled on all interfaces
- [ ] Test traffic profile created successfully
- [ ] Traffic generation starts/stops correctly

### Performance Testing

- [ ] Copper port: Achieve 500+ Mbps
- [ ] SFP port: Achieve 5+ Gbps
- [ ] Latency <50μs (copper), <1μs (SFP)
- [ ] No dropped packets at rated speed
- [ ] All impairments working (latency, jitter, loss)

---

## Summary

**Unified System Benefits**:
✅ **Single GUI** controls all 7 interfaces (5 copper + 2 SFP)  
✅ **Mixed modes** - Optimized copper + DPDK SFP simultaneously  
✅ **Automatic fallback** - If DPDK fails, SFP uses optimized mode  
✅ **Visual indicators** - Clear badges showing speed and mode  
✅ **Bandwidth validation** - Prevents exceeding interface limits  
✅ **Hardware timestamps** - On all interfaces where supported  
✅ **Flexible routing** - Any interface to any interface  

**Typical Performance**:
- **Copper aggregate**: 5 Gbps (5 × 1G ports)
- **SFP aggregate**: 20 Gbps (2 × 10G ports)
- **Total system**: 25 Gbps total capacity
- **Concurrent profiles**: 20+ traffic streams

---

**Start testing with a unified, powerful traffic generation platform!**

Access: `http://<your-vep1445-ip>:5000`
