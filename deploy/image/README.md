# 📀 MoMo-Shadow SD Card Image

## Pre-Built Images

Download the latest pre-built image from [Releases](https://github.com/M0M0Sec/MoMo-Shadow/releases).

### Quick Start

1. **Download** the `.img.xz` file from releases
2. **Flash** to SD card with [balenaEtcher](https://etcher.balena.io/)
3. **Insert** SD card into Pi Zero 2W
4. **Power on** the device
5. **Connect** to WiFi: `Shadow-Setup` (password: `shadowpass123`)
6. **Open** http://192.168.4.1

### Default Credentials

| Service | Username/SSID | Password |
|---------|---------------|----------|
| SSH | `pi` | `shadow123` |
| WiFi AP | `Shadow-Setup` | `shadowpass123` |
| Web UI | - | http://192.168.4.1 |

### USB Connection (Alternative)

The image has USB Gadget mode enabled. Connect Pi Zero 2W to your computer via USB:

```bash
# Linux/Mac
ssh pi@shadow.local

# Windows (if mDNS not working)
# Check Device Manager for new network adapter
# IP is usually 169.254.x.x or configure manually
```

---

## Building Your Own Image

### Prerequisites

- Linux system (Ubuntu 22.04+ recommended)
- Docker (optional, but recommended)
- ~10GB free disk space
- ~2 hours build time

### Method 1: GitHub Actions (Recommended)

1. Fork the repository
2. Go to Actions → "Build SD Card Image"
3. Click "Run workflow"
4. Download artifact when complete

### Method 2: Local Build with Docker

```bash
# Clone pi-gen
git clone https://github.com/RPi-Distro/pi-gen.git
cd pi-gen

# Copy our stage
cp -r /path/to/MoMo-Shadow/deploy/image/stage-shadow ./

# Create config
cat > config << EOF
IMG_NAME="momo-shadow"
RELEASE="bookworm"
TARGET_HOSTNAME=shadow
FIRST_USER_NAME=pi
FIRST_USER_PASS=shadow123
ENABLE_SSH=1
STAGE_LIST="stage0 stage1 stage2 stage-shadow"
EOF

# Build with Docker
./build-docker.sh
```

### Method 3: Local Build (Native)

```bash
# Install dependencies
sudo apt-get install -y coreutils quilt parted qemu-user-static \
    debootstrap zerofree zip dosfstools libarchive-tools libcap2-bin \
    grep rsync xz-utils file git curl bc gpg pigz xxd arch-test

# Clone and configure pi-gen
git clone https://github.com/RPi-Distro/pi-gen.git
cd pi-gen

# Add our custom stage
cp -r /path/to/MoMo-Shadow/deploy/image/stage-shadow ./

# Create config (same as above)

# Build
sudo ./build.sh
```

### Output

Built images are in `pi-gen/deploy/`:
- `momo-shadow-shadow.img.xz` - Compressed image
- `momo-shadow-shadow.info` - Build info

---

## Customization

### Change Default WiFi Password

Edit `stage-shadow/02-configure/00-run-chroot.sh`:
```bash
wpa_passphrase=YOUR_NEW_PASSWORD
```

### Change Default SSH Password

Edit `pi-gen/config`:
```
FIRST_USER_PASS=your_new_password
```

### Add Your WiFi Network

For first boot with internet access, create `wpa_supplicant.conf` on boot partition:
```
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YourHomeWiFi"
    psk="YourPassword"
    key_mgmt=WPA-PSK
}
```

---

## Image Contents

```
📀 MoMo-Shadow Image
├── 🐧 Raspberry Pi OS Lite (Bookworm, 64-bit)
├── 🐍 Python 3.11 + venv
├── 🥷 MoMo-Shadow (pre-installed at /opt/shadow)
├── 📡 WiFi Tools (aircrack-ng, hcxtools, tcpdump)
├── 🔧 USB Gadget Mode (enabled)
├── 📶 WiFi AP (auto-configured)
└── ⚙️ Systemd Service (auto-start)
```

### Partition Layout

| Partition | Size | Filesystem | Contents |
|-----------|------|------------|----------|
| boot | 512MB | FAT32 | Kernel, config.txt |
| root | ~4GB | ext4 | OS + MoMo-Shadow |

### Services

| Service | Status | Description |
|---------|--------|-------------|
| shadow | enabled | Main application |
| hostapd | enabled | WiFi AP |
| dnsmasq | enabled | DHCP server |
| avahi-daemon | enabled | mDNS (.local) |
| ssh | enabled | Remote access |

---

## Troubleshooting

### Can't connect to WiFi AP

- Wait 60 seconds after boot
- Check if `Shadow-Setup` appears in WiFi list
- Try rebooting the Pi

### SSH connection refused

```bash
# Enable SSH by creating empty file on boot partition
touch /Volumes/boot/ssh  # Mac
# or
touch /media/$USER/boot/ssh  # Linux
```

### mDNS not working (shadow.local)

- Windows: Install [Bonjour](https://support.apple.com/kb/DL999)
- Try IP directly: `192.168.4.1` (when connected to Shadow AP)

### Image won't boot

- Re-flash with balenaEtcher
- Try different SD card
- Check power supply (5V/2.5A minimum)

