# VEP1445 High-Performance Configuration Guide
## Achieving 100Mbps - 10Gbps Line Rate with Hardware Timestamps

This guide covers performance optimization for the VEP1445 traffic generator to achieve line-rate performance from 100Mbps to 10Gbps with hardware timestamping support.

## Performance Modes

The VEP1445 traffic engine supports three performance modes:

### Mode 1: Standard (100-500 Mbps)
- Uses optimized Python raw sockets
- Software timestamps
- **Setup**: Standard installation, no special configuration

### Mode 2: High-Performance (500Mbps - 2Gbps)
- Optimized raw sockets with zero-copy
- Hardware timestamps
- Packet rings and memory pools
- **Setup**: Kernel tuning + hardware timestamp support

### Mode 3: Ultra-Performance (2Gbps - 10Gbps+)
- DPDK (Data Plane Development Kit)
- Hardware timestamps
- Kernel bypass for maximum performance
- **Setup**: DPDK installation + hugepages + CPU isolation

## Hardware Timestamp Support

### Check Hardware Capability

```bash
# Check if your NIC supports hardware timestamps
ethtool -T eth1

# Look for:
# Capabilities:
#   hardware-transmit     (yes)
#   hardware-receive      (yes)
#   hardware-raw-clock    (yes)
```

### Enable Hardware Timestamps

Hardware timestamps are automatically enabled by the engine if supported. No manual configuration needed.

### Supported NICs

NICs with full hardware timestamp support:
- Intel X710, XL710, XXV710
- Intel I350, I210, I211
- Intel 82599, X520, X540
- Mellanox ConnectX-4, ConnectX-5, ConnectX-6
- Broadcom BCM57xx series
- Solarflare SFN series

## Mode 2: High-Performance Setup (500Mbps - 2Gbps)

### 1. Kernel Network Tuning

Create `/etc/sysctl.d/99-vep1445-network.conf`:

```bash
# Increase network buffers
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.core.rmem_default = 16777216
net.core.wmem_default = 16777216

# Increase socket buffers
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728

# Increase netdev backlog
net.core.netdev_max_backlog = 300000

# Increase number of packets queued on INPUT side
net.core.netdev_budget = 600

# Disable TCP timestamps for lower overhead
net.ipv4.tcp_timestamps = 0

# Enable TCP window scaling
net.ipv4.tcp_window_scaling = 1

# Increase local port range
net.ipv4.ip_local_port_range = 1024 65535
```

Apply settings:
```bash
sudo sysctl -p /etc/sysctl.d/99-vep1445-network.conf
```

### 2. Network Interface Optimization

```bash
# Disable interrupt coalescing for low latency
sudo ethtool -C eth1 rx-usecs 0 tx-usecs 0

# Increase ring buffer sizes
sudo ethtool -G eth1 rx 4096 tx 4096

# Enable all hardware offloads
sudo ethtool -K eth1 gso on
sudo ethtool -K eth1 tso on
sudo ethtool -K eth1 gro on

# Set interrupt affinity (pin to specific CPU cores)
# Find IRQ number
IRQ=$(cat /proc/interrupts | grep eth1 | awk '{print $1}' | tr -d ':')

# Set affinity to core 1
echo 2 | sudo tee /proc/irq/$IRQ/smp_affinity

# For multi-queue NICs, spread across cores
# This is interface-specific
```

### 3. CPU Governor

Set CPU to performance mode:
```bash
sudo apt-get install cpufrequtils
sudo cpufreq-set -g performance

# Or for all CPUs
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance | sudo tee $cpu
done
```

### 4. Disable Power Management

```bash
# Disable C-states for lower latency
sudo cpupower idle-set -D 0

# Disable CPU frequency scaling
echo 1 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo
```

### 5. Install and Run

```bash
sudo pip3 install -r requirements_highperf.txt

# Use the high-performance engine
sudo python3 traffic_engine_highperf.py
```

**Expected Performance**: 500Mbps - 2Gbps with <10μs jitter

## Mode 3: DPDK Setup (2Gbps - 10Gbps+)

### Prerequisites

- Compatible NIC (Intel, Mellanox recommended)
- Hugepage support
- IOMMU support (VT-d for Intel, AMD-Vi for AMD)
- Isolated CPU cores

### 1. Install DPDK

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y build-essential libnuma-dev python3-pip \
    python3-pyelftools pkg-config meson ninja-build

# Download DPDK (version 23.11 LTS recommended)
cd /opt
sudo wget https://fast.dpdk.org/rel/dpdk-23.11.tar.xz
sudo tar xf dpdk-23.11.tar.xz
cd dpdk-23.11

# Build DPDK
meson build
cd build
ninja
sudo ninja install
sudo ldconfig
```

### 2. Configure Hugepages

```bash
# Reserve 2GB hugepages (1024 x 2MB pages)
echo 1024 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# Make permanent - add to /etc/sysctl.conf
echo "vm.nr_hugepages=1024" | sudo tee -a /etc/sysctl.conf

# Mount hugepages
sudo mkdir -p /mnt/huge
sudo mount -t hugetlbfs nodev /mnt/huge

# Make permanent - add to /etc/fstab
echo "nodev /mnt/huge hugetlbfs defaults 0 0" | sudo tee -a /etc/fstab
```

### 3. CPU Isolation

Isolate CPUs for DPDK (example: isolate cores 2-5):

Edit `/etc/default/grub`:
```bash
GRUB_CMDLINE_LINUX="isolcpus=2,3,4,5 nohz_full=2,3,4,5 rcu_nocbs=2,3,4,5"
```

Update GRUB:
```bash
sudo update-grub
sudo reboot
```

### 4. Bind NICs to DPDK

```bash
# Load kernel modules
sudo modprobe vfio-pci
sudo modprobe uio_pci_generic

# Bind network interface to DPDK driver
cd /opt/dpdk-23.11

# Find PCI address of your NIC
./usertools/dpdk-devbind.py --status

# Bind to DPDK (example: eth1 at 0000:02:00.0)
sudo ./usertools/dpdk-devbind.py --bind=vfio-pci 0000:02:00.0

# Verify binding
./usertools/dpdk-devbind.py --status
```

### 5. Install DPDK Python Bindings

```bash
# Install dpdk-python package
cd /opt
git clone https://github.com/DPDK/dpdk-python.git
cd dpdk-python
sudo pip3 install .
```

### 6. Configure VEP1445 for DPDK

Edit `web_api.py` or create config file:

```python
# Enable DPDK mode
USE_DPDK = True

# Specify which interfaces to bind
DPDK_INTERFACES = ['eth1', 'eth2', 'eth3', 'eth4', 'eth5']

# CPU core assignments
DPDK_LCORES = "2,3,4,5"  # Use isolated cores

# Memory channels (check your platform)
DPDK_MEMORY_CHANNELS = 4
```

### 7. Run with DPDK

```bash
# Run with DPDK support
sudo python3 web_api.py --use-dpdk

# Or set environment variable
export VEP1445_USE_DPDK=1
sudo python3 web_api.py
```

**Expected Performance**: 2Gbps - 10Gbps+ with <1μs jitter

## Performance Verification

### 1. Check Packet Rate

```bash
# Monitor interface statistics
watch -n 1 'ethtool -S eth1 | grep packets'

# Or use the web interface statistics tab
```

### 2. Measure Hardware Timestamps

```python
# Test script to verify hardware timestamps
import socket
import struct

sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0800))
sock.bind(('eth1', 0))

# Enable hardware timestamps
SO_TIMESTAMPING = 37
flags = (1 << 0) | (1 << 2) | (1 << 6)  # TX_HW, RX_HW, RAW_HW
sock.setsockopt(socket.SOL_SOCKET, SO_TIMESTAMPING, flags)

# Send packet and retrieve timestamp
sock.send(b'test' * 256)

# Get timestamp from error queue
try:
    data, ancdata, flags, addr = sock.recvmsg(1, 1024, socket.MSG_ERRQUEUE)
    for cmsg_level, cmsg_type, cmsg_data in ancdata:
        if cmsg_type == SO_TIMESTAMPING:
            print("Hardware timestamp retrieved successfully!")
            break
except BlockingIOError:
    print("No hardware timestamp available")
```

### 3. Benchmark Throughput

Use the built-in RFC2544 throughput test:

```bash
# Via API
curl -X POST http://localhost:5000/api/rfc2544/start \
  -H "Content-Type: application/json" \
  -d '{"profile_name": "Test_Profile", "throughput_test": true}'

# Or use web interface RFC2544 tab
```

### 4. Monitor CPU Usage

```bash
# Check CPU usage by core
mpstat -P ALL 1

# Monitor specific process
top -p $(pgrep -f web_api.py)

# Check context switches (should be low for DPDK)
pidstat -w 1
```

## Troubleshooting Performance Issues

### Issue: Not Reaching Expected Throughput

**Diagnosis:**
```bash
# Check for dropped packets
ethtool -S eth1 | grep drop

# Check CPU usage
top

# Check for interrupt storms
cat /proc/interrupts | grep eth1

# Check ring buffer usage
ethtool -g eth1
```

**Solutions:**
1. Increase ring buffer sizes: `sudo ethtool -G eth1 rx 4096 tx 4096`
2. Enable offloads: `sudo ethtool -K eth1 tso on gso on gro on`
3. Pin interrupts to specific cores
4. Increase batch size in traffic profiles

### Issue: High Latency/Jitter

**Diagnosis:**
```bash
# Check for CPU frequency scaling
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq

# Check for C-states
cpupower idle-info

# Check for interrupt coalescing
ethtool -c eth1
```

**Solutions:**
1. Disable CPU frequency scaling: `sudo cpufreq-set -g performance`
2. Disable C-states: `sudo cpupower idle-set -D 0`
3. Disable interrupt coalescing: `sudo ethtool -C eth1 rx-usecs 0 tx-usecs 0`
4. Use DPDK mode for kernel bypass

### Issue: DPDK Initialization Fails

**Diagnosis:**
```bash
# Check hugepages
cat /proc/meminfo | grep Huge

# Check IOMMU
dmesg | grep -i iommu

# Check PCI device
lspci | grep Ethernet
```

**Solutions:**
1. Verify hugepages: `echo 1024 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages`
2. Enable IOMMU in BIOS
3. Use correct DPDK driver (vfio-pci for most modern systems)
4. Check DPDK logs: `cat /var/log/dpdk.log`

### Issue: Hardware Timestamps Not Working

**Diagnosis:**
```bash
# Check NIC capabilities
ethtool -T eth1

# Check kernel version (needs 3.17+)
uname -r

# Check for PTP support
ethtool -T eth1 | grep PTP
```

**Solutions:**
1. Update NIC firmware
2. Update kernel to 4.x or newer
3. Enable PTP: `sudo ethtool -s eth1 phc_index 0`
4. Check driver version: `ethtool -i eth1`

## Performance Optimization Checklist

### For 100-500 Mbps:
- [ ] Standard installation complete
- [ ] Interfaces configured
- [ ] Traffic profiles created

### For 500Mbps - 2Gbps:
- [ ] Kernel network tuning applied
- [ ] CPU governor set to performance
- [ ] NIC ring buffers increased
- [ ] Hardware offloads enabled
- [ ] Interrupt affinity configured

### For 2Gbps - 10Gbps:
- [ ] DPDK installed
- [ ] Hugepages configured (1024+ pages)
- [ ] CPUs isolated for DPDK
- [ ] NICs bound to DPDK driver
- [ ] DPDK mode enabled in VEP1445

### For Hardware Timestamps:
- [ ] NIC supports hardware timestamps (check with `ethtool -T`)
- [ ] Kernel 3.17 or newer
- [ ] PTP support enabled
- [ ] Timestamps enabled in traffic profile

## Benchmark Results

Expected performance on reference hardware:

| Mode | Hardware | Throughput | Latency | Timestamp Accuracy |
|------|----------|------------|---------|-------------------|
| Standard | Generic NIC | 100-500 Mbps | ~100μs | Software (~1ms) |
| High-Perf | Intel I350 | 500Mbps-2Gbps | ~10μs | Hardware (~100ns) |
| DPDK | Intel X710 | 2-10Gbps | <1μs | Hardware (~20ns) |
| DPDK | Mellanox CX-5 | 5-25Gbps | <500ns | Hardware (~10ns) |

## Advanced: Custom DPDK Configuration

For maximum performance, create custom DPDK configuration:

```bash
# /opt/vep1445/dpdk.conf

# EAL (Environment Abstraction Layer) options
--lcores='(0-1)@0,(2-3)@1,(4-5)@2'  # Core mapping
--socket-mem=2048,2048               # Memory per NUMA node
-n 4                                  # Memory channels
--proc-type=primary                   # Process type
--file-prefix=vep1445                # Shared memory prefix

# Port configuration
--vdev=net_pcap0,iface=eth1          # Virtual device for testing
--log-level=8                         # Debug level

# Performance options
--no-telemetry                        # Disable telemetry
--in-memory                           # Use in-memory mode
```

Load configuration:
```bash
sudo python3 web_api.py --dpdk-config=/opt/vep1445/dpdk.conf
```

## Monitoring and Metrics

### Real-time Performance Dashboard

Access via web interface:
```
http://<vep1445-ip>:5000/statistics
```

Metrics include:
- Packets/second (PPS)
- Bits/second (throughput)
- CPU utilization per core
- Memory usage
- Timestamp accuracy
- Latency distribution

### Export Metrics

```bash
# Export to CSV
curl http://localhost:5000/api/traffic/stats?format=csv > stats.csv

# Export to JSON
curl http://localhost:5000/api/traffic/stats > stats.json

# Prometheus metrics endpoint
curl http://localhost:5000/metrics
```

## Production Deployment

### Systemd Service with Performance Options

Create `/etc/systemd/system/vep1445-highperf.service`:

```ini
[Unit]
Description=VEP1445 High-Performance Traffic Generator
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vep1445-traffic-gen
Environment="VEP1445_USE_DPDK=1"
Environment="VEP1445_LCORES=2,3,4,5"
ExecStartPre=/opt/vep1445-traffic-gen/setup_hugepages.sh
ExecStart=/usr/bin/python3 /opt/vep1445-traffic-gen/web_api.py
CPUAffinity=2 3 4 5
CPUQuota=400%
Nice=-20
IOSchedulingClass=realtime
IOSchedulingPriority=0
LimitMEMLOCK=infinity
LimitNOFILE=1048576
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vep1445-highperf
sudo systemctl start vep1445-highperf
```

## Security Considerations for High-Performance Mode

1. **DPDK runs as root** - Ensure proper firewall rules
2. **Direct hardware access** - Isolate on management network
3. **Huge pages** - Can be exhausted, set limits
4. **CPU isolation** - May affect other services

## Summary

| Target Rate | Recommended Mode | Key Requirements |
|-------------|-----------------|------------------|
| 100-500 Mbps | Standard | None |
| 500Mbps-2Gbps | High-Performance | Kernel tuning, HW timestamps |
| 2-10Gbps | DPDK | Hugepages, CPU isolation, DPDK |
| >10Gbps | DPDK + Optimization | Multi-queue NIC, advanced tuning |

For most use cases, High-Performance mode (500Mbps-2Gbps) provides excellent results without the complexity of DPDK.

---

**Next Steps:**
1. Choose your performance mode based on requirements
2. Follow the setup instructions for that mode
3. Verify performance using RFC2544 tests
4. Fine-tune based on your specific hardware

**Need Help?** Check logs at `/var/log/vep1445/` and run diagnostics with `ethtool`, `mpstat`, and `perf`.
