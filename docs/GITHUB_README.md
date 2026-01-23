# VEP1445 Unified Traffic Generator

**Repository**: `netgen` (Network Generator)  
**Application**: VEP1445 Traffic Generator  
**Purpose**: Unified Copper (1G) + SFP (10G) Traffic Generation with Single GUI

---

## 🚀 Quick Start (From GitHub)

### Standard Deployment

```bash
# 1. Clone repository
cd /opt
sudo git clone https://github.com/YOUR_USERNAME/netgen.git

# 2. Enter directory (clones as 'netgen')
cd netgen

# 3. Update the fixed file (to resolve MAP_HUGETLB issue)
# The latest traffic_engine_unified.py has the fix

# 4. Run all-in-one installer
sudo ./install_allinone.sh
# Choose: Option 2 (System Directory)
# Choose: DPDK mode for both copper + SFP

# 5. Reboot (for DPDK)
sudo reboot

# 6. After reboot, bind SFP ports
cd /opt/vep1445-traffic-gen
sudo /opt/dpdk-23.11/usertools/dpdk-devbind.py --bind=vfio-pci <SFP1_PCI>
sudo /opt/dpdk-23.11/usertools/dpdk-devbind.py --bind=vfio-pci <SFP2_PCI>

# 7. Start system
sudo systemctl start vep1445

# 8. Access web interface
http://localhost:5000
```

---

## 📁 Directory Structure Explained

### Git Clone Creates
```
/opt/netgen/                    ← Repository name (your choice)
├── All source files
├── install_allinone.sh         ← Installer
└── Documentation
```

### Installer Creates
```
/opt/vep1445-traffic-gen/       ← Application installation
├── traffic_engine_unified.py   ← Running application
├── web_api.py
├── web/
└── All runtime files
```

**Why two directories?**
- `/opt/netgen` = Source repository (can be updated via git pull)
- `/opt/vep1445-traffic-gen` = Installed application (production files)

You can delete `/opt/netgen` after installation if desired.

---

## 🐛 Known Issues & Fixes

### Issue 1: AttributeError: module 'mmap' has no attribute 'MAP_HUGETLB'

**Symptom:**
```
AttributeError: module 'mmap' has no attribute 'MAP_HUGETLB'
```

**Cause:** Older Python versions don't have `MAP_HUGETLB` constant

**Fix:** The latest `traffic_engine_unified.py` has the fix. Update your files:

```bash
# If you already installed and get this error:
cd /opt/netgen
git pull  # Get latest fixes

# Copy fixed file to installation
sudo cp traffic_engine_unified.py /opt/vep1445-traffic-gen/

# Restart service
sudo systemctl restart vep1445
```

**Or use the quickfix script:**
```bash
cd /opt/netgen
sudo bash quickfix.sh
```

---

## 🔧 After Installation Fixes

If you've already run the installer but have issues:

### Quick Fix Script

```bash
cd /opt/netgen
sudo bash quickfix.sh
```

This will:
1. Copy the fixed files to `/opt/vep1445-traffic-gen`
2. Restart the service
3. Show you the web interface URL

---

## 📝 Naming Convention

| Name | Purpose | Location |
|------|---------|----------|
| **netgen** | Git repository name | `/opt/netgen` |
| **vep1445-traffic-gen** | Application name | `/opt/vep1445-traffic-gen` |
| **vep1445** | Systemd service name | `systemctl start vep1445` |

**All three refer to the same application!**

---

## 🎯 Deployment Workflow

```
┌─────────────────────────────────────────────┐
│ 1. Git Clone                                 │
│    cd /opt                                   │
│    sudo git clone .../netgen.git             │
│    → Creates: /opt/netgen                    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 2. Run Installer                             │
│    cd /opt/netgen                            │
│    sudo ./install_allinone.sh                │
│    → Creates: /opt/vep1445-traffic-gen       │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 3. Configure Performance                     │
│    Installer runs setup_performance.sh       │
│    → Configures: Kernel, NIC, DPDK           │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 4. Reboot (for DPDK)                         │
│    sudo reboot                               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 5. Bind SFP Ports                            │
│    dpdk-devbind.py --bind=vfio-pci <PCI>    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 6. Start Service                             │
│    sudo systemctl start vep1445              │
│    → Running from: /opt/vep1445-traffic-gen  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 7. Access Web GUI                            │
│    http://localhost:5000                     │
└─────────────────────────────────────────────┘
```

---

## 🔄 Updating from Git

```bash
# Get latest changes
cd /opt/netgen
sudo git pull

# If installer was updated, re-run it
sudo ./install_allinone.sh

# If only code files were updated, copy them
sudo cp traffic_engine_unified.py /opt/vep1445-traffic-gen/
sudo cp web_api.py /opt/vep1445-traffic-gen/
sudo cp web/index.html /opt/vep1445-traffic-gen/web/

# Restart service
sudo systemctl restart vep1445
```

---

## 📂 File Locations Reference

### Source Files (Git Repository)
```
/opt/netgen/
├── install_allinone.sh          ← Installer script
├── traffic_engine_unified.py    ← Latest engine code
├── web_api.py                   ← Latest API code
├── web/index.html               ← Latest GUI
├── setup_performance.sh         ← Performance config
└── Documentation/               ← All docs
```

### Installed Application
```
/opt/vep1445-traffic-gen/
├── traffic_engine_unified.py    ← Running engine
├── web_api.py                   ← Running API
├── web/index.html               ← Running GUI
├── config/                      ← User configs
└── logs/                        ← Runtime logs

/var/log/vep1445/
├── vep1445.log                  ← Main log
└── vep1445-error.log            ← Error log

/etc/systemd/system/
└── vep1445.service              ← Systemd service
```

---

## 🆘 Troubleshooting

### Service won't start

```bash
# Check service status
sudo systemctl status vep1445

# Check logs
sudo journalctl -u vep1445 -n 50

# Check Python errors
sudo tail -f /var/log/vep1445/vep1445-error.log
```

### MAP_HUGETLB error

```bash
# Update files from git
cd /opt/netgen
sudo git pull

# Run quickfix
sudo bash quickfix.sh
```

### Web interface not accessible

```bash
# Check if service is running
sudo systemctl status vep1445

# Check if port 5000 is listening
sudo netstat -tlnp | grep 5000

# Check firewall
sudo ufw status
sudo ufw allow 5000
```

### Need to reconfigure

```bash
# Re-run performance config
cd /opt/netgen
sudo bash setup_performance.sh --mode dpdk
```

---

## 📊 System Status Commands

```bash
# Service status
sudo systemctl status vep1445

# View logs (live)
sudo journalctl -u vep1445 -f

# View last 100 log lines
sudo journalctl -u vep1445 -n 100

# Check interface status
ip link show

# Check DPDK binding
sudo /opt/dpdk-23.11/usertools/dpdk-devbind.py --status

# Check hugepages
cat /proc/meminfo | grep Huge
```

---

## 🎯 Quick Commands

```bash
# Start
sudo systemctl start vep1445

# Stop
sudo systemctl stop vep1445

# Restart
sudo systemctl restart vep1445

# Enable auto-start
sudo systemctl enable vep1445

# Disable auto-start
sudo systemctl disable vep1445

# Check status
sudo systemctl status vep1445

# View logs
sudo journalctl -u vep1445 -f
```

---

## 📞 Support

- **Documentation**: See files in `/opt/netgen/`
- **Deployment Guide**: `DEPLOYMENT_UNIFIED.md`
- **Performance Guide**: `PERFORMANCE_GUIDE.md`
- **Installation Guide**: `INSTALL_GUIDE.md`

---

## 🎁 Features

- ✅ 5 Copper ports (1G) + 2 SFP ports (10G)
- ✅ Single web GUI for all interfaces
- ✅ 100Mbps to 10Gbps traffic generation
- ✅ Hardware timestamps (sub-microsecond)
- ✅ DPDK line-rate performance
- ✅ Multi-protocol support
- ✅ Network impairments
- ✅ RFC2544 testing

---

**Installation**: `sudo ./install_allinone.sh`  
**Web Interface**: `http://localhost:5000`  
**Service**: `sudo systemctl start vep1445`
