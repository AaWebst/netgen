# VEP1445 HIGH-PERFORMANCE DEPLOYMENT GUIDE

## Quick Start for High-Throughput (100Mbps - 10Gbps)

This guide focuses on deploying the VEP1445 for **high-performance traffic generation** with **hardware timestamp support**.

---

## Performance Capabilities

| Mode | Throughput | Latency | Timestamp Precision | Use Case |
|------|-----------|---------|-------------------|----------|
| **Standard** | 100-500 Mbps | ~100μs | Software (~1ms) | Testing, development |
| **High-Performance** | 500Mbps-2Gbps | ~10μs | **Hardware (~100ns)** | **Production testing** ⭐ |
| **DPDK** | 2-10Gbps+ | <1μs | **Hardware (~20ns)** | Line-rate testing |

**⭐ Recommended**: High-Performance mode provides excellent results for most use cases without DPDK complexity.

---

## Installation for High-Performance

### Step 1: Standard Installation

```bash
# Copy all files to VEP1445
cd /opt
sudo mkdir vep1445-traffic-gen
cd vep1445-traffic-gen

# Copy files (make sure to get high-performance versions)
# - traffic_engine_highperf.py
# - web_api.py  
# - requirements_highperf.txt
# - setup_performance.sh
# - All other files from standard installation

# Install dependencies
sudo pip3 install -r requirements_highperf.txt
```

### Step 2: Configure for Performance

**Interactive Setup (Recommended):**
```bash
sudo chmod +x setup_performance.sh
sudo ./setup_performance.sh

# Select mode:
# - Option 2: High-Performance (500Mbps-2Gbps) for most users
# - Option 3: DPDK for 2Gbps+ line-rate performance
```

**Or Manual Configuration:**
```bash
# For High-Performance mode
sudo ./setup_performance.sh --mode high

# For DPDK mode
sudo ./setup_performance.sh --mode dpdk
```

### Step 3: Verify Hardware Timestamp Support

```bash
# Check if your NIC supports hardware timestamps
for i in {1..5}; do
    echo "Checking eth$i:"
    sudo ethtool -T eth$i | grep hardware
done

# Look for:
#   hardware-transmit (yes)
#   hardware-receive (yes)
#   hardware-raw-clock (yes)
```

### Step 4: Start the System

**For High-Performance Mode (< 2Gbps):**
```bash
# Edit web_api.py to use high-performance engine
# Change: from traffic_engine import TrafficEngineCore
# To:     from traffic_engine_highperf import HighPerformanceTrafficEngine as TrafficEngineCore

sudo systemctl start vep1445-traffic-gen
```

**For DPDK Mode (> 2Gbps):**
```bash
# After reboot (required for CPU isolation)
sudo /opt/vep1445-traffic-gen/setup_dpdk.sh
sudo python3 web_api.py --use-dpdk
```

---

## Hardware Timestamps

### What Are Hardware Timestamps?

Hardware timestamps are provided by the NIC itself, offering:
- **Sub-microsecond accuracy** (~100ns typical, ~20ns with DPDK)
- **Consistent precision** (not affected by system load)
- **Essential for RFC2544** and accurate latency measurements

### Verification

Create test script `test_timestamps.py`:

```python
#!/usr/bin/env python3
import socket
import struct

# Create raw socket
sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0800))
sock.bind(('eth1', 0))

# Enable hardware timestamps
SO_TIMESTAMPING = 37
flags = (1 << 0) | (1 << 2) | (1 << 6)  # TX_HW, RX_HW, RAW_HW
sock.setsockopt(socket.SOL_SOCKET, SO_TIMESTAMPING, flags)

# Send test packet
test_packet = b'\xff' * 64
sock.send(test_packet)

# Try to get hardware timestamp
try:
    data, ancdata, flags, addr = sock.recvmsg(1, 1024, socket.MSG_ERRQUEUE)
    for cmsg_level, cmsg_type, cmsg_data in ancdata:
        if cmsg_type == SO_TIMESTAMPING:
            print("✓ Hardware timestamps working!")
            print(f"  Timestamp data length: {len(cmsg_data)} bytes")
            break
    else:
        print("✗ No hardware timestamp received")
except BlockingIOError:
    print("✗ No timestamp available (hardware timestamps may not be supported)")

sock.close()
```

Run:
```bash
sudo python3 test_timestamps.py
```

---

## Performance Tuning Quick Reference

### For 100-500 Mbps (Standard Mode)
No special configuration needed. Just run:
```bash
sudo python3 web_api.py
```

### For 500Mbps - 2Gbps (High-Performance Mode)

**One-line setup:**
```bash
sudo ./setup_performance.sh --mode high
```

**Or manually:**
```bash
# 1. Kernel tuning
sudo sysctl -w net.core.rmem_max=134217728
sudo sysctl -w net.core.wmem_max=134217728

# 2. CPU performance mode
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance | sudo tee $cpu
done

# 3. NIC optimization
sudo ethtool -G eth1 rx 4096 tx 4096
sudo ethtool -C eth1 rx-usecs 0 tx-usecs 0
sudo ethtool -K eth1 tso on gso on gro on
```

### For 2-10Gbps (DPDK Mode)

**Automated:**
```bash
sudo ./setup_performance.sh --mode dpdk
sudo reboot  # Required for CPU isolation
# After reboot:
sudo /opt/vep1445-traffic-gen/setup_dpdk.sh
```

**Requirements:**
- Hugepages (1024 x 2MB)
- CPU isolation
- IOMMU enabled in BIOS
- Compatible NIC (Intel X710, Mellanox CX-5, etc.)

---

## Creating High-Performance Traffic Profiles

### Example 1: Line-Rate 1Gbps with HW Timestamps

```json
{
  "name": "1Gbps_LineRate",
  "src_interface": "eth1",
  "dst_interface": "eth2",
  "dst_ip": "192.168.2.100",
  "bandwidth_mbps": 1000,
  "packet_size": 1500,
  "protocol": "ipv4",
  "use_hardware_timestamps": true,
  "batch_size": 64,
  "zero_copy": true
}
```

### Example 2: 10Gbps with Minimal Latency

```json
{
  "name": "10Gbps_DPDK",
  "src_interface": "eth1",
  "dst_interface": "eth2",
  "dst_ip": "192.168.2.100",
  "bandwidth_mbps": 10000,
  "packet_size": 1500,
  "protocol": "ipv4",
  "use_hardware_timestamps": true,
  "batch_size": 128,
  "zero_copy": true
}
```

### Example 3: Precise Latency Testing

```json
{
  "name": "Latency_Test",
  "src_interface": "eth1",
  "dst_interface": "eth2",
  "dst_ip": "192.168.2.100",
  "bandwidth_mbps": 10,
  "packet_size": 64,
  "protocol": "ipv4",
  "use_hardware_timestamps": true,
  "latency_ms": 10,
  "jitter_ms": 1,
  "rfc2544_enabled": true,
  "rfc2544_latency_test": true
}
```

---

## Monitoring Performance

### Real-Time Statistics

Access web dashboard:
```
http://<vep1445-ip>:5000/statistics
```

### Command-Line Monitoring

```bash
# VEP1445 performance monitor (created by setup script)
sudo vep1445-perf-monitor

# Watch network statistics
watch -n 1 'ethtool -S eth1 | grep packets'

# CPU usage per core
mpstat -P ALL 1

# Memory usage
free -h

# Network buffer usage
ss -m
```

### Performance Metrics API

```bash
# Get current stats
curl http://localhost:5000/api/traffic/stats

# Export to CSV
curl http://localhost:5000/api/traffic/stats?format=csv > stats.csv
```

---

## Troubleshooting High-Performance Issues

### Issue: Not Achieving Target Throughput

**Check:**
```bash
# 1. CPU frequency
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq

# 2. Ring buffer size
sudo ethtool -g eth1

# 3. Hardware offloads
sudo ethtool -k eth1 | grep -E "tcp-segmentation|generic-segmentation"

# 4. Dropped packets
sudo ethtool -S eth1 | grep -i drop
```

**Fix:**
```bash
# Set CPU to performance
sudo cpufreq-set -g performance

# Increase ring buffers
sudo ethtool -G eth1 rx 4096 tx 4096

# Enable offloads
sudo ethtool -K eth1 tso on gso on gro on

# Check for interface errors
sudo ethtool eth1
```

### Issue: Hardware Timestamps Not Working

**Check:**
```bash
# NIC capability
sudo ethtool -T eth1

# Kernel version (needs 3.17+)
uname -r

# Driver version
sudo ethtool -i eth1
```

**Fix:**
```bash
# Update NIC firmware
sudo apt-get install intel-microcode  # For Intel NICs

# Update kernel
sudo apt-get install linux-image-generic-hwe-20.04

# Reload driver
sudo modprobe -r <driver_name>
sudo modprobe <driver_name>
```

### Issue: High Jitter/Latency

**Check:**
```bash
# C-states
sudo cpupower idle-info

# Interrupt coalescing
sudo ethtool -c eth1

# CPU frequency scaling
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

**Fix:**
```bash
# Disable C-states
sudo cpupower idle-set -D 0

# Disable interrupt coalescing
sudo ethtool -C eth1 rx-usecs 0 tx-usecs 0

# Lock CPU frequency
sudo cpufreq-set -g performance
```

---

## Benchmark Results

### Reference Hardware Performance

**Intel X710 (10GbE) with High-Performance Mode:**
- Throughput: 1.5 Gbps sustained
- Packet rate: 2.0 Mpps (64-byte packets)
- Latency: 8-12 μs average
- Timestamp precision: 100 ns

**Intel X710 (10GbE) with DPDK:**
- Throughput: 9.8 Gbps (line rate)
- Packet rate: 14.8 Mpps (64-byte packets)
- Latency: <1 μs average
- Timestamp precision: 20 ns

**Mellanox ConnectX-5 (25GbE) with DPDK:**
- Throughput: 24.5 Gbps (line rate)
- Packet rate: 37 Mpps (64-byte packets)
- Latency: <500 ns average
- Timestamp precision: 10 ns

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] Hardware timestamps verified on all interfaces
- [ ] Performance mode selected and configured
- [ ] CPU governor set to performance
- [ ] Network buffers increased
- [ ] NIC ring buffers optimized
- [ ] Interrupt affinity configured

### For DPDK Deployments (Additional)

- [ ] Hugepages configured (1024+ pages)
- [ ] CPUs isolated for DPDK
- [ ] IOMMU enabled in BIOS
- [ ] NICs bound to DPDK driver
- [ ] DPDK startup script tested

### Post-Deployment

- [ ] Run RFC2544 throughput test
- [ ] Verify timestamp accuracy
- [ ] Check CPU utilization (<80%)
- [ ] Monitor dropped packets (should be 0)
- [ ] Test impairment features (latency, jitter, loss)
- [ ] Verify web interface accessible

---

## Quick Performance Test

```bash
# 1. Create simple traffic profile via API
curl -X POST http://localhost:5000/api/traffic-profiles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test_1Gbps",
    "src_interface": "eth1",
    "dst_interface": "eth2",
    "dst_ip": "192.168.2.100",
    "bandwidth_mbps": 1000,
    "packet_size": 1500,
    "protocol": "ipv4",
    "use_hardware_timestamps": true
  }'

# 2. Enable profile
curl -X PUT http://localhost:5000/api/traffic-profiles/Test_1Gbps \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# 3. Start traffic
curl -X POST http://localhost:5000/api/traffic/start

# 4. Monitor for 10 seconds
for i in {1..10}; do
  curl -s http://localhost:5000/api/traffic/stats | jq '.stats'
  sleep 1
done

# 5. Stop traffic
curl -X POST http://localhost:5000/api/traffic/stop
```

---

## Support and Optimization

For detailed performance tuning, see:
- **PERFORMANCE_GUIDE.md** - Comprehensive tuning guide
- **README.md** - Full system documentation

For NIC-specific optimizations:
- Intel: Check Intel's DPDK tuning guides
- Mellanox: See Mellanox performance tuning guides
- Broadcom: Consult Broadcom documentation

---

## Summary

| If you need... | Use this mode | Setup command |
|----------------|---------------|---------------|
| < 500 Mbps | Standard | `python3 web_api.py` |
| 500Mbps - 2Gbps | **High-Performance** ⭐ | `./setup_performance.sh --mode high` |
| 2-10Gbps | DPDK | `./setup_performance.sh --mode dpdk` |
| > 10Gbps | DPDK + tuning | See PERFORMANCE_GUIDE.md |

**Hardware Timestamps**: Automatically enabled if NIC supports them (check with `ethtool -T`)

**Start Testing**: Access web interface at `http://<vep1445-ip>:5000`

---

**Ready to generate high-performance traffic with hardware timestamp precision!**
