# VEP1445 Installation Quick Reference

## 🚀 All-In-One Installation (EASIEST)

### One-Command Install

```bash
chmod +x install_allinone.sh
./install_allinone.sh
```

That's it! The installer will:
1. Ask where to install (User Home vs System Directory)
2. Copy all files
3. Install dependencies
4. Create startup scripts
5. Configure permissions
6. Optionally configure performance

---

## 📍 Installation Location Options

### Option 1: User Home Directory (RECOMMENDED for Testing/Dev)

**Location**: `~/vep1445-traffic-gen`

**Advantages**:
- ✅ No sudo needed for installation
- ✅ Easy to update and modify files
- ✅ Your user owns all files
- ✅ Desktop shortcut created automatically
- ✅ Easy to remove (`rm -rf ~/vep1445-traffic-gen`)

**When to use sudo**:
- Only for first-time raw socket capability grant
- Only for performance configuration
- After that, runs without sudo!

**Start command**:
```bash
cd ~/vep1445-traffic-gen
./start.sh
```

**File permissions**: All owned by your user

---

### Option 2: System Directory (RECOMMENDED for Production)

**Location**: `/opt/vep1445-traffic-gen`

**Advantages**:
- ✅ Systemd service integration
- ✅ Auto-start on boot
- ✅ Multi-user access
- ✅ Standard Linux service location
- ✅ Proper logging to /var/log

**Requires sudo**:
- For installation
- For running (needs raw socket access)
- Standard for system services

**Start command**:
```bash
sudo systemctl start vep1445
```

**File permissions**: Owned by root

---

## 🎯 Comparison Chart

| Feature | User Home (~/) | System (/opt) |
|---------|---------------|---------------|
| **Location** | ~/vep1445-traffic-gen | /opt/vep1445-traffic-gen |
| **Install sudo?** | No ❌ | Yes ✓ |
| **Run sudo?** | Once, then no* | Yes ✓ |
| **Systemd service** | No ❌ | Yes ✓ |
| **Auto-start** | No ❌ | Yes ✓ |
| **Easy updates** | Yes ✓ | Requires sudo |
| **Desktop shortcut** | Yes ✓ | No ❌ |
| **Multi-user** | No ❌ | Yes ✓ |
| **File ownership** | Your user | root |
| **Logs** | ~/vep1445-traffic-gen/logs | /var/log/vep1445 |
| **Best for** | Dev/Testing | Production |

\* After one-time capability grant

---

## 📋 Step-by-Step: User Home Installation

### 1. Download/Extract Files
```bash
cd ~/Downloads/vep1445-files
```

### 2. Run All-In-One Installer
```bash
chmod +x install_allinone.sh
./install_allinone.sh
```

### 3. Choose Option 1 (User Home)
```
Enter choice [1-2]: 1
```

### 4. First Start (needs sudo once)
```bash
cd ~/vep1445-traffic-gen
./start.sh
# Will prompt for sudo to grant capabilities
```

### 5. Subsequent Starts (no sudo!)
```bash
cd ~/vep1445-traffic-gen
./start.sh
# Runs without sudo now!
```

### 6. Access Web Interface
```
http://localhost:5000
```

---

## 📋 Step-by-Step: System Installation

### 1. Download/Extract Files
```bash
cd ~/Downloads/vep1445-files
```

### 2. Run All-In-One Installer with Sudo
```bash
chmod +x install_allinone.sh
sudo ./install_allinone.sh
```

### 3. Choose Option 2 (System)
```
Enter choice [1-2]: 2
```

### 4. Enable Systemd Service
```bash
sudo systemctl enable vep1445
```

### 5. Start Service
```bash
sudo systemctl start vep1445
```

### 6. Check Status
```bash
sudo systemctl status vep1445
```

### 7. Access Web Interface
```
http://localhost:5000
```

---

## 🛠️ What Gets Installed Where

### User Home Mode (`~/vep1445-traffic-gen`)

```
~/vep1445-traffic-gen/
├── traffic_engine_unified.py      ← Main engine
├── web_api.py                      ← API server
├── web/
│   └── index.html                  ← Web GUI
├── config/
│   └── sample_config.json          ← Example config
├── scripts/
│   └── setup_performance.sh        ← Performance config
├── logs/                            ← Log files
│   └── vep1445.log
├── start.sh                         ← Start script ⭐
├── stop.sh                          ← Stop script
├── status.sh                        ← Status check
├── DEPLOYMENT_UNIFIED.md            ← Main guide
├── README_HIGHPERF.md
├── PERFORMANCE_GUIDE.md
└── (other docs)

~/Desktop/
└── VEP1445.desktop                  ← Desktop shortcut

~/.local/
└── (Python packages)                ← Dependencies
```

### System Mode (`/opt/vep1445-traffic-gen`)

```
/opt/vep1445-traffic-gen/
├── (same structure as user mode)
└── (files owned by root)

/var/log/vep1445/
├── vep1445.log                      ← Main log
└── vep1445-error.log                ← Error log

/etc/systemd/system/
└── vep1445.service                  ← Systemd service

/usr/local/lib/
└── (Python packages)                ← Dependencies
```

---

## 💡 Sudo Requirements Explained

### User Home Mode

**Sudo needed for**:
1. **First-time capability grant** (one-time only)
   ```bash
   sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/python3
   ```
   This allows Python to create raw sockets without sudo

2. **Performance configuration** (optional)
   ```bash
   sudo ./scripts/setup_performance.sh --mode high
   ```
   Changes kernel settings, NIC parameters

**After that**: No sudo needed! ✓

### System Mode

**Sudo needed for**:
1. **Installation** (one-time)
2. **Running service** (always - standard for network services)
3. **Viewing logs** (optional - logs in /var/log)

This is normal for system services.

---

## 🎮 Quick Commands Reference

### User Home Mode

```bash
# Start
cd ~/vep1445-traffic-gen && ./start.sh

# Stop  
cd ~/vep1445-traffic-gen && ./stop.sh

# Status
cd ~/vep1445-traffic-gen && ./status.sh

# View logs
tail -f ~/vep1445-traffic-gen/logs/vep1445.log

# Access from anywhere (add to ~/.bashrc)
alias vep1445-start='cd ~/vep1445-traffic-gen && ./start.sh'
alias vep1445-stop='cd ~/vep1445-traffic-gen && ./stop.sh'
alias vep1445-status='cd ~/vep1445-traffic-gen && ./status.sh'
```

### System Mode

```bash
# Start
sudo systemctl start vep1445

# Stop
sudo systemctl stop vep1445

# Restart
sudo systemctl restart vep1445

# Status
sudo systemctl status vep1445

# Enable auto-start
sudo systemctl enable vep1445

# Disable auto-start
sudo systemctl disable vep1445

# View logs (live)
sudo journalctl -u vep1445 -f

# View logs (last 100 lines)
sudo journalctl -u vep1445 -n 100
```

---

## 🔄 Switching Modes

### From User → System

```bash
# 1. Stop user mode
cd ~/vep1445-traffic-gen
./stop.sh

# 2. Run installer again, choose System mode
cd ~/Downloads/vep1445-files
sudo ./install_allinone.sh
# Choose option 2

# 3. Remove user installation (optional)
rm -rf ~/vep1445-traffic-gen
```

### From System → User

```bash
# 1. Stop and disable system service
sudo systemctl stop vep1445
sudo systemctl disable vep1445

# 2. Run installer again, choose User mode
cd ~/Downloads/vep1445-files
./install_allinone.sh
# Choose option 1

# 3. Remove system installation (optional)
sudo rm -rf /opt/vep1445-traffic-gen
sudo rm /etc/systemd/system/vep1445.service
```

---

## 📱 Desktop Integration (User Mode Only)

A desktop shortcut is created automatically in user mode:

**Location**: `~/Desktop/VEP1445.desktop`

**Double-click to**:
- Open terminal
- Start VEP1445
- See real-time logs

**To remove**:
```bash
rm ~/Desktop/VEP1445.desktop
```

---

## 🐛 Troubleshooting

### "Permission denied" when accessing raw sockets

**User Mode**:
```bash
# Grant capability (one-time)
sudo setcap cap_net_raw,cap_net_admin=eip $(which python3)
```

**System Mode**:
```bash
# Run with sudo (normal)
sudo systemctl start vep1445
```

### Can't find installation directory

**Check where you installed**:
```bash
# User mode
ls ~/vep1445-traffic-gen

# System mode
ls /opt/vep1445-traffic-gen
```

### Web interface won't start

**Check if already running**:
```bash
# User mode
./status.sh

# System mode
sudo systemctl status vep1445
```

**Check port 5000 is free**:
```bash
sudo netstat -tlnp | grep 5000
```

### Need to update files

**User Mode** (easy!):
```bash
cd ~/vep1445-traffic-gen
# Just copy new files over
cp ~/Downloads/new-file.py .
```

**System Mode**:
```bash
# Need sudo
sudo cp ~/Downloads/new-file.py /opt/vep1445-traffic-gen/
sudo systemctl restart vep1445
```

---

## 💾 Backup and Removal

### Backup Configuration

**User Mode**:
```bash
tar czf vep1445-backup.tar.gz ~/vep1445-traffic-gen
```

**System Mode**:
```bash
sudo tar czf vep1445-backup.tar.gz /opt/vep1445-traffic-gen
```

### Complete Removal

**User Mode**:
```bash
cd ~/vep1445-traffic-gen
./stop.sh
cd ~
rm -rf ~/vep1445-traffic-gen
rm ~/Desktop/VEP1445.desktop
```

**System Mode**:
```bash
sudo systemctl stop vep1445
sudo systemctl disable vep1445
sudo rm -rf /opt/vep1445-traffic-gen
sudo rm /etc/systemd/system/vep1445.service
sudo rm -rf /var/log/vep1445
sudo systemctl daemon-reload
```

---

## ✅ Recommendation

**For most users**: Start with **User Home** mode
- Easy to set up
- Easy to modify
- Easy to remove
- Minimal sudo usage
- Perfect for development and testing

**Upgrade to System mode when**:
- Moving to production
- Need auto-start on boot
- Multiple users need access
- Want systemd integration

---

## 🎯 Summary

| Your Situation | Recommended Mode | Install Command |
|----------------|------------------|-----------------|
| Testing VEP1445 | User Home | `./install_allinone.sh` → Option 1 |
| Development | User Home | `./install_allinone.sh` → Option 1 |
| Production, single user | User Home | `./install_allinone.sh` → Option 1 |
| Production, multi-user | System | `sudo ./install_allinone.sh` → Option 2 |
| Need auto-start | System | `sudo ./install_allinone.sh` → Option 2 |
| Prefer systemd | System | `sudo ./install_allinone.sh` → Option 2 |

**Both modes are fully functional** - choose based on your preference!

---

**Quick Start**: `./install_allinone.sh` and follow the prompts!
