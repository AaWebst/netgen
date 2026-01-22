# VEP1445 Traffic Generator - Complete File Structure

## Directory Structure

```
vep1445-traffic-gen/
│
├── Documentation Files (READ THESE FIRST!)
│   ├── README_HIGHPERF.md          (11 KB)  ⭐ START HERE - Quick deployment guide
│   ├── PERFORMANCE_GUIDE.md        (14 KB)  📊 Complete performance tuning
│   ├── README.md                   (17 KB)  📖 Full system documentation  
│   └── QUICKSTART.md               (7.4 KB) 🚀 5-minute getting started
│
├── Core Engine Files
│   ├── traffic_engine_highperf.py  (29 KB)  ⚡ HIGH-PERFORMANCE ENGINE (100Mbps-10Gbps)
│   ├── traffic_engine.py           (36 KB)  📦 Standard engine (original)
│   └── web_api.py                  (17 KB)  🌐 REST API backend (Flask)
│
├── Web Interface
│   └── web/
│       └── index.html              (51 KB)  🖥️  Professional web GUI (NOC-style)
│
├── Configuration Files
│   ├── sample_config.json          (5.7 KB) 📝 Example traffic profiles
│   ├── requirements.txt            (44 B)   📦 Python deps (standard)
│   └── requirements_highperf.txt   (416 B)  📦 Python deps (high-performance)
│
├── Installation Scripts
│   ├── install.sh                  (5.8 KB) 📥 Automated installation
│   ├── setup_performance.sh        (15 KB)  ⚡ Performance configuration (IMPORTANT!)
│   └── start_vep1445.sh            (4.9 KB) ▶️  Manual startup script
│
└── System Service
    └── vep1445-traffic-gen.service (845 B)  ⚙️  Systemd service file

```

---

## File Descriptions

### 📚 Documentation Files (Start Here!)

#### README_HIGHPERF.md ⭐ **[START WITH THIS]**
- **Size**: 11 KB
- **Purpose**: Quick deployment guide for high-performance setup
- **Covers**:
  - Performance modes (Standard/High-Perf/DPDK)
  - Hardware timestamp verification
  - One-command setup instructions
  - Troubleshooting quick reference
  - Performance benchmarks
- **When to use**: First file to read for 100Mbps-10Gbps deployments

#### PERFORMANCE_GUIDE.md
- **Size**: 14 KB  
- **Purpose**: Comprehensive performance tuning encyclopedia
- **Covers**:
  - Detailed DPDK installation
  - Kernel tuning parameters
  - CPU isolation and hugepages
  - NIC-specific optimizations
  - Advanced troubleshooting
  - Production deployment checklist
- **When to use**: Deep-dive reference when optimizing for specific throughput

#### README.md
- **Size**: 17 KB
- **Purpose**: Complete system documentation
- **Covers**:
  - System architecture
  - All features (protocols, impairments, RFC2544)
  - API reference
  - Configuration examples
  - Troubleshooting guide
- **When to use**: Reference for features, protocols, and standard operation

#### QUICKSTART.md
- **Size**: 7.4 KB
- **Purpose**: 5-minute getting started guide
- **Covers**:
  - Basic installation steps
  - First traffic profile creation
  - Common scenarios
  - Essential troubleshooting
- **When to use**: First-time users wanting immediate results

---

### ⚙️ Core Engine Files

#### traffic_engine_highperf.py ⭐ **[USE THIS FOR PERFORMANCE]**
- **Size**: 29 KB
- **Purpose**: High-performance traffic engine (100Mbps-10Gbps)
- **Features**:
  - Hardware timestamp support (sub-microsecond precision)
  - Zero-copy packet transmission (memory-mapped rings)
  - Batch processing (64+ packets per syscall)
  - Memory pools with hugepage support
  - DPDK integration (optional, for 2-10Gbps+)
  - Multi-process architecture
- **Performance**: 500Mbps-2Gbps (optimized mode), 2-10Gbps+ (DPDK mode)
- **When to use**: Any deployment requiring >100Mbps or hardware timestamps

#### traffic_engine.py
- **Size**: 36 KB
- **Purpose**: Original/standard traffic engine
- **Features**:
  - Network discovery (ARP/DHCP)
  - Multi-protocol support (IPv4/6, MPLS, VXLAN, Q-in-Q)
  - Network impairments (latency, jitter, loss)
  - RFC2544 testing
- **Performance**: Up to ~500 Mbps
- **When to use**: Testing, development, or <500Mbps requirements

#### web_api.py
- **Size**: 17 KB
- **Purpose**: Flask-based REST API backend
- **Features**:
  - RESTful API endpoints
  - Interface management
  - Traffic profile CRUD operations
  - Statistics collection
  - Configuration save/load
- **Integration**: Works with both traffic engines
- **Port**: 5000 (default)

---

### 🖥️ Web Interface

#### web/index.html
- **Size**: 51 KB (self-contained single file)
- **Purpose**: Professional web-based control interface
- **Features**:
  - Real-time statistics dashboard
  - Network Operations Center (NOC) aesthetic
  - Interface status monitoring
  - Traffic profile management
  - Live charts and graphs
  - RFC2544 test controls
- **Technologies**: Pure HTML/CSS/JavaScript (no dependencies)
- **Design**: Industrial dark theme with animated backgrounds
- **Access**: http://<vep1445-ip>:5000

---

### ⚙️ Configuration Files

#### sample_config.json
- **Size**: 5.7 KB
- **Purpose**: Example configuration with 6 pre-configured traffic profiles
- **Includes**:
  - VoIP traffic (LAN1→LAN2)
  - Video streaming (LAN2→LAN3)
  - Bulk data (LAN3→LAN4)
  - MPLS traffic (LAN4→LAN5)
  - VXLAN overlay (LAN1→LAN5)
  - Q-in-Q provider traffic (LAN2→LAN4)
- **When to use**: Load as template, customize for your needs

#### requirements.txt
- **Size**: 44 bytes
- **Purpose**: Python dependencies for standard mode
- **Contents**:
  - Flask==3.0.0
  - flask-cors==4.0.0
  - scapy==2.5.0
- **Install**: `sudo pip3 install -r requirements.txt`

#### requirements_highperf.txt
- **Size**: 416 bytes
- **Purpose**: Python dependencies for high-performance mode
- **Additional packages**:
  - psutil (performance monitoring)
  - Notes for DPDK installation
- **Install**: `sudo pip3 install -r requirements_highperf.txt`

---

### 📦 Installation Scripts

#### install.sh
- **Size**: 5.8 KB
- **Purpose**: Automated installation script
- **Actions**:
  - Checks system requirements
  - Installs dependencies
  - Creates directories
  - Copies files to /opt/vep1445-traffic-gen
  - Installs systemd service
  - Configures network capabilities
- **Usage**: `sudo ./install.sh`

#### setup_performance.sh ⭐ **[CRITICAL FOR PERFORMANCE]**
- **Size**: 15 KB
- **Purpose**: Performance configuration automation
- **Features**:
  - Interactive mode selection
  - Kernel network tuning
  - CPU governor optimization
  - NIC optimization (ring buffers, offloads)
  - Interrupt affinity configuration
  - DPDK installation and setup
  - Hugepage configuration
  - CPU isolation setup
- **Modes**:
  - `--mode standard`: Minimal config
  - `--mode high`: Optimized for 500Mbps-2Gbps ⭐
  - `--mode dpdk`: DPDK setup for 2-10Gbps+
- **Usage**: `sudo ./setup_performance.sh --mode high`

#### start_vep1445.sh
- **Size**: 4.9 KB
- **Purpose**: Manual startup script with validation
- **Features**:
  - System checks (Python version, dependencies)
  - Interface validation
  - Network capability configuration
  - Logging setup
  - Process management
- **Usage**: `sudo ./start_vep1445.sh`

---

### 🔧 System Service

#### vep1445-traffic-gen.service
- **Size**: 845 bytes
- **Purpose**: Systemd service definition
- **Features**:
  - Automatic startup on boot
  - Resource limits
  - Network capabilities
  - Logging configuration
- **Install**: Copied to `/etc/systemd/system/` by install.sh
- **Usage**:
  ```bash
  sudo systemctl start vep1445-traffic-gen
  sudo systemctl enable vep1445-traffic-gen
  sudo systemctl status vep1445-traffic-gen
  ```

---

## Installation Paths

When installed, files are organized as follows:

```
/opt/vep1445-traffic-gen/          Main installation directory
├── traffic_engine_highperf.py
├── traffic_engine.py
├── web_api.py
├── setup_performance.sh
├── start_vep1445.sh
├── requirements_highperf.txt
├── sample_config.json
├── README_HIGHPERF.md
├── PERFORMANCE_GUIDE.md
└── web/
    └── index.html

/etc/systemd/system/
└── vep1445-traffic-gen.service    Systemd service

/var/log/vep1445/                  Log files
├── traffic-gen.log
└── traffic-gen-error.log

/home/claude/                      Runtime configuration
└── vep1445_runtime_config.json

/etc/sysctl.d/                     Kernel tuning
└── 99-vep1445-network.conf        (created by setup_performance.sh)
```

---

## Recommended Installation Order

### For Standard Deployment (<500Mbps):
1. **install.sh** - Install system
2. **QUICKSTART.md** - Follow guide
3. Start using web interface

### For High-Performance Deployment (500Mbps-2Gbps) ⭐ **[RECOMMENDED]**:
1. **README_HIGHPERF.md** - Read deployment guide
2. **install.sh** - Install system
3. **setup_performance.sh --mode high** - Configure performance
4. Verify with `ethtool -T eth1` (hardware timestamps)
5. Start using web interface

### For Ultra-Performance Deployment (2-10Gbps+):
1. **PERFORMANCE_GUIDE.md** - Read comprehensive guide
2. **install.sh** - Install system  
3. **setup_performance.sh --mode dpdk** - Configure DPDK
4. **Reboot** - Required for CPU isolation
5. **setup_dpdk.sh** - Initialize DPDK
6. Start with `--use-dpdk` flag

---

## File Dependencies

```
Execution Flow:
┌─────────────────────────────────────────────────────────┐
│  install.sh                                              │
│    ↓ Copies files to /opt/vep1445-traffic-gen          │
│    ↓ Installs requirements_highperf.txt                 │
│    ↓ Installs vep1445-traffic-gen.service              │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  setup_performance.sh --mode high                        │
│    ↓ Configures kernel (99-vep1445-network.conf)       │
│    ↓ Optimizes NICs                                      │
│    ↓ Sets CPU governor                                   │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  web_api.py (Flask server)                               │
│    ↓ Imports traffic_engine_highperf.py                 │
│    ↓ Serves web/index.html                              │
│    ↓ Provides REST API                                   │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  traffic_engine_highperf.py                              │
│    ↓ Manages network interfaces                          │
│    ↓ Generates high-performance traffic                  │
│    ↓ Applies hardware timestamps                         │
│    ↓ Handles impairments                                 │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Reference Table

| File | Size | Required | Purpose | When to Read |
|------|------|----------|---------|--------------|
| **README_HIGHPERF.md** | 11 KB | ⭐ Yes | Quick deployment | **Read first** |
| **PERFORMANCE_GUIDE.md** | 14 KB | Recommended | Deep tuning | Optimization |
| **README.md** | 17 KB | Recommended | Full docs | Feature reference |
| **QUICKSTART.md** | 7.4 KB | Optional | Fast start | New users |
| **traffic_engine_highperf.py** | 29 KB | ⭐ Yes | HW timestamps engine | Use for >100Mbps |
| **traffic_engine.py** | 36 KB | Optional | Standard engine | <500Mbps fallback |
| **web_api.py** | 17 KB | ⭐ Yes | API backend | Always |
| **web/index.html** | 51 KB | ⭐ Yes | Web GUI | Always |
| **install.sh** | 5.8 KB | ⭐ Yes | Installation | Run once |
| **setup_performance.sh** | 15 KB | ⭐ Yes | Performance config | Run once per mode |
| **start_vep1445.sh** | 4.9 KB | Optional | Manual start | Alternative to systemd |
| **requirements_highperf.txt** | 416 B | ⭐ Yes | Dependencies | Install once |
| **sample_config.json** | 5.7 KB | Optional | Examples | Reference |
| **vep1445-traffic-gen.service** | 845 B | Recommended | Systemd service | Auto-start |

---

## Total Package Size

- **Total files**: 15 files
- **Total size**: ~214 KB
- **Installation size**: ~300 MB (including Python dependencies)
- **With DPDK**: ~2 GB (including DPDK installation)

---

## Next Steps

1. **Download all files** to your VEP1445 system
2. **Read README_HIGHPERF.md** for deployment guide
3. **Run install.sh** to set up the system
4. **Run setup_performance.sh** to configure performance mode
5. **Access web interface** at http://<vep1445-ip>:5000
6. **Create traffic profiles** and start generating!

---

**All files are ready for deployment. Choose your performance mode and deploy!**
