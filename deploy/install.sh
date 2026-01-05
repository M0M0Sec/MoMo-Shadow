#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
#                    MoMo-Shadow Complete Installation Script
#                         One Command, Everything Included
#═══════════════════════════════════════════════════════════════════════════════
#
# Usage: curl -fsSL https://raw.githubusercontent.com/M0M0Sec/MoMo-Shadow/main/deploy/install.sh | sudo bash
#
# This script installs:
# - System dependencies
# - Nexmon (for monitor mode on Pi Zero 2W)
# - MoMo-Shadow application
# - Systemd services
#
#═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Directories
INSTALL_DIR="/opt/shadow"
CONFIG_DIR="/etc/shadow"
DATA_DIR="/var/shadow"
NEXMON_DIR="/opt/nexmon"

# Banner
echo -e "${CYAN}"
cat << "EOF"
  __  __       __  __           _____ _               _               
 |  \/  |     |  \/  |         / ____| |             | |              
 | \  / | ___ | \  / | ___    | (___ | |__   __ _  __| | _____      __
 | |\/| |/ _ \| |\/| |/ _ \    \___ \| '_ \ / _` |/ _` |/ _ \ \ /\ / /
 | |  | | (_) | |  | | (_) |   ____) | | | | (_| | (_| | (_) \ V  V / 
 |_|  |_|\___/|_|  |_|\___/   |_____/|_| |_|\__,_|\__,_|\___/ \_/\_/  
                                                                       
                    Stealth WiFi Recon Device
                         v0.1.0 Installer
EOF
echo -e "${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] Please run as root (sudo)${NC}"
    exit 1
fi

# Detect platform
detect_platform() {
    echo -e "${CYAN}[*] Detecting platform...${NC}"
    
    if [ ! -f /proc/cpuinfo ]; then
        echo -e "${RED}[ERROR] Cannot detect platform${NC}"
        exit 1
    fi
    
    if grep -q "Raspberry Pi Zero 2" /proc/cpuinfo; then
        PLATFORM="pi_zero_2w"
        CHIP="bcm43436s"
        echo -e "${GREEN}[✓] Raspberry Pi Zero 2W detected${NC}"
    elif grep -q "Raspberry Pi Zero W" /proc/cpuinfo; then
        PLATFORM="pi_zero_w"
        CHIP="bcm43430a1"
        echo -e "${GREEN}[✓] Raspberry Pi Zero W detected${NC}"
    elif grep -q "Raspberry Pi 3" /proc/cpuinfo; then
        PLATFORM="pi_3"
        CHIP="bcm43430a1"
        echo -e "${GREEN}[✓] Raspberry Pi 3 detected${NC}"
    elif grep -q "Raspberry Pi 4" /proc/cpuinfo; then
        PLATFORM="pi_4"
        CHIP="bcm43455c0"
        echo -e "${GREEN}[✓] Raspberry Pi 4 detected${NC}"
    else
        echo -e "${YELLOW}[!] Unknown platform - Nexmon may not work${NC}"
        PLATFORM="unknown"
        CHIP="unknown"
    fi
}

# Install system dependencies
install_dependencies() {
    echo -e "${CYAN}[*] Installing system dependencies...${NC}"
    
    apt update
    apt install -y \
        git \
        build-essential \
        python3-pip \
        python3-venv \
        python3-dev \
        libgmp3-dev \
        gawk \
        qpdf \
        bison \
        flex \
        make \
        autoconf \
        libtool \
        texinfo \
        libffi-dev \
        libssl-dev \
        hostapd \
        dnsmasq \
        aircrack-ng \
        hcxtools \
        tcpdump \
        iw \
        wireless-tools
    
    # Install kernel headers (package name varies by distro)
    echo -e "${CYAN}[*] Installing kernel headers...${NC}"
    KERNEL_VER=$(uname -r)
    
    if apt install -y "linux-headers-${KERNEL_VER}" 2>/dev/null; then
        echo -e "${GREEN}[✓] Kernel headers installed (linux-headers-${KERNEL_VER})${NC}"
    elif apt install -y linux-headers-rpi-v8 2>/dev/null; then
        echo -e "${GREEN}[✓] Kernel headers installed (linux-headers-rpi-v8)${NC}"
    elif apt install -y raspberrypi-kernel-headers 2>/dev/null; then
        echo -e "${GREEN}[✓] Kernel headers installed (raspberrypi-kernel-headers)${NC}"
    elif apt install -y linux-headers-generic 2>/dev/null; then
        echo -e "${GREEN}[✓] Kernel headers installed (linux-headers-generic)${NC}"
    else
        echo -e "${YELLOW}[!] Could not install kernel headers - Nexmon compilation may fail${NC}"
        echo -e "${YELLOW}[!] Continuing without kernel headers...${NC}"
    fi
    
    echo -e "${GREEN}[✓] Dependencies installed${NC}"
}

# Install Nexmon
install_nexmon() {
    echo -e "${CYAN}[*] Installing Nexmon for ${CHIP}...${NC}"
    
    if [ "$PLATFORM" = "unknown" ]; then
        echo -e "${YELLOW}[!] Skipping Nexmon - unknown platform${NC}"
        return
    fi
    
    # Check if already installed
    if command -v nexutil &> /dev/null; then
        echo -e "${GREEN}[✓] Nexmon already installed${NC}"
        return
    fi
    
    # Clone Nexmon
    if [ ! -d "$NEXMON_DIR" ]; then
        git clone https://github.com/seemoo-lab/nexmon.git "$NEXMON_DIR"
    fi
    
    cd "$NEXMON_DIR"
    
    # Setup build environment
    source setup_env.sh
    
    # Build firmware tools
    cd buildtools/isl-0.10
    ./configure
    make
    make install
    ln -sf /usr/local/lib/libisl.so /usr/lib/arm-linux-gnueabihf/libisl.so.10
    
    cd "$NEXMON_DIR"
    
    # Build utilities
    cd utilities/libnexmon
    make
    
    # Determine kernel version and build path
    KERNEL_VER=$(uname -r | cut -d'.' -f1-2)
    
    # Build for specific chip
    cd "$NEXMON_DIR/patches/$CHIP"
    
    # Find appropriate firmware version
    if [ -d "7_45_189" ]; then
        FIRMWARE_VER="7_45_189"
    elif [ -d "7_45_206" ]; then
        FIRMWARE_VER="7_45_206"
    elif [ -d "7_45_241" ]; then
        FIRMWARE_VER="7_45_241"
    else
        FIRMWARE_VER=$(ls -d */ | head -1 | tr -d '/')
    fi
    
    if [ -z "$FIRMWARE_VER" ]; then
        echo -e "${RED}[ERROR] No firmware version found for ${CHIP}${NC}"
        return 1
    fi
    
    echo -e "${CYAN}[*] Building Nexmon for ${CHIP}/${FIRMWARE_VER}...${NC}"
    
    cd "$NEXMON_DIR/patches/$CHIP/$FIRMWARE_VER/nexmon"
    make
    
    # Backup original firmware
    ORIG_FW="/lib/firmware/brcm/brcmfmac43436-sdio.bin"
    if [ -f "$ORIG_FW" ] && [ ! -f "${ORIG_FW}.orig" ]; then
        cp "$ORIG_FW" "${ORIG_FW}.orig"
    fi
    
    # Install patched firmware
    make install-firmware
    
    # Install nexutil
    cd "$NEXMON_DIR/utilities/nexutil"
    make
    make install
    
    echo -e "${GREEN}[✓] Nexmon installed${NC}"
    
    # Unload and reload driver
    echo -e "${CYAN}[*] Reloading WiFi driver...${NC}"
    rmmod brcmfmac 2>/dev/null || true
    modprobe brcmfmac
    
    sleep 3
}

# Install MoMo-Shadow
install_shadow() {
    echo -e "${CYAN}[*] Installing MoMo-Shadow...${NC}"
    
    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$DATA_DIR/data"
    mkdir -p "$DATA_DIR/captures"
    
    # Clone or update
    if [ -d "$INSTALL_DIR/.git" ]; then
        cd "$INSTALL_DIR"
        git pull
    else
        rm -rf "$INSTALL_DIR"
        git clone https://github.com/M0M0Sec/MoMo-Shadow.git "$INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip wheel setuptools
    
    # Install Shadow
    pip install -e .
    
    # Install optional dependencies
    pip install waveshare-epd 2>/dev/null || echo -e "${YELLOW}[!] waveshare-epd not available (will use mock display)${NC}"
    pip install smbus2 2>/dev/null || echo -e "${YELLOW}[!] smbus2 not available (battery monitoring limited)${NC}"
    
    echo -e "${GREEN}[✓] MoMo-Shadow installed${NC}"
}

# Configure system
configure_system() {
    echo -e "${CYAN}[*] Configuring system...${NC}"
    
    # Enable SPI for e-Paper
    if ! grep -q "dtparam=spi=on" /boot/config.txt; then
        echo "dtparam=spi=on" >> /boot/config.txt
        echo -e "${GREEN}[✓] SPI enabled${NC}"
    fi
    
    # Disable default WiFi management
    systemctl disable wpa_supplicant 2>/dev/null || true
    systemctl stop wpa_supplicant 2>/dev/null || true
    
    # Copy default config if not exists
    if [ ! -f "$CONFIG_DIR/config.yml" ]; then
        cp "$INSTALL_DIR/config/shadow.example.yml" "$CONFIG_DIR/config.yml"
        echo -e "${GREEN}[✓] Default config created${NC}"
    fi
    
    # Install systemd service
    cp "$INSTALL_DIR/deploy/shadow.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable shadow.service
    
    echo -e "${GREEN}[✓] System configured${NC}"
}

# Verify installation
verify_installation() {
    echo -e "${CYAN}[*] Verifying installation...${NC}"
    
    ERRORS=0
    
    # Check Nexmon
    if command -v nexutil &> /dev/null; then
        echo -e "${GREEN}[✓] nexutil available${NC}"
    else
        echo -e "${YELLOW}[!] nexutil not found - monitor mode may not work${NC}"
        ERRORS=$((ERRORS+1))
    fi
    
    # Check Shadow CLI
    if "$INSTALL_DIR/venv/bin/shadow" version &> /dev/null; then
        echo -e "${GREEN}[✓] shadow CLI working${NC}"
    else
        echo -e "${RED}[✗] shadow CLI failed${NC}"
        ERRORS=$((ERRORS+1))
    fi
    
    # Check monitor mode
    echo -e "${CYAN}[*] Testing monitor mode...${NC}"
    
    ip link set wlan0 down 2>/dev/null || true
    if iw dev wlan0 set type monitor 2>/dev/null; then
        echo -e "${GREEN}[✓] Monitor mode supported${NC}"
        iw dev wlan0 set type managed 2>/dev/null || true
    else
        echo -e "${YELLOW}[!] Monitor mode test failed - may need reboot${NC}"
    fi
    ip link set wlan0 up 2>/dev/null || true
    
    return $ERRORS
}

# Print summary
print_summary() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}           MoMo-Shadow Installation Complete!${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${CYAN}Platform:${NC}     $PLATFORM ($CHIP)"
    echo -e "  ${CYAN}Install Dir:${NC}  $INSTALL_DIR"
    echo -e "  ${CYAN}Config:${NC}       $CONFIG_DIR/config.yml"
    echo -e "  ${CYAN}Data:${NC}         $DATA_DIR"
    echo ""
    echo -e "${YELLOW}  Commands:${NC}"
    echo -e "    Start:    ${GREEN}sudo systemctl start shadow${NC}"
    echo -e "    Stop:     ${GREEN}sudo systemctl stop shadow${NC}"
    echo -e "    Status:   ${GREEN}sudo systemctl status shadow${NC}"
    echo -e "    Logs:     ${GREEN}sudo journalctl -u shadow -f${NC}"
    echo -e "    CLI:      ${GREEN}shadow run${NC}"
    echo ""
    echo -e "${YELLOW}  Usage:${NC}"
    echo -e "    1. Reboot the device"
    echo -e "    2. Connect to WiFi: ${GREEN}Shadow-XXXX${NC}"
    echo -e "    3. Password: ${GREEN}shadowpass123${NC}"
    echo -e "    4. Open: ${GREEN}http://192.168.4.1${NC}"
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Main installation
main() {
    echo -e "${CYAN}[*] Starting MoMo-Shadow installation...${NC}"
    echo ""
    
    detect_platform
    install_dependencies
    install_nexmon
    install_shadow
    configure_system
    
    if verify_installation; then
        print_summary
        echo -e "${YELLOW}[!] Please reboot to apply all changes:${NC}"
        echo -e "    ${GREEN}sudo reboot${NC}"
    else
        echo -e "${YELLOW}[!] Installation completed with warnings${NC}"
        echo -e "${YELLOW}[!] Please reboot and check logs${NC}"
        print_summary
    fi
}

# Run main
main "$@"
