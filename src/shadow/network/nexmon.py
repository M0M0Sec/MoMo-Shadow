"""
Nexmon Interface Manager

Manages Nexmon-patched WiFi for monitor mode on Pi Zero 2W.
Single interface switches between AP mode and Monitor mode.
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class WiFiMode(Enum):
    """WiFi interface mode."""

    MANAGED = "managed"
    MONITOR = "monitor"
    AP = "ap"


class NexmonManager:
    """
    Nexmon WiFi manager for Pi Zero 2W.

    Handles mode switching between AP and Monitor mode
    on the single internal WiFi interface.
    """

    def __init__(self, interface: str = "wlan0"):
        """
        Initialize Nexmon manager.

        Args:
            interface: WiFi interface name (usually wlan0)
        """
        self.interface = interface
        self._current_mode: WiFiMode = WiFiMode.MANAGED
        self._monitor_interface: str | None = None

    @property
    def current_mode(self) -> WiFiMode:
        """Get current WiFi mode."""
        return self._current_mode

    @property
    def monitor_interface(self) -> str:
        """Get monitor mode interface name."""
        return self._monitor_interface or f"{self.interface}mon"

    async def check_nexmon(self) -> bool:
        """
        Check if Nexmon is installed and working.

        Returns:
            True if Nexmon is available
        """
        try:
            # Check for nexutil
            proc = await asyncio.create_subprocess_exec(
                "which", "nexutil",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode != 0:
                logger.warning("nexutil not found - Nexmon may not be installed")
                return False

            # Check Nexmon firmware
            proc = await asyncio.create_subprocess_exec(
                "nexutil", "-v",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            if b"nexmon" in stdout.lower() or proc.returncode == 0:
                logger.info("Nexmon detected")
                return True

            return False

        except Exception as e:
            logger.error(f"Nexmon check failed: {e}")
            return False

    async def set_monitor_mode(self) -> bool:
        """
        Switch interface to monitor mode.

        Returns:
            True if successful
        """
        logger.info(f"Switching {self.interface} to monitor mode...")

        try:
            # Stop any services using WiFi
            await self._stop_wifi_services()

            # Method 1: Use airmon-ng (preferred)
            if await self._airmon_start():
                self._current_mode = WiFiMode.MONITOR
                return True

            # Method 2: Use iw directly
            if await self._iw_monitor():
                self._current_mode = WiFiMode.MONITOR
                return True

            # Method 3: Nexmon-specific
            if await self._nexmon_monitor():
                self._current_mode = WiFiMode.MONITOR
                return True

            logger.error("Failed to set monitor mode")
            return False

        except Exception as e:
            logger.error(f"Monitor mode error: {e}")
            return False

    async def set_managed_mode(self) -> bool:
        """
        Switch interface back to managed mode.

        Returns:
            True if successful
        """
        logger.info(f"Switching to managed mode...")

        try:
            # Stop monitor mode
            if self._monitor_interface:
                await self._run_cmd(f"airmon-ng stop {self._monitor_interface}")
                self._monitor_interface = None

            # Bring down interface
            await self._run_cmd(f"ip link set {self.interface} down")

            # Set managed mode
            await self._run_cmd(f"iw dev {self.interface} set type managed")

            # Bring up interface
            await self._run_cmd(f"ip link set {self.interface} up")

            # Restart WiFi services
            await self._start_wifi_services()

            self._current_mode = WiFiMode.MANAGED
            logger.info("Switched to managed mode")
            return True

        except Exception as e:
            logger.error(f"Managed mode error: {e}")
            return False

    async def _airmon_start(self) -> bool:
        """Start monitor mode using airmon-ng."""
        try:
            # Kill interfering processes
            await self._run_cmd("airmon-ng check kill")

            # Start monitor mode
            proc = await asyncio.create_subprocess_exec(
                "airmon-ng", "start", self.interface,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode() + stderr.decode()

            # Parse output for monitor interface name
            if "monitor mode" in output.lower() or "enabled" in output.lower():
                # Check for new interface
                for suffix in ["mon", "0mon", ""]:
                    test_iface = f"{self.interface}{suffix}"
                    if await self._interface_exists(test_iface):
                        self._monitor_interface = test_iface
                        logger.info(f"Monitor mode enabled on {test_iface}")
                        return True

            return False

        except FileNotFoundError:
            logger.debug("airmon-ng not found")
            return False

    async def _iw_monitor(self) -> bool:
        """Start monitor mode using iw."""
        try:
            # Bring down interface
            await self._run_cmd(f"ip link set {self.interface} down")

            # Set monitor mode
            result = await self._run_cmd(f"iw dev {self.interface} set type monitor")

            if not result:
                return False

            # Bring up interface
            await self._run_cmd(f"ip link set {self.interface} up")

            self._monitor_interface = self.interface
            logger.info(f"Monitor mode enabled on {self.interface} (iw)")
            return True

        except Exception as e:
            logger.debug(f"iw monitor failed: {e}")
            return False

    async def _nexmon_monitor(self) -> bool:
        """Start monitor mode using Nexmon-specific commands."""
        try:
            # Nexmon uses nexutil to enable monitor mode
            # This enables the monitor mode bits in the firmware

            # Bring down interface
            await self._run_cmd(f"ip link set {self.interface} down")

            # Enable monitor mode via nexutil
            proc = await asyncio.create_subprocess_exec(
                "nexutil", "-m2",  # Monitor mode
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            # Set interface type
            await self._run_cmd(f"iw dev {self.interface} set type monitor")

            # Bring up interface
            await self._run_cmd(f"ip link set {self.interface} up")

            # Verify
            if await self._is_monitor_mode():
                self._monitor_interface = self.interface
                logger.info(f"Monitor mode enabled via Nexmon")
                return True

            return False

        except FileNotFoundError:
            logger.debug("nexutil not found")
            return False

    async def _is_monitor_mode(self) -> bool:
        """Check if interface is in monitor mode."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "iw", "dev", self.interface, "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            return b"type monitor" in stdout

        except Exception:
            return False

    async def _interface_exists(self, iface: str) -> bool:
        """Check if interface exists."""
        return Path(f"/sys/class/net/{iface}").exists()

    async def _stop_wifi_services(self) -> None:
        """Stop services that use WiFi."""
        services = ["wpa_supplicant", "hostapd", "dnsmasq", "NetworkManager"]

        for service in services:
            await self._run_cmd(f"systemctl stop {service}", ignore_errors=True)
            await self._run_cmd(f"killall {service}", ignore_errors=True)

        await asyncio.sleep(1)

    async def _start_wifi_services(self) -> None:
        """Start WiFi services."""
        await self._run_cmd("systemctl start wpa_supplicant", ignore_errors=True)

    async def _run_cmd(self, cmd: str, ignore_errors: bool = False) -> bool:
        """Run shell command."""
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0 and not ignore_errors:
                logger.debug(f"Command failed: {cmd}")
                return False

            return True

        except Exception as e:
            if not ignore_errors:
                logger.error(f"Command error: {e}")
            return False

    async def set_channel(self, channel: int) -> bool:
        """Set WiFi channel."""
        iface = self._monitor_interface or self.interface

        try:
            result = await self._run_cmd(f"iw dev {iface} set channel {channel}")

            if result:
                logger.debug(f"Channel set to {channel}")

            return result

        except Exception as e:
            logger.error(f"Channel set error: {e}")
            return False

