# VEP1445 Lab Network Setup Guide
## Traffic Generator for Multi-LAN Testing Environment

---

## 🎯 Your Use Case (Confirmed)

**Traffic Generator for Lab Networks**

```
Your Lab Setup:
┌─────────────────────────────────────────────────────────────┐
│                     Lab Network                              │
│                                                               │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐      │
│  │ LAN 1  │    │ LAN 2  │    │ LAN 3  │    │ LAN 4  │      │
│  │ Switch │    │ Switch │    │ Switch │    │ Switch │      │
│  └───┬────┘    └───┬────┘    └───┬────┘    └───┬────┘      │
│      │             │             │             │            │
│      │             │             │             │            │
│  ┌───┴─────────────┴─────────────┴─────────────┴────┐      │
│  │                                                     │      │
│  │              VEP1445 Traffic Generator              │      │
│  │                                                     │      │
│  │  Port 1  Port 2  Port 3  Port 4  Port 5  10G 10G  │      │
│  │  (eno2)  (eno3)  (eno4)  (enp7)  (enp8)  (sfp) .. │      │
│  └─────────────────────────────────────────────────────┘      │
│                                                               │
│  Traffic Flows (Examples):                                   │
│  • LAN 1 → LAN 2: 500 Mbps, DSCP 46, 5ms latency           │
│  • LAN 3 → LAN 4: 800 Mbps, 2% packet loss                 │
│  • LAN 2 ↔ LAN 5: Bidirectional 600 Mbps                   │
│  • 10G ↔ 10G: Line-rate testing                             │
│                                                               │
│  All configured from Web GUI!                                │
└─────────────────────────────────────────────────────────────┘
```

**What VEP1445 Does:**
- ✅ Generates customizable traffic between LAN ports
- ✅ Configure bandwidth (100Mbps - 10Gbps)
- ✅ Set QoS/DSCP markings
- ✅ Add impairments (latency, jitter, packet loss)
- ✅ Measure throughput, latency, packet loss
- ✅ RFC2544 testing
- ✅ All from single web GUI

**What VEP1445 Does NOT Do:**
- ✗ Route traffic (your lab switches do that)
- ✗ Need DHCP/IPs for operation (generates packets)
- ✗ Act as gateway

**Your lab switches handle the actual routing between LANs!**

---

## 📋 Complete Setup Steps

### **Step 1: Unbind Interfaces from DPDK**

Currently, most interfaces are bound to DPDK. For traffic generation in your lab setup, we want them in kernel mode (except 10G SFP which can stay in DPDK).

```bash
# Unbind copper/1G interfaces from DPDK to kernel
sudo dpdk-devbind.py -u 0000:02:00.0  # I350 #1
sudo dpdk-devbind.py -u 0000:02:00.1  # I350 #2
sudo dpdk-devbind.py -u 0000:02:00.3  # I350 #3
sudo dpdk-devbind.py -u 0000:07:00.0  # X553 1G #1
sudo dpdk-devbind.py -u 0000:07:00.1  # X553 1G #2

# Bind back to kernel drivers
sudo dpdk-devbind.py -b igb 0000:02:00.0
sudo dpdk-devbind.py -b igb 0000:02:00.1
sudo dpdk-devbind.py -b igb 0000:02:00.3
sudo dpdk-devbind.py -b ixgbe 0000:07:00.0
sudo dpdk-devbind.py -b ixgbe 0000:07:00.1

# Keep 10G SFP in DPDK (already bound - leave as is)
# 0000:05:00.0 stays as drv=vfio-pci
# 0000:05:00.1 stays as drv=vfio-pci
```

**Verify:**
```bash
sudo dpdk-devbind.py --status
# Should show 5 interfaces in "kernel driver" section
# Should show 2 x 10G in "DPDK-compatible driver" section
```

---

### **Step 2: Check Interface Names**

After unbinding, check what interface names Linux assigned:

```bash
ip link show | grep -E '^[0-9]+: (en|eth)'
```

You'll see something like:
```
2: eno1: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
3: eno2: <BROADCAST,MULTICAST> ...
4: eno3: <BROADCAST,MULTICAST> ...
5: eno4: <BROADCAST,MULTICAST> ...
6: enp7s0f0: <BROADCAST,MULTICAST> ...
7: enp7s0f1: <BROADCAST,MULTICAST> ...
```

Write these down - you'll need them!

---

### **Step 3: Run Interface Configuration Script**

This script auto-detects your interfaces and configures VEP1445:

```bash
cd /opt/vep1445-traffic-gen
sudo bash configure_interfaces.sh
```

**The script will:**
1. Detect all available network interfaces
2. Show you details (speed, driver, MAC)
3. Let you select which to use (or use all)
4. Generate configuration for VEP1445
5. Update web_api.py
6. Offer to bring interfaces up
7. Offer to start VEP1445

**Interactive prompts:**
```
Found 6 network interfaces:
  [0] eno1
      Type: 1G Copper
      Speed: 1000
  [1] eno2
      Type: 1G Copper
      Speed: 1000
  [2] eno3
      Type: 1G Copper
      Speed: 1000
  ...

Select interfaces to use: <press Enter to use all>
Bring up interfaces now? [Y/n]: y
Start VEP1445 now? [Y/n]: y
```

---

### **Step 4: Access Web GUI**

Once VEP1445 starts:

```
http://localhost:5000
```

Or from another machine:
```
http://<vep1445-ip>:5000
```

---

## 🎮 Using VEP1445 in Your Lab

### **Creating Traffic Profiles**

**Example 1: LAN 1 → LAN 2 (VoIP Traffic)**

1. In web GUI, go to "Traffic Profiles"
2. Click "+ ADD TRAFFIC PROFILE"
3. Configure:
   ```
   Name: LAN1_to_LAN2_VoIP
   Source Interface: eno2 (plugged into LAN 1 switch)
   Destination Interface: eno3 (plugged into LAN 2 switch)
   Destination IP: 192.168.2.100 (any IP in LAN 2)
   Bandwidth: 500 Mbps
   Packet Size: 200 bytes
   Protocol: IPv4
   DSCP: 46 (EF - Voice)
   Latency: 0 ms
   Jitter: 0 ms
   Packet Loss: 0%
   ```
4. Enable profile (toggle switch)
5. Click "▶ START TRAFFIC"

**What happens:**
- VEP1445 generates packets on eno2 (LAN 1)
- Packets go to your LAN 1 switch
- Switch routes to LAN 2 switch
- Arrives at eno3 (LAN 2)
- Measures throughput/latency

---

**Example 2: LAN 3 → LAN 4 (With Impairments)**

```
Name: LAN3_to_LAN4_Impaired
Source: eno4 (LAN 3)
Destination: enp7s0f0 (LAN 4)
Bandwidth: 800 Mbps
Packet Size: 1500 bytes
DSCP: 26 (AF31)
Latency: 50 ms       ← Adds delay
Jitter: 10 ms        ← Adds jitter
Packet Loss: 2%      ← Drops 2% of packets
```

**Use case:** Test how applications behave on impaired networks

---

**Example 3: Bidirectional Traffic**

Create TWO profiles:

**Profile 1 (LAN 2 → LAN 5):**
```
Source: eno3 (LAN 2)
Destination: enp7s0f1 (LAN 5)
Bandwidth: 600 Mbps
```

**Profile 2 (LAN 5 → LAN 2):**
```
Source: enp7s0f1 (LAN 5)
Destination: eno3 (LAN 2)
Bandwidth: 600 Mbps
```

Both enabled = Bidirectional 600 Mbps traffic!

---

**Example 4: 10G Line-Rate Test**

```
Name: 10G_LineRate
Source: sfp0 (10G SFP port 1)
Destination: sfp1 (10G SFP port 2)
Bandwidth: 10000 Mbps
Packet Size: 1500 bytes
DSCP: 0
```

Tests maximum 10G throughput!

---

### **Multiple Concurrent Streams**

You can run **many profiles simultaneously**:

```
Active Profiles:
✓ LAN1_to_LAN2_VoIP     (500 Mbps)
✓ LAN2_to_LAN3_Video    (2000 Mbps)  
✓ LAN3_to_LAN4_Data     (800 Mbps)
✓ LAN4_to_LAN5_Bulk     (1500 Mbps)
✓ 10G_Backbone_Test     (10000 Mbps)

All running at the same time!
Total throughput: 14.8 Gbps
```

---

## 📊 Monitoring & Statistics

### **In Web GUI:**

1. Go to "Statistics" tab
2. See real-time metrics:
   - TX/RX packets per profile
   - Throughput (Mbps)
   - Packet loss
   - Latency
   - Jitter

3. Export data:
   - JSON format
   - CSV format

---

### **Command Line:**

```bash
# Get statistics via API
curl http://localhost:5000/api/traffic/stats

# Get interface status
curl http://localhost:5000/api/interfaces

# Get capabilities
curl http://localhost:5000/api/capabilities
```

---

## 🔧 Common Lab Scenarios

### **Scenario 1: Test Switch Performance**

**Goal:** Verify switch can handle 5 Gbps aggregate

```
Create 5 profiles:
- LAN1 → LAN2: 1000 Mbps
- LAN2 → LAN3: 1000 Mbps
- LAN3 → LAN4: 1000 Mbps
- LAN4 → LAN5: 1000 Mbps
- LAN5 → LAN1: 1000 Mbps

Start all → Monitor for packet loss
If no loss = switch handles 5 Gbps ✓
```

---

### **Scenario 2: Test QoS Policies**

**Goal:** Verify DSCP markings are preserved

```
Create profiles with different DSCP:
- Profile 1: DSCP 46 (Voice) - 200 Mbps
- Profile 2: DSCP 26 (Video) - 500 Mbps
- Profile 3: DSCP 0 (Best Effort) - 300 Mbps

Use packet capture on switches to verify DSCP
```

---

### **Scenario 3: Test Under Impaired Conditions**

**Goal:** See how applications handle network problems

```
Profile: LAN1 → LAN2
- Normal: 1000 Mbps, 0ms latency, 0% loss
- Impaired: 1000 Mbps, 100ms latency, 5% loss

Compare application performance
```

---

### **Scenario 4: RFC2544 Compliance Test**

**Goal:** Standards-based throughput testing

```
Enable RFC2544 in profile:
✓ Throughput test
✓ Latency test
✓ Frame loss test
✓ Back-to-back test

Test with frame sizes: 64, 128, 256, 512, 1024, 1518
Generates compliance report
```

---

## 🎯 Lab Network Configuration

### **Physical Connections:**

```
VEP1445 Port   →   Lab Switch   →   Lab Network
─────────────────────────────────────────────────
eno2 (Port 1)  →   LAN 1 Switch →   192.168.1.0/24
eno3 (Port 2)  →   LAN 2 Switch →   192.168.2.0/24
eno4 (Port 3)  →   LAN 3 Switch →   192.168.3.0/24
enp7s0f0 (4)   →   LAN 4 Switch →   192.168.4.0/24
enp7s0f1 (5)   →   LAN 5 Switch →   192.168.5.0/24
sfp0 (10G)     →   10G Backbone →   10.0.0.0/24
sfp1 (10G)     →   10G Backbone →   10.0.1.0/24
```

**Each VEP1445 port connects to a different switch in your lab**

---

### **IP Addressing (Not Required but Helpful)**

VEP1445 generates packets with any destination IP you specify. You can:

**Option A: Use any IPs (no configuration needed)**
```
Profile destination: 192.168.2.100
VEP1445 generates packets to this IP
Doesn't need to exist - just for packet headers
```

**Option B: Assign IPs to interfaces (optional)**
```bash
# Only if you want VEP1445 to respond to pings
sudo ip addr add 192.168.1.10/24 dev eno2
sudo ip addr add 192.168.2.10/24 dev eno3
# etc...
```

**For traffic generation, Option A is fine!**

---

## 🐛 Troubleshooting

### **"No such device" error**

**Cause:** Interface name doesn't exist

**Fix:**
```bash
# Check actual interface names
ip link show

# Run configure_interfaces.sh to auto-detect
sudo bash configure_interfaces.sh
```

---

### **"Permission denied" on socket**

**Cause:** Need root for raw sockets

**Fix:**
```bash
# Always run with sudo
sudo python3 web_api.py
```

---

### **Interface won't come up**

**Fix:**
```bash
# Bring up interface manually
sudo ip link set eno2 up
sudo ip link set eno3 up
# etc...
```

---

### **No traffic being generated**

**Check:**
1. Interfaces are UP: `ip link show`
2. Cables connected
3. Profile is ENABLED (toggle switch in GUI)
4. Traffic is STARTED (click start button)
5. Check logs: `tail -f /var/log/vep1445/vep1445.log`

---

### **Statistics show 0**

**Possible causes:**
- Interface down
- Cable not connected
- Wrong destination interface selected
- Bandwidth set to 0

---

## 🎁 Advanced Features

### **Multi-Protocol Support**

VEP1445 supports:
- ✅ IPv4
- ✅ IPv6
- ✅ MPLS (label stacking)
- ✅ VXLAN (overlay networks)
- ✅ Q-in-Q (802.1ad double tagging)

Configure in profile settings!

---

### **Hardware Timestamps**

All interfaces use hardware timestamps for:
- Sub-microsecond precision
- Accurate latency measurements
- Jitter detection

Enabled automatically!

---

### **Batch Processing**

VEP1445 uses optimized batch processing:
- Sends 64-128 packets per syscall
- Reduces CPU overhead
- Maximizes throughput

No configuration needed!

---

## ✅ Quick Reference

### **Start VEP1445**
```bash
cd /opt/vep1445-traffic-gen
sudo python3 web_api.py
```

### **Stop VEP1445**
```bash
sudo pkill -f "python3.*web_api.py"
```

### **View Logs**
```bash
tail -f /var/log/vep1445/vep1445.log
```

### **Check Interfaces**
```bash
ip link show
ethtool eno2
```

### **Check DPDK Status**
```bash
sudo dpdk-devbind.py --status
```

### **Restart After Config Change**
```bash
sudo pkill -f web_api
sudo python3 web_api.py
```

---

## 📞 Support Files

- **Interface Detection:** `detect_interfaces.sh`
- **Auto Configuration:** `configure_interfaces.sh`
- **Use Case Guide:** `USE_CASE_CLARIFICATION.md`
- **Performance Tuning:** `PERFORMANCE_GUIDE.md`
- **Full Documentation:** `README.md`

---

## 🎯 Summary

**Your Setup:**
- VEP1445 plugged into 5+ lab networks
- Generates customizable traffic between LANs
- Configure bandwidth, QoS, impairments
- All from web GUI

**Steps:**
1. Unbind interfaces from DPDK ✓
2. Run `configure_interfaces.sh` ✓
3. Start VEP1445 ✓
4. Access http://localhost:5000 ✓
5. Create traffic profiles ✓
6. Generate traffic! ✓

**Perfect for your lab environment!** 🚀
