<h1 align="center">🥷 MoMo-Shadow</h1>
<h3 align="center">Stealth WiFi Reconnaissance Device</h3>

<p align="center">
  <strong>Pocket-sized passive recon with e-Paper display</strong><br>
  <sub>Built for Red Teams • Pi Zero 2W + Waveshare 2.13" e-Paper</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-0.1.0-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Platform-Pi%20Zero%202W-c51a4a?style=for-the-badge&logo=raspberry-pi" alt="Platform">
  <img src="https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Status-Development-yellow?style=for-the-badge" alt="Status">
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-hardware">Hardware</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-operation-modes">Modes</a> •
  <a href="#-web-ui">Web UI</a> •
  <a href="#-ecosystem">Ecosystem</a>
</p>

---

> ⚠️ **DEVELOPMENT STATUS**: This project is under active development and has not been live-tested in the field. Use at your own risk.

---

## 🎯 What is MoMo-Shadow?

**MoMo-Shadow** is a pocket-sized, buttonless WiFi reconnaissance device designed for stealth operations. It combines a **Raspberry Pi Zero 2W** with a **Waveshare 2.13" e-Paper display** for ultra-low power consumption and outdoor readability.

### Why Shadow?

| Challenge | Shadow Solution |
|-----------|-----------------|
| 🔋 Limited battery life | ✅ e-Paper + low power = 48-72h runtime |
| 📱 No screen for feedback | ✅ e-Paper shows status, AP info, stats |
| 🎛️ Physical buttons required | ✅ WiFi AP + Web UI for full control |
| 🕵️ Visible devices suspicious | ✅ ~75x40x15mm, fits in palm |
| 💰 Expensive recon gear | ✅ ~$50 total hardware cost |

---

## ✨ Features

### 📡 Reconnaissance

```
Passive Scanning:
├── Access point discovery
├── Hidden SSID detection
├── Client MAC logging
├── Probe request capture
├── Signal strength mapping
└── BLE device detection (planned)

Capture:
├── WPA2/WPA3 handshake capture
├── PMKID capture
├── Targeted deauthentication
├── Auto-stop on success
└── Hashcat format export
```

### 🖥️ User Interface

```
e-Paper Display (250x122):
├── Current mode & status
├── AP/Client/Probe counts
├── Battery percentage
├── WiFi AP credentials
├── Target information
└── Capture progress

Web UI (Mobile-friendly):
├── Real-time statistics
├── Access point list
├── Target selection
├── Mode switching
├── Capture control
└── System management
```

### 🔋 Power Management

```
Battery Optimization:
├── e-Paper = near-zero idle draw
├── Configurable refresh rate
├── Drop mode (display off)
├── Low battery warnings
├── Auto-shutdown protection
└── 48-72h passive scanning
```

---

## 🔧 Hardware

### Required Components

| Component | Model | Price |
|-----------|-------|-------|
| **SBC** | Raspberry Pi Zero 2W | $15 |
| **Display** | Waveshare 2.13" e-Paper HAT | $20 |
| **Battery** | 2000mAh LiPo + charging board | $10 |
| **Storage** | MicroSD 16GB | $5 |
| **Total** | | **~$50** |

> 🎉 **No external WiFi adapter needed!** Installer automatically patches internal WiFi with Nexmon for monitor mode.

### Pinout (e-Paper HAT)

```
e-Paper 2.13" V4 Connection:
┌─────────────────────────────────────┐
│  VCC  ──── 3.3V (Pin 1)            │
│  GND  ──── GND  (Pin 6)            │
│  DIN  ──── MOSI (Pin 19, GPIO10)   │
│  CLK  ──── SCLK (Pin 23, GPIO11)   │
│  CS   ──── CE0  (Pin 24, GPIO8)    │
│  DC   ──── GPIO25 (Pin 22)         │
│  RST  ──── GPIO17 (Pin 11)         │
│  BUSY ──── GPIO24 (Pin 18)         │
└─────────────────────────────────────┘
```

### Assembly

```
┌─────────────────────────────────────────┐
│           PHYSICAL LAYOUT               │
├─────────────────────────────────────────┤
│                                         │
│    ┌─────────────────────────────┐     │
│    │                             │     │
│    │      e-Paper Display        │     │
│    │       (250 x 122)           │     │
│    │                             │     │
│    └─────────────────────────────┘     │
│                                         │
│    ┌─────────────────────────────┐     │
│    │     Pi Zero 2W + HAT        │     │
│    │    (Internal WiFi+Nexmon)   │     │
│    └─────────────────────────────┘     │
│                                         │
│    ┌───────────────────┐ ┌──────┐      │
│    │    LiPo Battery   │ │ USB  │      │
│    │     2000mAh       │ │Charge│      │
│    └───────────────────┘ └──────┘      │
│                                         │
└─────────────────────────────────────────┘

Dimensions: ~65 x 30 x 12mm (super compact!)
No external WiFi adapter needed!
```

---

## 🚀 Quick Start

### Option 1: Pre-Built Image (Recommended) ⭐

**Fastest way to get started - flash and go!**

1. **Download** from [Releases](https://github.com/M0M0Sec/MoMo-Shadow/releases/latest):
   ```
   momo-shadow-vX.X.X-pi-zero-2w.img.xz
   ```

2. **Flash** with [balenaEtcher](https://etcher.balena.io/):
   - Select downloaded `.img.xz`
   - Select your SD card
   - Click "Flash!"

3. **Boot** - Insert SD card, power on Pi Zero 2W

4. **Connect** to WiFi: `Shadow-Setup` (password: `shadowpass123`)

5. **Open** http://192.168.4.1 - You're ready! 🥷

> **Default SSH:** `pi` / `shadow123`

---

### Option 2: One-Line Install

If you prefer to install on existing Raspberry Pi OS:

```bash
# SSH into your Pi Zero 2W, then:
curl -fsSL https://raw.githubusercontent.com/M0M0Sec/MoMo-Shadow/main/deploy/install.sh | sudo bash
```

**The script automatically:**
- ✅ Installs all dependencies
- ✅ Installs Nexmon (monitor mode for internal WiFi)
- ✅ Installs MoMo-Shadow
- ✅ Configures systemd service
- ✅ Enables SPI for e-Paper

After reboot, Shadow starts automatically.

---

### Option 3: Manual Install

```bash
# Clone repository
git clone https://github.com/M0M0Sec/MoMo-Shadow.git /opt/shadow
cd /opt/shadow

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install
pip install -e .

# Configure
sudo mkdir -p /etc/momo-shadow
sudo cp config/shadow.example.yml /etc/momo-shadow/config.yml

# Run
shadow run

# Boot and connect!
```

---

### Option 3: Manual Install

<details>
<summary>Click to expand manual installation steps</summary>

```bash
# 1. Flash Raspberry Pi OS Lite (64-bit)
# 2. Enable SSH: touch /boot/ssh
# 3. Boot and SSH into Pi

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y git python3-pip python3-venv python3-dev \
    hostapd dnsmasq aircrack-ng hcxtools iw wireless-tools \
    build-essential libgmp3-dev gawk raspberrypi-kernel-headers

# Install Nexmon (for monitor mode)
cd /opt
sudo git clone https://github.com/seemoo-lab/nexmon.git
cd nexmon
source setup_env.sh
# ... (follow Nexmon build instructions for bcm43436s)

# Install MoMo-Shadow
cd /opt
sudo git clone https://github.com/M0M0Sec/MoMo-Shadow.git shadow
cd shadow
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Configure
sudo mkdir -p /etc/momo-shadow /var/momo-shadow/data /var/momo-shadow/captures
sudo cp config/shadow.example.yml /etc/momo-shadow/config.yml

# Install service
sudo cp deploy/shadow.service /etc/systemd/system/
sudo systemctl enable shadow
sudo reboot
```

</details>

### 5. Connect & Use

```
Boot Sequence:
┌─────────────────────────────────────────────────────┐
│  1. BOOT (10s)                                      │
│     └─► System starting...                          │
│                                                      │
│  2. SETUP MODE (60s) ─────────────────────────────┐│
│     └─► WiFi AP: Shadow-XXXX                      ││
│     └─► Connect & open http://192.168.4.1         ││
│     └─► Configure targets, start scan             ││
│                                                    ││
│  3. AUTO-SWITCH ◄─────────────────────────────────┘│
│     └─► AP stops, Monitor mode starts              │
│     └─► Scanning begins automatically              │
│                                                      │
│  4. SCANNING (autonomous)                           │
│     └─► Reboot to return to Setup mode             │
└─────────────────────────────────────────────────────┘
```

**Quick Connect:**
1. Connect to WiFi: `Shadow-XXXX`
2. Password: `shadowpass123`
3. Open: `http://192.168.4.1`
4. Click "Start Scanning" or wait 60s for auto-start

---

## 🎮 Operation Modes

### Passive Mode (Default)

```yaml
# Config
autostart:
  mode: passive

# Behavior
- Listen only, no packets transmitted
- Log all APs, clients, probes
- Maximum stealth
- Battery: 48-72 hours
```

### Capture Mode

```yaml
# Config
autostart:
  mode: capture
targets:
  ssids:
    - "Target-Network"

# Behavior
- Select target AP
- Send targeted deauth
- Capture handshake
- Auto-stop on success
- Battery: 12-24 hours
```

### Drop Mode

```yaml
# Config
autostart:
  mode: drop

# Behavior
- Display off (max power save)
- Silent background logging
- Retrieve data via SD card
- Battery: 72+ hours
```

---

## 🌐 Web UI

The web interface provides full control without physical buttons.

### Screenshots

```
┌────────────────────────────────────┐
│  🥷 MoMo-Shadow     [SCANNING] 🔋85%│
├────────────────────────────────────┤
│                                    │
│  📊 Statistics                     │
│  ┌────────┐ ┌────────┐            │
│  │   12   │ │   24   │            │
│  │  APs   │ │Clients │            │
│  └────────┘ └────────┘            │
│  ┌────────┐ ┌────────┐            │
│  │   156  │ │   2    │            │
│  │ Probes │ │  HS    │            │
│  └────────┘ └────────┘            │
│                                    │
│  📶 Access Points                  │
│  ├── Corp-WiFi      -45dBm  WPA2  │
│  ├── Guest-Net      -52dBm  OPEN  │
│  └── IoT-Devices    -68dBm  WPA2  │
│                                    │
│  🎯 Capture                        │
│  [Passive] [Capture] [Drop]        │
│  Target: None selected             │
│  [▶ Start Capture]                 │
│                                    │
└────────────────────────────────────┘
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | System status |
| GET | `/api/aps` | Access points |
| GET | `/api/clients` | Clients |
| GET | `/api/probes` | Probe requests |
| GET | `/api/handshakes` | Captured handshakes |
| POST | `/api/mode` | Change mode |
| POST | `/api/target` | Set target |
| POST | `/api/capture/start` | Start capture |
| POST | `/api/deauth` | Send deauth |
| POST | `/api/shutdown` | Shutdown device |

---

## 📊 e-Paper Display

### Screen Layout

```
┌──────────────────────────────────────────────┐
│ SHADOW                              🔋 85%   │  <- Header (18px)
├──────────────────────────────────────────────┤
│                                              │
│  MODE: SCANNING                              │  <- Mode
│                                              │
│  APs: 12       Clients: 24                   │  <- Stats
│  Probes: 156   HS: 2                         │
│                                              │
│  WiFi AP: Shadow-A3F2                        │  <- AP Info
│  Pass: shadowpass123                         │
│                                              │
│  ─────────────────────────────               │
│  Connect to WiFi AP                          │  <- Instructions
│  Open http://192.168.4.1                     │
│                                              │
│  Up: 2h 34m                                  │  <- Uptime
└──────────────────────────────────────────────┘
        250px × 122px (2.13" diagonal)
```

---

## 📁 Project Structure

```
MoMo-Shadow/
├── src/shadow/
│   ├── __init__.py           # Package init
│   ├── main.py               # Main orchestrator
│   ├── config.py             # Pydantic config
│   ├── cli.py                # Typer CLI
│   │
│   ├── core/                 # Core functionality
│   │   ├── scanner.py        # WiFi scanner
│   │   ├── capture.py        # Handshake capture
│   │   ├── deauth.py         # Deauth attacks
│   │   └── hopper.py         # Channel hopping
│   │
│   ├── ui/                   # User interface
│   │   └── epaper.py         # e-Paper driver
│   │
│   ├── web/                  # Web UI
│   │   └── server.py         # FastAPI server
│   │
│   ├── network/              # Network management
│   │   ├── ap.py             # WiFi AP (hostapd)
│   │   ├── manager.py        # Interface manager
│   │   └── nexmon.py         # Nexmon monitor mode
│   │
│   ├── storage/              # Data persistence
│   │   ├── database.py       # SQLite storage
│   │   └── export.py         # Hashcat export
│   │
│   └── hardware/             # Hardware drivers
│       ├── battery.py        # Battery monitor
│       └── power.py          # Power management
│
├── config/
│   └── shadow.example.yml    # Example config
│
├── deploy/
│   ├── install.sh            # One-line installer (Nexmon + Shadow)
│   ├── shadow.service        # Systemd service
│   └── image/                # SD card image builder
│
├── tests/                    # Test suite
├── docs/                     # Documentation
├── pyproject.toml            # Project config
└── README.md                 # This file
```

---

## 🌐 MoMo Ecosystem

MoMo-Shadow is part of the MoMo offensive security ecosystem.

```
                         ☁️ CLOUD/VPS
              ┌─────────────────────────────┐
              │  GPU Cracking │ WireGuard   │
              └───────────────┬─────────────┘
                              │
               ┌──────────────▼──────────────┐
               │         MoMo-NEXUS          │
               │      Central C2 Hub         │
               └──────────────┬──────────────┘
                              │
      ┌───────────────────────┼───────────────────────┐
      │                       │                       │
┌─────▼─────┐          ┌──────▼──────┐         ┌─────▼─────┐
│   MoMo    │          │GhostBridge  │         │  Shadow   │ ← You are here
│  WiFi/BLE │          │ Net Implant │         │  Recon    │
│   Pi 5    │          │   NanoPi    │         │  Pi Zero  │
└───────────┘          └─────────────┘         └───────────┘
```

### Ecosystem Projects

| Project | Description | Platform |
|---------|-------------|----------|
| **🔵 MoMo** | Full WiFi/BLE/SDR platform | Raspberry Pi 5 |
| **🟢 Nexus** | Central C2 hub | Raspberry Pi 4 |
| **👻 GhostBridge** | Network implant | NanoPi R2S |
| **🎭 Mimic** | USB attack platform | Pi Zero 2W |
| **🥷 Shadow** | Stealth recon (this project) | Pi Zero 2W |

---

## 🔧 CLI Reference

```bash
# Start Shadow
shadow run [--config PATH] [--mode MODE] [--debug]

# Show status
shadow status

# Manage config
shadow config --show
shadow config --create /path/to/config.yml

# List interfaces
shadow interfaces

# Export captures
shadow export capture.pcap [--output /path/to/output]

# Version info
shadow version

# Web UI only
shadow web [--host 0.0.0.0] [--port 80]
```

---

## ⚠️ Legal Disclaimer

> **MoMo-Shadow is designed for authorized security testing and educational purposes only.**

- ✅ Only use on networks you own or have explicit written permission to test
- ✅ Respect local laws regarding wireless security testing
- ✅ Follow responsible disclosure practices
- ❌ Unauthorized access to computer systems is illegal
- ❌ The developers are not responsible for misuse

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Part of the 🔥 MoMo Ecosystem</strong><br>
  <sub>Stealth • Portable • Low Power</sub>
</p>

<p align="center">
  <a href="https://github.com/M0M0Sec/MoMo">🔵 MoMo</a> •
  <a href="https://github.com/M0M0Sec/MoMo-Nexus">🟢 Nexus</a> •
  <a href="https://github.com/M0M0Sec/Momo-GhostBridge">👻 GhostBridge</a> •
  <a href="https://github.com/M0M0Sec/MoMo-Mimic">🎭 Mimic</a> •
  <a href="https://github.com/M0M0Sec/MoMo-Shadow">🥷 Shadow</a>
</p>

<p align="center">
  <sub>Made with ❤️ by the MoMo Team</sub>
</p>

