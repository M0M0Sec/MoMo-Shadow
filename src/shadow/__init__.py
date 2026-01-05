"""
MoMo-Shadow - Stealth Recon Device

Pocket-sized WiFi reconnaissance device with e-Paper display.
Designed for Pi Zero 2W + Waveshare 2.13" e-Paper.

Features:
- Passive WiFi scanning
- Probe request capture
- WPA2/WPA3 handshake capture
- e-Paper display (low power)
- WiFi AP + Web UI control
- Drop & forget operations
"""

__version__ = "0.1.0"
__author__ = "MoMo Team"

from shadow.config import ShadowConfig
from shadow.main import ShadowOrchestrator, ShadowState

__all__ = [
    "__version__",
    "ShadowConfig",
    "ShadowOrchestrator",
    "ShadowState",
]
