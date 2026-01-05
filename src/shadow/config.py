"""
Shadow Configuration Module

Pydantic-based configuration with YAML support.
Designed for headless operation via /boot/shadow.yml
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DeviceConfig(BaseModel):
    """Device identification."""

    name: str = Field(default="shadow-01", description="Device name")


class APConfig(BaseModel):
    """WiFi Access Point configuration for control."""

    enabled: bool = Field(default=True, description="Enable WiFi AP for control")
    ssid: str = Field(default="Shadow-{random}", description="AP SSID ({random} = 4 hex chars)")
    password: str = Field(default="shadowpass123", min_length=8, description="AP password")
    hidden: bool = Field(default=False, description="Hide SSID")
    channel: int = Field(default=6, ge=1, le=13, description="WiFi channel")
    setup_timeout: int = Field(default=60, ge=10, le=300, description="AP mode timeout before auto-switching to monitor (seconds)")

    def get_ssid(self) -> str:
        """Get SSID with random suffix if specified."""
        if "{random}" in self.ssid:
            return self.ssid.replace("{random}", secrets.token_hex(2).upper())
        return self.ssid


class WebConfig(BaseModel):
    """Web UI configuration."""

    enabled: bool = Field(default=True, description="Enable Web UI")
    host: str = Field(default="0.0.0.0", description="Bind host")
    port: int = Field(default=80, ge=1, le=65535, description="Bind port")
    auth_enabled: bool = Field(default=False, description="Require authentication")
    auth_token: str = Field(default="", description="Auth token (empty = use AP password)")


class AutostartConfig(BaseModel):
    """Autostart configuration."""

    enabled: bool = Field(default=True, description="Enable autostart on boot")
    mode: str = Field(default="passive", description="Operation mode")
    delay: int = Field(default=10, ge=0, le=300, description="Delay before start (seconds)")

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Validate operation mode."""
        allowed = {"passive", "capture", "drop"}
        if v.lower() not in allowed:
            raise ValueError(f"Mode must be one of: {allowed}")
        return v.lower()


class TargetsConfig(BaseModel):
    """Target filtering configuration."""

    ssids: list[str] = Field(default_factory=list, description="Target SSIDs (empty = all)")
    bssids: list[str] = Field(default_factory=list, description="Target BSSIDs")
    ignore: list[str] = Field(default_factory=list, description="SSIDs to ignore")


class ScanConfig(BaseModel):
    """WiFi scanning configuration."""

    channels_2g: list[int] = Field(
        default=[1, 6, 11],
        description="2.4GHz channels to scan",
    )
    channels_5g: list[int] = Field(
        default=[36, 40, 44, 48],
        description="5GHz channels to scan",
    )
    hop_interval: float = Field(default=0.5, ge=0.1, le=5.0, description="Channel hop interval")
    interface: str = Field(default="wlan0", description="WiFi interface for scanning")
    use_nexmon: bool = Field(default=True, description="Use Nexmon for monitor mode (Pi Zero 2W)")


class CaptureConfig(BaseModel):
    """Handshake capture configuration."""

    enabled: bool = Field(default=True, description="Enable handshake capture")
    deauth_count: int = Field(default=5, ge=1, le=50, description="Deauth packets per burst")
    deauth_interval: float = Field(default=1.0, ge=0.5, le=10.0, description="Deauth interval")
    timeout: int = Field(default=120, ge=30, le=600, description="Capture timeout (seconds)")
    auto_stop: bool = Field(default=True, description="Stop after successful capture")


class DisplayConfig(BaseModel):
    """e-Paper display configuration."""

    enabled: bool = Field(default=True, description="Enable e-Paper display")
    refresh_interval: int = Field(default=60, ge=10, le=600, description="Refresh interval (sec)")
    show_password: bool = Field(default=False, description="Show AP password on display")
    rotation: int = Field(default=0, description="Display rotation (0, 90, 180, 270)")

    @field_validator("rotation")
    @classmethod
    def validate_rotation(cls, v: int) -> int:
        """Validate rotation."""
        if v not in (0, 90, 180, 270):
            raise ValueError("Rotation must be 0, 90, 180, or 270")
        return v


class PowerConfig(BaseModel):
    """Power management configuration."""

    low_battery_threshold: int = Field(default=15, ge=5, le=50, description="Low battery warning %")
    auto_shutdown: int = Field(default=5, ge=0, le=20, description="Auto shutdown battery %")
    sleep_on_idle: bool = Field(default=False, description="Sleep display when idle")
    idle_timeout: int = Field(default=300, ge=60, le=3600, description="Idle timeout (seconds)")


class NexusConfig(BaseModel):
    """Nexus sync configuration."""

    enabled: bool = Field(default=False, description="Enable Nexus sync")
    url: str = Field(default="http://nexus.local:8080", description="Nexus API URL")
    api_key_env: str = Field(default="NEXUS_API_KEY", description="API key env var")
    sync_on_wifi: bool = Field(default=True, description="Auto-sync when on WiFi")
    sync_interval: int = Field(default=300, ge=60, le=3600, description="Sync interval (seconds)")


class StorageConfig(BaseModel):
    """Storage configuration."""

    data_dir: str = Field(default="/var/momo-shadow/data", description="Data directory")
    captures_dir: str = Field(default="/var/momo-shadow/captures", description="Captures directory")
    max_db_size_mb: int = Field(default=100, ge=10, le=1000, description="Max database size MB")


class ShadowConfig(BaseSettings):
    """
    Main Shadow configuration.

    Configuration is loaded from:
    1. Default values
    2. /boot/shadow.yml (for headless setup)
    3. /etc/momo-shadow/config.yml
    4. Environment variables (prefixed with SHADOW_)
    """

    model_config = SettingsConfigDict(
        env_prefix="SHADOW_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    device: DeviceConfig = Field(default_factory=DeviceConfig)
    ap: APConfig = Field(default_factory=APConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    autostart: AutostartConfig = Field(default_factory=AutostartConfig)
    targets: TargetsConfig = Field(default_factory=TargetsConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    power: PowerConfig = Field(default_factory=PowerConfig)
    nexus: NexusConfig = Field(default_factory=NexusConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> ShadowConfig:
        """Load configuration from YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> ShadowConfig:
        """
        Load configuration with fallback order:
        1. Provided path
        2. SHADOW_CONFIG environment variable
        3. /boot/shadow.yml (headless setup)
        4. /etc/momo-shadow/config.yml
        5. Default values
        """
        # Try provided path
        if config_path:
            return cls.from_yaml(config_path)

        # Try environment variable
        env_path = os.environ.get("SHADOW_CONFIG")
        if env_path and Path(env_path).exists():
            return cls.from_yaml(env_path)

        # Try /boot/shadow.yml (headless setup)
        boot_path = Path("/boot/shadow.yml")
        if boot_path.exists():
            return cls.from_yaml(boot_path)

        # Try /etc/momo-shadow/config.yml
        etc_path = Path("/etc/momo-shadow/config.yml")
        if etc_path.exists():
            return cls.from_yaml(etc_path)

        # Return defaults
        return cls()

    def to_yaml(self, path: str | Path) -> None:
        """Save configuration to YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = self.model_dump()
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    def get_all_channels(self) -> list[int]:
        """Get all channels to scan."""
        return self.scan.channels_2g + self.scan.channels_5g

    def should_target(self, ssid: str, bssid: str) -> bool:
        """Check if network should be targeted."""
        # Check ignore list
        for pattern in self.targets.ignore:
            if pattern.lower() in ssid.lower():
                return False

        # If no targets specified, target all
        if not self.targets.ssids and not self.targets.bssids:
            return True

        # Check SSID targets
        for pattern in self.targets.ssids:
            if pattern.endswith("*"):
                if ssid.lower().startswith(pattern[:-1].lower()):
                    return True
            elif pattern.lower() == ssid.lower():
                return True

        # Check BSSID targets
        if bssid.upper() in [b.upper() for b in self.targets.bssids]:
            return True

        return False

