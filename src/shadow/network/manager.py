"""
Interface Manager Module

Manages WiFi interfaces and monitor mode.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class InterfaceMode(Enum):
    """Interface operation mode."""

    MANAGED = "managed"
    MONITOR = "monitor"
    AP = "ap"


@dataclass
class InterfaceInfo:
    """Interface information."""

    name: str
    mac: str
    mode: InterfaceMode
    channel: int | None = None
    driver: str | None = None
    phy: str | None = None


class InterfaceManager:
    """
    WiFi interface manager.

    Handles monitor mode, channel setting, etc.
    """

    def __init__(self, interface: str = "wlan0"):
        """
        Initialize interface manager.

        Args:
            interface: WiFi interface name
        """
        self.interface = interface
        self._original_mac: str | None = None
        self._original_mode: InterfaceMode | None = None

    async def get_info(self) -> InterfaceInfo | None:
        """Get interface information."""
        try:
            # Get interface details using iw
            proc = await asyncio.create_subprocess_exec(
                "iw",
                "dev",
                self.interface,
                "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode != 0:
                return None

            output = stdout.decode()

            # Parse output
            mode = InterfaceMode.MANAGED
            channel = None
            mac = None

            for line in output.split("\n"):
                line = line.strip()
                if line.startswith("type"):
                    mode_str = line.split()[-1]
                    if mode_str == "monitor":
                        mode = InterfaceMode.MONITOR
                    elif mode_str == "AP":
                        mode = InterfaceMode.AP
                elif line.startswith("channel"):
                    match = re.search(r"channel (\d+)", line)
                    if match:
                        channel = int(match.group(1))
                elif line.startswith("addr"):
                    mac = line.split()[-1]

            return InterfaceInfo(
                name=self.interface,
                mac=mac or "00:00:00:00:00:00",
                mode=mode,
                channel=channel,
            )

        except Exception as e:
            logger.error(f"Failed to get interface info: {e}")
            return None

    async def set_monitor_mode(self) -> bool:
        """
        Set interface to monitor mode.

        Returns:
            True if successful
        """
        try:
            # Get current info
            info = await self.get_info()
            if info:
                self._original_mode = info.mode
                self._original_mac = info.mac

            # Bring interface down
            await self._run_cmd(f"ip link set {self.interface} down")

            # Set monitor mode
            result = await self._run_cmd(f"iw dev {self.interface} set type monitor")

            if not result:
                # Try airmon-ng as fallback
                result = await self._run_cmd(f"airmon-ng start {self.interface}")

            # Bring interface up
            await self._run_cmd(f"ip link set {self.interface} up")

            # Verify
            info = await self.get_info()
            if info and info.mode == InterfaceMode.MONITOR:
                logger.info(f"{self.interface} set to monitor mode")
                return True

            logger.error("Failed to set monitor mode")
            return False

        except Exception as e:
            logger.error(f"Monitor mode error: {e}")
            return False

    async def set_managed_mode(self) -> bool:
        """
        Set interface to managed mode.

        Returns:
            True if successful
        """
        try:
            # Bring interface down
            await self._run_cmd(f"ip link set {self.interface} down")

            # Set managed mode
            await self._run_cmd(f"iw dev {self.interface} set type managed")

            # Bring interface up
            await self._run_cmd(f"ip link set {self.interface} up")

            logger.info(f"{self.interface} set to managed mode")
            return True

        except Exception as e:
            logger.error(f"Managed mode error: {e}")
            return False

    async def set_channel(self, channel: int) -> bool:
        """
        Set interface channel.

        Args:
            channel: WiFi channel

        Returns:
            True if successful
        """
        try:
            result = await self._run_cmd(
                f"iw dev {self.interface} set channel {channel}"
            )
            if result:
                logger.debug(f"{self.interface} set to channel {channel}")
            return result

        except Exception as e:
            logger.error(f"Channel set error: {e}")
            return False

    async def set_mac(self, mac: str) -> bool:
        """
        Set interface MAC address.

        Args:
            mac: New MAC address

        Returns:
            True if successful
        """
        try:
            # Bring interface down
            await self._run_cmd(f"ip link set {self.interface} down")

            # Set MAC
            result = await self._run_cmd(
                f"ip link set {self.interface} address {mac}"
            )

            # Bring interface up
            await self._run_cmd(f"ip link set {self.interface} up")

            if result:
                logger.info(f"{self.interface} MAC set to {mac}")

            return result

        except Exception as e:
            logger.error(f"MAC set error: {e}")
            return False

    async def randomize_mac(self) -> str | None:
        """
        Randomize MAC address.

        Returns:
            New MAC address or None on failure
        """
        import random

        # Generate random MAC (locally administered)
        mac = [
            random.randint(0x00, 0xFF) | 0x02,  # Set locally administered bit
            random.randint(0x00, 0xFF),
            random.randint(0x00, 0xFF),
            random.randint(0x00, 0xFF),
            random.randint(0x00, 0xFF),
            random.randint(0x00, 0xFF),
        ]
        mac_str = ":".join(f"{b:02x}" for b in mac)

        if await self.set_mac(mac_str):
            return mac_str
        return None

    async def restore_mac(self) -> bool:
        """Restore original MAC address."""
        if self._original_mac:
            return await self.set_mac(self._original_mac)
        return False

    async def restore_mode(self) -> bool:
        """Restore original interface mode."""
        if self._original_mode == InterfaceMode.MANAGED:
            return await self.set_managed_mode()
        return True

    async def _run_cmd(self, cmd: str) -> bool:
        """Run shell command."""
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.debug(f"Command failed: {cmd} - {stderr.decode()}")
                return False

            return True

        except Exception as e:
            logger.error(f"Command error: {cmd} - {e}")
            return False

    @staticmethod
    async def list_interfaces() -> list[str]:
        """List available WiFi interfaces."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "iw",
                "dev",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            interfaces = []
            for line in stdout.decode().split("\n"):
                if "Interface" in line:
                    iface = line.strip().split()[-1]
                    interfaces.append(iface)

            return interfaces

        except Exception as e:
            logger.error(f"List interfaces error: {e}")
            return []

