# 📡 MoMo-Shadow API Reference

> REST API documentation for web interface and automation

---

## 📋 Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Status](#status)
  - [Access Points](#access-points)
  - [Clients](#clients)
  - [Probes](#probes)
  - [Handshakes](#handshakes)
  - [Control](#control)
  - [System](#system)
- [WebSocket Events](#websocket-events)
- [Error Handling](#error-handling)

---

## 🌐 Overview

**Base URL**: `http://192.168.4.1` (via WiFi AP)

**Content Type**: `application/json`

**API Version**: `v1`

```bash
# Example request
curl http://192.168.4.1/api/status
```

---

## 🔐 Authentication

By default, authentication is disabled when connecting via WiFi AP.

### Enable Authentication

```yaml
# config.yml
web:
  auth_enabled: true
  auth_token: "your-secret-token"
```

### Using Token

```bash
# Header
curl -H "Authorization: Bearer your-secret-token" \
     http://192.168.4.1/api/status

# Query parameter
curl "http://192.168.4.1/api/status?token=your-secret-token"
```

---

## 📍 Endpoints

### Status

#### GET `/api/status`

Get current device status.

**Response:**
```json
{
  "state": "scanning",
  "mode": "passive",
  "uptime": 3600,
  "ap_count": 15,
  "client_count": 42,
  "probe_count": 156,
  "handshake_count": 2,
  "battery_percent": 85,
  "target_ssid": null
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `state` | string | Current state: `idle`, `scanning`, `capturing`, `stopped`, `error` |
| `mode` | string | Operation mode: `passive`, `capture`, `drop` |
| `uptime` | int | Seconds since start |
| `ap_count` | int | Discovered access points |
| `client_count` | int | Discovered clients |
| `probe_count` | int | Captured probe requests |
| `handshake_count` | int | Captured handshakes |
| `battery_percent` | int | Battery level (0-100) |
| `target_ssid` | string | Current capture target (null if none) |

---

### Access Points

#### GET `/api/aps`

Get discovered access points.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 100 | Max results |
| `sort` | string | `signal` | Sort by: `signal`, `ssid`, `clients` |

**Response:**
```json
[
  {
    "bssid": "AA:BB:CC:DD:EE:FF",
    "ssid": "Corp-WiFi",
    "channel": 6,
    "signal_dbm": -45,
    "security": "WPA2",
    "clients": 5,
    "hidden": false
  }
]
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bssid` | string | MAC address |
| `ssid` | string | Network name |
| `channel` | int | WiFi channel |
| `signal_dbm` | int | Signal strength in dBm |
| `security` | string | `OPEN`, `WEP`, `WPA`, `WPA2`, `WPA3` |
| `clients` | int | Connected client count |
| `hidden` | bool | Is SSID hidden |

---

### Clients

#### GET `/api/clients`

Get discovered WiFi clients.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `bssid` | string | - | Filter by AP BSSID |
| `limit` | int | 100 | Max results |

**Response:**
```json
[
  {
    "mac": "11:22:33:44:55:66",
    "bssid": "AA:BB:CC:DD:EE:FF",
    "signal_dbm": -52,
    "probes": ["Home-WiFi", "Corp-Guest"]
  }
]
```

---

### Probes

#### GET `/api/probes`

Get captured probe requests.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `ssid` | string | - | Filter by probed SSID |
| `limit` | int | 100 | Max results |

**Response:**
```json
[
  {
    "client_mac": "11:22:33:44:55:66",
    "ssid": "Home-WiFi",
    "signal_dbm": -60,
    "timestamp": "2026-01-05T12:30:00Z"
  }
]
```

---

### Handshakes

#### GET `/api/handshakes`

Get captured handshakes.

**Response:**
```json
[
  {
    "bssid": "AA:BB:CC:DD:EE:FF",
    "ssid": "Corp-WiFi",
    "client_mac": "11:22:33:44:55:66",
    "capture_type": "handshake",
    "timestamp": "2026-01-05T12:45:00Z",
    "complete": true,
    "pcap_path": "/var/momo-shadow/captures/Corp-WiFi_AABBCCDDEEFF_20260105.pcap"
  }
]
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `capture_type` | string | `handshake` or `pmkid` |
| `complete` | bool | Has all required EAPOL messages |
| `pcap_path` | string | Path to capture file |

---

### Control

#### POST `/api/mode`

Change operation mode.

**Request:**
```json
{
  "mode": "capture"
}
```

**Modes:** `passive`, `capture`, `drop`

**Response:**
```json
{
  "status": "ok",
  "mode": "capture"
}
```

---

#### POST `/api/target`

Set capture target.

**Request:**
```json
{
  "bssid": "AA:BB:CC:DD:EE:FF",
  "ssid": "Corp-WiFi"
}
```

**Response:**
```json
{
  "status": "ok",
  "target": "Corp-WiFi"
}
```

---

#### POST `/api/capture/start`

Start handshake capture for current target.

**Response:**
```json
{
  "status": "ok"
}
```

**Errors:**
- `400`: No target selected

---

#### POST `/api/capture/stop`

Stop current capture.

**Response:**
```json
{
  "status": "ok"
}
```

---

#### POST `/api/deauth`

Send deauthentication packets.

**Request:**
```json
{
  "bssid": "AA:BB:CC:DD:EE:FF",
  "ssid": "Corp-WiFi"
}
```

**Response:**
```json
{
  "status": "ok"
}
```

---

### System

#### GET `/api/config`

Get current configuration.

**Response:**
```json
{
  "device": {
    "name": "shadow-01"
  },
  "ap": {
    "enabled": true,
    "ssid": "Shadow-A3F2",
    "hidden": false
  },
  "autostart": {
    "mode": "passive",
    "delay": 10
  }
  // ... full config
}
```

---

#### POST `/api/shutdown`

Shutdown device.

**Response:**
```json
{
  "status": "shutting_down"
}
```

---

#### POST `/api/reboot`

Reboot device.

**Response:**
```json
{
  "status": "rebooting"
}
```

---

## 📡 WebSocket Events

**Endpoint**: `ws://192.168.4.1/ws`

### Event Types

```json
// New AP discovered
{
  "event": "ap_found",
  "data": {
    "bssid": "AA:BB:CC:DD:EE:FF",
    "ssid": "Corp-WiFi",
    "channel": 6
  }
}

// Handshake captured
{
  "event": "handshake",
  "data": {
    "ssid": "Corp-WiFi",
    "complete": true
  }
}

// Status update
{
  "event": "status",
  "data": {
    "state": "capturing",
    "battery_percent": 82
  }
}

// Error
{
  "event": "error",
  "data": {
    "message": "Capture timeout"
  }
}
```

### JavaScript Example

```javascript
const ws = new WebSocket('ws://192.168.4.1/ws');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  switch (msg.event) {
    case 'ap_found':
      console.log('New AP:', msg.data.ssid);
      break;
    case 'handshake':
      console.log('Handshake captured!');
      break;
  }
};
```

---

## ❌ Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `400` | Bad Request (invalid parameters) |
| `401` | Unauthorized (auth required) |
| `404` | Not Found |
| `500` | Internal Server Error |
| `503` | Service Unavailable (not ready) |

### Error Response Format

```json
{
  "detail": "Error message here"
}
```

### Common Errors

```json
// No target selected
{
  "detail": "No target selected"
}

// Invalid mode
{
  "detail": "Invalid mode"
}

// Service not ready
{
  "detail": "Service not ready"
}
```

---

## 🔧 Examples

### Python Client

```python
import requests

BASE = "http://192.168.4.1"

# Get status
status = requests.get(f"{BASE}/api/status").json()
print(f"APs: {status['ap_count']}")

# Get access points
aps = requests.get(f"{BASE}/api/aps").json()
for ap in aps:
    print(f"{ap['ssid']} ({ap['signal_dbm']}dBm)")

# Set target and capture
requests.post(f"{BASE}/api/target", json={
    "bssid": "AA:BB:CC:DD:EE:FF",
    "ssid": "Corp-WiFi"
})
requests.post(f"{BASE}/api/capture/start")
```

### Bash/cURL

```bash
#!/bin/bash
BASE="http://192.168.4.1"

# Get status
curl -s "$BASE/api/status" | jq

# List APs
curl -s "$BASE/api/aps" | jq '.[] | .ssid'

# Set mode
curl -X POST "$BASE/api/mode" \
  -H "Content-Type: application/json" \
  -d '{"mode": "capture"}'

# Shutdown
curl -X POST "$BASE/api/shutdown"
```

---

*Last Updated: January 2026*

