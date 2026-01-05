# 📝 Changelog

All notable changes to MoMo-Shadow will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- BLE device scanning
- GPS integration for wardriving
- Nexus sync integration
- PMKID capture support
- WPA3 SAE detection

---

## [0.1.0] - 2026-01-05

### Added

#### Core Features
- **WiFi Scanner** - Passive scanning with scapy
  - Access point discovery
  - Client detection
  - Probe request capture
  - Hidden SSID detection
  - Channel hopping

- **Handshake Capture** - WPA2 4-way handshake capture
  - EAPOL frame parsing
  - Multi-message tracking
  - PCAP export
  - Auto-stop on success

- **Deauth Attack** - Targeted deauthentication
  - AP to client deauth
  - Client to AP deauth
  - Configurable burst count/interval

- **Channel Hopper** - Automated channel cycling
  - 2.4GHz and 5GHz support
  - Configurable hop interval
  - Random/sequential modes

#### User Interface
- **e-Paper Display** - Waveshare 2.13" V4 support
  - 250x122 pixel resolution
  - Status screen (idle, scanning, capturing)
  - Statistics display
  - Battery indicator
  - WiFi AP credentials

- **Web UI** - Mobile-friendly dark theme
  - Real-time statistics
  - Access point list
  - Target selection
  - Mode switching
  - Capture control
  - System management

#### Network
- **WiFi AP** - Control access point
  - hostapd integration
  - dnsmasq for DHCP
  - Captive portal redirect

- **Interface Manager** - WiFi interface control
  - Monitor mode switching
  - Channel setting
  - MAC randomization

#### Storage
- **SQLite Database** - Async data persistence
  - Access points table
  - Clients table
  - Probe requests table
  - Handshakes table

- **Hashcat Export** - Capture export
  - hcxpcapngtool integration
  - Mode 22000 format

#### Hardware
- **Battery Monitor** - Power monitoring
  - PiSugar support
  - UPS HAT support
  - INA219 support
  - Mock mode for testing

- **Power Manager** - System power control
  - Shutdown/reboot
  - WiFi power save
  - CPU governor
  - Low power mode

#### Configuration
- **Pydantic Config** - Type-safe configuration
  - YAML file support
  - Environment variables
  - /boot/shadow.yml for headless
  - Validation and defaults

#### CLI
- **Typer CLI** - Command-line interface
  - `shadow run` - Start Shadow
  - `shadow status` - Show status
  - `shadow config` - Manage config
  - `shadow export` - Export captures
  - `shadow interfaces` - List WiFi interfaces
  - `shadow web` - Start web UI only

### Technical
- Python 3.11+ required
- Async/await throughout
- Clean architecture design
- Type hints on all functions
- Comprehensive docstrings

### Documentation
- README.md with full documentation
- OPERATIONS.md - Field guide
- HARDWARE.md - Assembly guide
- API.md - API reference
- CHANGELOG.md - This file

---

## Version History

| Version | Date | Status |
|---------|------|--------|
| 0.1.0 | 2026-01-05 | 🚧 Development |

---

## Upgrade Notes

### From Pre-release to 0.1.0

This is the initial release. No upgrade path needed.

---

## Contributors

- MoMo Team

---

*Part of the MoMo Ecosystem*

