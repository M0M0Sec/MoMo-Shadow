#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
#                    MoMo-Shadow Image Builder
#                  Creates ready-to-flash SD card image
#═══════════════════════════════════════════════════════════════════════════════
#
# This script creates a complete Raspberry Pi OS image with:
# - Nexmon pre-installed
# - MoMo-Shadow pre-installed
# - Auto-start on boot
#
# Usage: sudo ./build-image.sh
#
# Output: shadow-v0.1.0-pi-zero-2w.img.xz
#
#═══════════════════════════════════════════════════════════════════════════════

set -e

VERSION="0.1.0"
IMAGE_NAME="shadow-v${VERSION}-pi-zero-2w"
WORK_DIR="/tmp/shadow-build"
OUTPUT_DIR="$(pwd)/output"

echo "═══════════════════════════════════════════════════════════════"
echo "              MoMo-Shadow Image Builder v${VERSION}"
echo "═══════════════════════════════════════════════════════════════"

# Check requirements
if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] Please run as root"
    exit 1
fi

# Check for pi-gen
if [ ! -d "/opt/pi-gen" ]; then
    echo "[*] Cloning pi-gen..."
    git clone https://github.com/RPi-Distro/pi-gen.git /opt/pi-gen
fi

cd /opt/pi-gen

# Create custom stage
STAGE_DIR="stage-shadow"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

# Stage config
cat > "$STAGE_DIR/EXPORT_IMAGE" << EOF
EOF

cat > "$STAGE_DIR/prerun.sh" << 'EOF'
#!/bin/bash -e
if [ ! -d "${ROOTFS_DIR}" ]; then
    copy_previous
fi
EOF
chmod +x "$STAGE_DIR/prerun.sh"

# Package installation
cat > "$STAGE_DIR/00-packages" << EOF
git
python3-pip
python3-venv
python3-dev
hostapd
dnsmasq
aircrack-ng
tcpdump
iw
wireless-tools
EOF

# Custom installation script
mkdir -p "$STAGE_DIR/files"
cat > "$STAGE_DIR/files/install-shadow.sh" << 'INSTALL_SCRIPT'
#!/bin/bash
set -e

# Install Nexmon
cd /opt
git clone https://github.com/seemoo-lab/nexmon.git
cd nexmon
source setup_env.sh

cd buildtools/isl-0.10
./configure && make && make install
ln -sf /usr/local/lib/libisl.so /usr/lib/arm-linux-gnueabihf/libisl.so.10

cd /opt/nexmon/utilities/libnexmon
make

cd /opt/nexmon/patches/bcm43436s/7_45_206/nexmon
make && make install-firmware

cd /opt/nexmon/utilities/nexutil
make && make install

# Install MoMo-Shadow
cd /opt
git clone https://github.com/M0M0Sec/MoMo-Shadow.git shadow
cd shadow
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .

# Create directories
mkdir -p /etc/shadow
mkdir -p /var/shadow/data
mkdir -p /var/shadow/captures

# Copy config
cp /opt/shadow/config/shadow.example.yml /etc/shadow/config.yml

# Install service
cp /opt/shadow/deploy/shadow.service /etc/systemd/system/
systemctl enable shadow.service

# Enable SPI
echo "dtparam=spi=on" >> /boot/config.txt

# Disable default WiFi
systemctl disable wpa_supplicant || true
INSTALL_SCRIPT
chmod +x "$STAGE_DIR/files/install-shadow.sh"

# Run script
cat > "$STAGE_DIR/01-run.sh" << 'EOF'
#!/bin/bash -e
install -m 755 files/install-shadow.sh "${ROOTFS_DIR}/tmp/"
on_chroot << CHROOT
/tmp/install-shadow.sh
rm /tmp/install-shadow.sh
CHROOT
EOF
chmod +x "$STAGE_DIR/01-run.sh"

# Build config
cat > config << EOF
IMG_NAME="${IMAGE_NAME}"
RELEASE="bookworm"
TARGET_HOSTNAME="shadow"
FIRST_USER_NAME="shadow"
FIRST_USER_PASS="shadow"
ENABLE_SSH=1
LOCALE_DEFAULT="en_US.UTF-8"
KEYBOARD_KEYMAP="us"
TIMEZONE_DEFAULT="UTC"
STAGE_LIST="stage0 stage1 stage2 stage-shadow"
EOF

# Build
echo "[*] Building image... (this will take a while)"
./build.sh

# Compress output
mkdir -p "$OUTPUT_DIR"
OUTPUT_IMAGE=$(find deploy -name "*.img" | head -1)
if [ -n "$OUTPUT_IMAGE" ]; then
    echo "[*] Compressing image..."
    xz -9 -k "$OUTPUT_IMAGE"
    mv "${OUTPUT_IMAGE}.xz" "$OUTPUT_DIR/${IMAGE_NAME}.img.xz"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "                    Build Complete!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "  Output: $OUTPUT_DIR/${IMAGE_NAME}.img.xz"
    echo ""
    echo "  Flash with:"
    echo "    xzcat ${IMAGE_NAME}.img.xz | sudo dd of=/dev/sdX bs=4M status=progress"
    echo ""
else
    echo "[ERROR] Build failed - no image found"
    exit 1
fi

