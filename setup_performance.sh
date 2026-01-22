#!/bin/bash

# VEP1445 Performance Configuration Script
# Automatically configure system for high-performance packet processing

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║   VEP1445 High-Performance Configuration                      ║"
echo "║   Optimizing for 100Mbps - 10Gbps Traffic Generation         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root${NC}"
    exit 1
fi

PERFORMANCE_MODE=""
USE_DPDK=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            PERFORMANCE_MODE="$2"
            shift 2
            ;;
        --dpdk)
            USE_DPDK=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Interactive mode selection if not specified
if [ -z "$PERFORMANCE_MODE" ]; then
    echo -e "${CYAN}Select Performance Mode:${NC}"
    echo "  1) Standard (100-500 Mbps)"
    echo "  2) High-Performance (500Mbps-2Gbps) [Recommended]"
    echo "  3) Ultra-Performance/DPDK (2Gbps-10Gbps+)"
    read -p "Enter choice [1-3]: " choice
    
    case $choice in
        1) PERFORMANCE_MODE="standard" ;;
        2) PERFORMANCE_MODE="high" ;;
        3) PERFORMANCE_MODE="dpdk"; USE_DPDK=true ;;
        *) echo "Invalid choice"; exit 1 ;;
    esac
fi

echo -e "\n${GREEN}Configuring for: $PERFORMANCE_MODE mode${NC}\n"

# ============================================================================
# STANDARD MODE
# ============================================================================

if [ "$PERFORMANCE_MODE" == "standard" ]; then
    echo -e "${CYAN}[Standard Mode] Minimal configuration${NC}"
    
    # Just ensure interfaces are up
    for i in {1..5}; do
        if ip link show eth$i &>/dev/null; then
            ip link set eth$i up
            echo "  ✓ eth$i up"
        fi
    done
    
    echo -e "${GREEN}Standard mode configured${NC}"
    exit 0
fi

# ============================================================================
# HIGH-PERFORMANCE MODE
# ============================================================================

if [ "$PERFORMANCE_MODE" == "high" ]; then
    echo -e "${CYAN}[1/6] Configuring kernel network parameters...${NC}"
    
    cat > /etc/sysctl.d/99-vep1445-network.conf << 'EOF'
# VEP1445 High-Performance Network Configuration

# Increase network buffers
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.core.rmem_default = 16777216
net.core.wmem_default = 16777216

# TCP buffers
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728

# Increase netdev backlog
net.core.netdev_max_backlog = 300000
net.core.netdev_budget = 600

# Disable TCP timestamps for performance
net.ipv4.tcp_timestamps = 0

# Enable window scaling
net.ipv4.tcp_window_scaling = 1

# Increase local port range
net.ipv4.ip_local_port_range = 1024 65535

# Optimize for throughput
net.ipv4.tcp_congestion_control = htcp
net.ipv4.tcp_mtu_probing = 1
EOF

    sysctl -p /etc/sysctl.d/99-vep1445-network.conf > /dev/null
    echo -e "${GREEN}  ✓ Kernel parameters configured${NC}"
    
    echo -e "\n${CYAN}[2/6] Setting CPU governor to performance...${NC}"
    
    apt-get install -y -qq cpufrequtils linux-tools-common > /dev/null 2>&1 || true
    
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        if [ -f "$cpu" ]; then
            echo performance > $cpu
        fi
    done
    echo -e "${GREEN}  ✓ CPU governor set to performance${NC}"
    
    echo -e "\n${CYAN}[3/6] Optimizing network interfaces...${NC}"
    
    for i in {1..5}; do
        if ip link show eth$i &>/dev/null; then
            # Bring up interface
            ip link set eth$i up
            
            # Disable interrupt coalescing for low latency
            ethtool -C eth$i rx-usecs 0 tx-usecs 0 2>/dev/null || true
            
            # Increase ring buffers
            ethtool -G eth$i rx 4096 tx 4096 2>/dev/null || true
            
            # Enable hardware offloads
            ethtool -K eth$i gso on tso on gro on 2>/dev/null || true
            
            # Check for hardware timestamp support
            if ethtool -T eth$i 2>/dev/null | grep -q "hardware-transmit"; then
                echo -e "  ✓ eth$i optimized ${GREEN}[HW timestamps available]${NC}"
            else
                echo -e "  ✓ eth$i optimized ${YELLOW}[SW timestamps only]${NC}"
            fi
        fi
    done
    
    echo -e "\n${CYAN}[4/6] Configuring interrupt affinity...${NC}"
    
    for i in {1..5}; do
        if ip link show eth$i &>/dev/null; then
            IRQ=$(cat /proc/interrupts | grep eth$i | awk '{print $1}' | tr -d ':' | head -1)
            if [ ! -z "$IRQ" ]; then
                # Bind to specific CPU (round-robin across available CPUs)
                CPU=$((i % $(nproc)))
                MASK=$((1 << CPU))
                echo $MASK > /proc/irq/$IRQ/smp_affinity 2>/dev/null || true
                echo "  ✓ eth$i IRQ $IRQ -> CPU $CPU"
            fi
        fi
    done
    
    echo -e "\n${CYAN}[5/6] Disabling power management features...${NC}"
    
    # Disable CPU idle states
    cpupower idle-set -D 0 2>/dev/null || true
    
    # Disable Intel P-state turbo
    if [ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]; then
        echo 1 > /sys/devices/system/cpu/intel_pstate/no_turbo
    fi
    
    echo -e "${GREEN}  ✓ Power management optimized${NC}"
    
    echo -e "\n${CYAN}[6/6] Creating performance monitoring script...${NC}"
    
    cat > /usr/local/bin/vep1445-perf-monitor << 'EOF'
#!/bin/bash
# VEP1445 Performance Monitor

echo "VEP1445 Performance Metrics"
echo "============================"
echo ""

for i in {1..5}; do
    if ip link show eth$i &>/dev/null; then
        echo "Interface: eth$i"
        ethtool -S eth$i | grep -E 'packets|bytes' | head -6
        echo ""
    fi
done

echo "CPU Usage:"
mpstat -P ALL 1 1 | grep Average | head -6

echo ""
echo "Network Buffer Usage:"
ss -m | grep -A 1 -E 'ESTAB|LISTEN' | head -10
EOF

    chmod +x /usr/local/bin/vep1445-perf-monitor
    
    echo -e "${GREEN}  ✓ Monitor script created: /usr/local/bin/vep1445-perf-monitor${NC}"
    
    echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════════╗"
    echo "║  High-Performance Mode Configured Successfully!               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Expected Performance: 500Mbps - 2Gbps"
    echo ""
    echo "Monitor performance: vep1445-perf-monitor"
    echo ""
    
    exit 0
fi

# ============================================================================
# DPDK MODE
# ============================================================================

if [ "$PERFORMANCE_MODE" == "dpdk" ] || [ "$USE_DPDK" = true ]; then
    echo -e "${CYAN}[DPDK Mode] Setting up ultra-high-performance configuration${NC}"
    echo ""
    
    # First, apply all high-performance settings
    echo -e "${CYAN}[1/10] Applying high-performance base configuration...${NC}"
    $0 --mode high
    
    echo -e "\n${CYAN}[2/10] Checking DPDK prerequisites...${NC}"
    
    # Check IOMMU support
    if dmesg | grep -q "IOMMU enabled"; then
        echo -e "${GREEN}  ✓ IOMMU enabled${NC}"
    else
        echo -e "${YELLOW}  ⚠ IOMMU not detected - may need BIOS configuration${NC}"
        echo "    Add 'intel_iommu=on' (Intel) or 'amd_iommu=on' (AMD) to kernel parameters"
    fi
    
    # Check hugepage support
    if grep -q "pse" /proc/cpuinfo; then
        echo -e "${GREEN}  ✓ Hugepage support detected${NC}"
    else
        echo -e "${RED}  ✗ Hugepage support not found${NC}"
        exit 1
    fi
    
    echo -e "\n${CYAN}[3/10] Installing DPDK dependencies...${NC}"
    
    apt-get update -qq
    apt-get install -y -qq build-essential libnuma-dev python3-pip \
        python3-pyelftools pkg-config meson ninja-build \
        libpcap-dev > /dev/null 2>&1
    
    echo -e "${GREEN}  ✓ Dependencies installed${NC}"
    
    echo -e "\n${CYAN}[4/10] Configuring hugepages (2GB = 1024 x 2MB pages)...${NC}"
    
    # Configure hugepages
    echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
    
    # Make persistent
    if ! grep -q "vm.nr_hugepages" /etc/sysctl.conf; then
        echo "vm.nr_hugepages=1024" >> /etc/sysctl.conf
    fi
    
    # Mount hugepages
    mkdir -p /mnt/huge
    if ! mount | grep -q "/mnt/huge"; then
        mount -t hugetlbfs nodev /mnt/huge
    fi
    
    # Make persistent
    if ! grep -q "/mnt/huge" /etc/fstab; then
        echo "nodev /mnt/huge hugetlbfs defaults 0 0" >> /etc/fstab
    fi
    
    HUGE_AVAIL=$(cat /proc/meminfo | grep HugePages_Free | awk '{print $2}')
    echo -e "${GREEN}  ✓ Hugepages configured: $HUGE_AVAIL available${NC}"
    
    echo -e "\n${CYAN}[5/10] Configuring CPU isolation...${NC}"
    
    # Determine CPU count and isolate half for DPDK
    NUM_CPUS=$(nproc)
    if [ $NUM_CPUS -ge 4 ]; then
        ISOLATE_START=$((NUM_CPUS / 2))
        ISOLATE_END=$((NUM_CPUS - 1))
        ISOLATE_CPUS="${ISOLATE_START}-${ISOLATE_END}"
        
        # Update GRUB
        if ! grep -q "isolcpus=" /etc/default/grub; then
            sed -i "s/GRUB_CMDLINE_LINUX=\"/GRUB_CMDLINE_LINUX=\"isolcpus=$ISOLATE_CPUS nohz_full=$ISOLATE_CPUS rcu_nocbs=$ISOLATE_CPUS /" /etc/default/grub
            update-grub
            
            echo -e "${YELLOW}  ⚠ CPU isolation requires reboot to take effect${NC}"
            echo "    Isolated CPUs: $ISOLATE_CPUS"
        else
            echo -e "${GREEN}  ✓ CPU isolation already configured${NC}"
        fi
    else
        echo -e "${YELLOW}  ⚠ Not enough CPUs for isolation (need 4+, have $NUM_CPUS)${NC}"
    fi
    
    echo -e "\n${CYAN}[6/10] Downloading and building DPDK...${NC}"
    
    DPDK_VERSION="23.11"
    DPDK_DIR="/opt/dpdk-${DPDK_VERSION}"
    
    if [ ! -d "$DPDK_DIR" ]; then
        cd /opt
        if [ ! -f "dpdk-${DPDK_VERSION}.tar.xz" ]; then
            echo "  Downloading DPDK ${DPDK_VERSION}..."
            wget -q https://fast.dpdk.org/rel/dpdk-${DPDK_VERSION}.tar.xz
        fi
        
        echo "  Extracting..."
        tar xf dpdk-${DPDK_VERSION}.tar.xz
        
        cd $DPDK_DIR
        echo "  Building DPDK (this may take several minutes)..."
        meson build > /dev/null 2>&1
        cd build
        ninja > /dev/null 2>&1
        ninja install > /dev/null 2>&1
        ldconfig
        
        echo -e "${GREEN}  ✓ DPDK ${DPDK_VERSION} built and installed${NC}"
    else
        echo -e "${GREEN}  ✓ DPDK already installed at $DPDK_DIR${NC}"
    fi
    
    echo -e "\n${CYAN}[7/10] Loading DPDK kernel modules...${NC}"
    
    modprobe uio
    modprobe vfio-pci
    
    echo -e "${GREEN}  ✓ Kernel modules loaded${NC}"
    
    echo -e "\n${CYAN}[8/10] Scanning for DPDK-capable NICs...${NC}"
    
    cd $DPDK_DIR
    
    echo ""
    ./usertools/dpdk-devbind.py --status-dev net
    echo ""
    
    echo -e "${YELLOW}To bind interfaces to DPDK:${NC}"
    echo "  1. Find PCI address above (e.g., 0000:02:00.0)"
    echo "  2. Run: $DPDK_DIR/usertools/dpdk-devbind.py --bind=vfio-pci <PCI_ADDR>"
    echo "  3. Repeat for all interfaces"
    echo ""
    
    read -p "Automatically bind eth1-eth5 to DPDK? [y/N]: " bind_auto
    
    if [[ "$bind_auto" =~ ^[Yy]$ ]]; then
        for i in {1..5}; do
            if ip link show eth$i &>/dev/null; then
                PCI=$(basename $(readlink /sys/class/net/eth$i/device))
                echo "  Binding eth$i ($PCI) to DPDK..."
                ./usertools/dpdk-devbind.py --bind=vfio-pci $PCI
            fi
        done
        echo -e "${GREEN}  ✓ Interfaces bound to DPDK${NC}"
    fi
    
    echo -e "\n${CYAN}[9/10] Creating DPDK startup script...${NC}"
    
    cat > /opt/vep1445-traffic-gen/setup_dpdk.sh << 'EOF'
#!/bin/bash
# VEP1445 DPDK Startup Script

# Load modules
modprobe uio
modprobe vfio-pci

# Setup hugepages
echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
mount -t hugetlbfs nodev /mnt/huge 2>/dev/null || true

# Bind interfaces (customize PCI addresses as needed)
# Example:
# /opt/dpdk-23.11/usertools/dpdk-devbind.py --bind=vfio-pci 0000:02:00.0

echo "DPDK environment ready"
EOF

    chmod +x /opt/vep1445-traffic-gen/setup_dpdk.sh
    
    echo -e "${GREEN}  ✓ DPDK startup script created${NC}"
    
    echo -e "\n${CYAN}[10/10] Creating DPDK configuration file...${NC}"
    
    cat > /opt/vep1445-traffic-gen/dpdk.conf << EOF
# VEP1445 DPDK Configuration

# EAL Options
-l 2-5                      # Use CPU cores 2-5
-n 4                        # Memory channels
--socket-mem=2048,2048      # Memory per NUMA node (MB)
--proc-type=primary
--file-prefix=vep1445
--log-level=8
EOF

    echo -e "${GREEN}  ✓ DPDK configuration created${NC}"
    
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗"
    echo "║  DPDK Mode Configured Successfully!                           ║"
    echo "╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Expected Performance: 2Gbps - 10Gbps+"
    echo ""
    echo -e "${YELLOW}IMPORTANT NEXT STEPS:${NC}"
    echo ""
    echo "1. Reboot system to apply CPU isolation"
    echo "2. After reboot, run: /opt/vep1445-traffic-gen/setup_dpdk.sh"
    echo "3. Bind interfaces to DPDK"
    echo "4. Start VEP1445 with: python3 web_api.py --use-dpdk"
    echo ""
    echo "Verify DPDK status:"
    echo "  $DPDK_DIR/usertools/dpdk-devbind.py --status"
    echo ""
    
    exit 0
fi

echo -e "${RED}Invalid performance mode: $PERFORMANCE_MODE${NC}"
exit 1
