# 🔧 MoMo-Shadow Hardware Guide

> Complete hardware setup and assembly instructions

---

## 📋 Table of Contents

- [Bill of Materials](#bill-of-materials)
- [Component Details](#component-details)
- [Assembly Guide](#assembly-guide)
- [Wiring Diagram](#wiring-diagram)
- [Enclosure Options](#enclosure-options)
- [Power Options](#power-options)
- [Troubleshooting](#troubleshooting)

---

## 📦 Bill of Materials

### Required Components (Minimum Build)

| Component | Model | Quantity | Price | Link |
|-----------|-------|:--------:|------:|------|
| SBC | Raspberry Pi Zero 2W | 1 | $15 | [raspberrypi.com](https://www.raspberrypi.com) |
| Display | Waveshare 2.13" e-Paper HAT (V4) | 1 | $20 | [waveshare.com](https://www.waveshare.com) |
| MicroSD | 16GB+ Class 10 | 1 | $5 | Amazon |
| **Subtotal** | | | **$40** | |

> 🎉 **No external WiFi adapter needed!** Uses Nexmon-patched internal WiFi for monitor mode.

### Power Options (Choose One)

| Option | Model | Price | Runtime | Notes |
|--------|-------|------:|---------|-------|
| **A** | PiSugar 2 | $30 | 6-8h | Integrated, easy |
| **B** | LiPo + TP4056 | $8 | 10-12h | DIY, compact |
| **C** | USB Power Bank | $10 | 8-10h | Simple, bulky |

### Optional Components

| Component | Purpose | Price |
|-----------|---------|------:|
| GPS Module (VK-162) | Wardriving | $10 |
| 3D Printed Case | Enclosure | $5 |
| Heat Sink | Thermal management | $2 |

---

## 🔍 Component Details

### Raspberry Pi Zero 2W

```
Specifications:
├── CPU: Quad-core ARM Cortex-A53 @ 1GHz
├── RAM: 512MB
├── WiFi: 2.4GHz 802.11 b/g/n (BCM43436s)
├── Bluetooth: 4.2 BLE
├── GPIO: 40-pin header
├── USB: 1x Micro USB (OTG)
└── Power: 5V via Micro USB

Nexmon Support:
• BCM43436s chip supports Nexmon firmware patch
• Enables monitor mode on internal WiFi
• Same interface switches between AP ↔ Monitor mode
• Pwnagotchi compatibility confirmed ✅

Notes:
• No external WiFi adapter needed!
• Single interface design (AP or Monitor, not both)
• 2.4GHz only (no 5GHz support)
• GPIO header for e-Paper HAT
```

### Waveshare 2.13" e-Paper HAT (V4)

```
Specifications:
├── Resolution: 250 x 122 pixels
├── Colors: Black/White
├── Interface: SPI
├── Refresh: Full ~2s, Partial ~0.3s
├── Power: <0.01mW in sleep
└── Viewing: 180° (e-Paper)

Notes:
• V4 has faster partial refresh
• Works in direct sunlight
• No backlight needed
• HAT form factor (plugs into GPIO)
```

### WiFi (Nexmon - Internal)

**Internal WiFi with Nexmon Firmware:**

```
Chip: Broadcom BCM43436s
├── Nexmon patch enables monitor mode ✅
├── Packet injection supported ✅
├── 2.4GHz channels 1-13
├── No 5GHz support
└── Pwnagotchi compatible

Mode Switching:
┌─────────────┐         ┌─────────────┐
│  AP Mode    │ ◄─────► │Monitor Mode │
│  (Setup)    │         │ (Scanning)  │
└─────────────┘         └─────────────┘
     │                        │
     │ Web UI control         │ WiFi scanning
     │ Configuration          │ Handshake capture
     └────────────────────────┘
```

**Optional: External WiFi Adapter**

If you want 5GHz support or simultaneous AP+Monitor:

| Chipset | Model | Monitor | 5GHz | Driver |
|---------|-------|:-------:|:----:|--------|
| RTL8812AU | Alfa AWUS036ACH | ✅ | ✅ | rtl8812au |
| MT7612U | Alfa AWUS036ACM | ✅ | ✅ | mt76 |

---

## 🔨 Assembly Guide

### Step 1: Prepare Pi Zero 2W

```
1. Solder GPIO header (if not pre-soldered)
   • Use 2x20 pin header
   • Solder from component side
   • Check all pins are connected

2. Flash SD Card
   • Download Raspberry Pi OS Lite (64-bit)
   • Flash with Balena Etcher or dd
   • Enable SSH: touch /boot/ssh

3. One-Line Install (after first boot)
   • SSH into Pi
   • Run: curl -fsSL https://shadow.momo.dev/install | sudo bash
   • Reboot when prompted
   
   The installer handles EVERYTHING:
   ✅ System dependencies
   ✅ Nexmon (monitor mode)
   ✅ MoMo-Shadow
   ✅ SPI for e-Paper
   ✅ Systemd service
```

### Step 2: Attach e-Paper HAT

```
1. Align HAT with GPIO header
   • Pin 1 (3.3V) aligned with Pi Pin 1
   • All 40 pins should match

2. Press firmly until seated
   • No bent pins
   • HAT should be parallel to Pi

3. Connect ribbon cable (if separate)
   • Some HATs have detachable display
```

### Step 3: Connect WiFi Adapter

```
1. Connect OTG adapter to Pi
   • Micro USB (data port, not power)
   
2. Connect WiFi adapter to OTG
   • May need short USB extension
   
3. Position antenna
   • Away from Pi/display for less interference
```

### Step 4: Power Setup

**Option A: PiSugar**
```
1. Attach PiSugar to back of Pi
2. Connect via pogo pins or cable
3. Charge via USB-C on PiSugar
4. Power button on PiSugar
```

**Option B: LiPo + TP4056**
```
1. Connect TP4056 to LiPo battery
2. Connect TP4056 OUT to Pi 5V
   • Red wire to Pin 2 (5V)
   • Black wire to Pin 6 (GND)
3. Charge via Micro USB on TP4056
```

**Option C: Power Bank**
```
1. Connect power bank to Pi power port
2. Simple but larger form factor
3. Ensure bank doesn't auto-off
```

---

## 📊 Wiring Diagram

### e-Paper HAT Pinout

```
e-Paper 2.13" V4 → Pi Zero 2W
═══════════════════════════════════════

Display Pin    Function    Pi GPIO    Pi Pin
───────────────────────────────────────
VCC            Power       3.3V       1
GND            Ground      GND        6
DIN            Data In     GPIO10     19 (MOSI)
CLK            Clock       GPIO11     23 (SCLK)
CS             Chip Sel    GPIO8      24 (CE0)
DC             Data/Cmd    GPIO25     22
RST            Reset       GPIO17     11
BUSY           Busy        GPIO24     18


┌─────────────────────────────────────────────────────┐
│                    PI ZERO 2W                        │
│                    GPIO HEADER                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│   3V3 (1) ●  ● (2) 5V         VCC ← e-Paper        │
│   SDA (3) ●  ● (4) 5V                               │
│   SCL (5) ●  ● (6) GND        GND ← e-Paper        │
│    4  (7) ●  ● (8) TXD                              │
│   GND (9) ●  ● (10) RXD                             │
│   17 (11) ●  ● (12) 18        RST ← e-Paper        │
│   27 (13) ●  ● (14) GND                             │
│   22 (15) ●  ● (16) 23                              │
│  3V3 (17) ●  ● (18) 24        BUSY ← e-Paper       │
│   10 (19) ●  ● (20) GND       DIN ← e-Paper        │
│    9 (21) ●  ● (22) 25        DC ← e-Paper         │
│   11 (23) ●  ● (24) 8         CLK ← e-Paper        │
│  GND (25) ●  ● (26) 7         CS ← e-Paper         │
│    0 (27) ●  ● (28) 1                               │
│    5 (29) ●  ● (30) GND                             │
│    6 (31) ●  ● (32) 12                              │
│   13 (33) ●  ● (34) GND                             │
│   19 (35) ●  ● (36) 16                              │
│   26 (37) ●  ● (38) 20                              │
│  GND (39) ●  ● (40) 21                              │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Power Wiring (DIY LiPo)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   LiPo      │     │   TP4056    │     │  Pi Zero    │
│  Battery    │     │   Charger   │     │             │
│             │     │             │     │             │
│  (+) ───────┼─────┤ B+     OUT+ ├─────┤ 5V (Pin 2)  │
│  (-) ───────┼─────┤ B-     OUT- ├─────┤ GND (Pin 6) │
│             │     │             │     │             │
└─────────────┘     │    USB      │     └─────────────┘
                    │  (Charge)   │
                    └─────────────┘

⚠️ WARNING: Double-check polarity before connecting!
```

---

## 📦 Enclosure Options

### Option 1: 3D Printed Case

```
Dimensions: 75 x 45 x 20mm
Features:
├── Pi Zero + HAT fit
├── Battery compartment
├── USB port access
├── Antenna slot
└── Ventilation holes

Files: /docs/stl/shadow-case.stl
```

### Option 2: Commercial Case

```
Compatible Cases:
├── Pimoroni Pibow Zero
├── Official Pi Zero case
├── Generic ABS case
└── Hammond project box

Modifications needed:
├── Cut hole for display
├── Drill USB port hole
└── Add antenna mount
```

### Option 3: Covert Housing

```
Ideas:
├── USB charger shell
├── Smoke detector housing
├── Electrical box
├── Book hollowed out
└── Custom 3D print

Considerations:
├── Heat dissipation
├── RF transparency
├── Antenna placement
└── Physical access
```

---

## 🔋 Power Options

### Runtime Estimates

| Mode | PiSugar 2 (1200mAh) | LiPo (2000mAh) | Power Bank (5000mAh) |
|------|:-------------------:|:--------------:|:--------------------:|
| Passive | 6-8h | 10-14h | 20-25h |
| Capture | 4-6h | 8-10h | 15-20h |
| Drop | 10-12h | 16-24h | 30-40h |

### Power Consumption

```
Component          Active    Idle
───────────────────────────────────
Pi Zero 2W         120mA     80mA
e-Paper (refresh)  15mA      0.01mA
WiFi Adapter       300mA     50mA
───────────────────────────────────
Total (Active)     ~435mA
Total (Idle)       ~130mA
```

### Battery Recommendations

| Capacity | Form Factor | Runtime (Passive) |
|----------|-------------|:-----------------:|
| 1200mAh | Small | 6-8h |
| 2000mAh | Medium | 10-14h |
| 3000mAh | Large | 16-20h |
| 5000mAh | Power bank | 30-40h |

---

## 🔧 Troubleshooting

### e-Paper Not Displaying

```
Check:
□ SPI enabled in /boot/config.txt
□ HAT properly seated
□ Correct GPIO pins
□ waveshare-epd library installed

Test:
$ ls /dev/spidev*
# Should show /dev/spidev0.0

$ python3 -c "from waveshare_epd import epd2in13_V4; print('OK')"
```

### WiFi Adapter Not Found

```
Check:
□ Adapter connected to data port (not power)
□ OTG adapter working
□ Correct driver installed

Test:
$ lsusb
# Should show your adapter

$ iw dev
# Should show wlan interface

$ iwconfig wlan1
# Should show wireless info
```

### Monitor Mode Fails

```
Check:
□ Adapter supports monitor mode
□ Correct driver version
□ Interface not in use

Fix:
$ sudo airmon-ng check kill
$ sudo iw dev wlan1 set type monitor
$ sudo ip link set wlan1 up
```

### Battery Not Charging

```
Check:
□ Correct polarity
□ Charger LED status
□ Battery voltage (should be 3.0-4.2V)

TP4056 LEDs:
├── Red = Charging
├── Blue = Full
└── Both off = No battery
```

### Overheating

```
Causes:
├── No ventilation
├── Heavy WiFi load
├── Direct sunlight

Solutions:
├── Add heat sink
├── Add ventilation holes
├── Reduce TX power
├── Use passive mode
```

---

## 📐 Specifications Summary

```
┌─────────────────────────────────────────────────────┐
│              MOMO-SHADOW SPECS                       │
├─────────────────────────────────────────────────────┤
│  Dimensions:    75 x 45 x 20mm (without antenna)    │
│  Weight:        ~80g (with battery)                 │
│  Display:       250 x 122 pixels (e-Paper)          │
│  Battery:       10-72h (mode dependent)             │
│  WiFi:          Monitor mode + AP mode              │
│  Storage:       16GB+ MicroSD                       │
│  Interface:     WiFi AP + Web UI                    │
│  OS:            Raspberry Pi OS Lite (64-bit)       │
│  Python:        3.11+                               │
└─────────────────────────────────────────────────────┘
```

---

*Last Updated: January 2026*

