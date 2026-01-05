"""
Power Management Module

Power control and system management.
"""

from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


class PowerManager:
    """
    System power management.

    Features:
    - System shutdown/reboot
    - WiFi power saving
    - CPU frequency scaling
    """

    def __init__(self):
        """Initialize power manager."""
        self._shutdown_scheduled = False

    async def shutdown(self, delay: int = 0) -> None:
        """
        Shutdown the system.

        Args:
            delay: Delay in seconds before shutdown
        """
        if self._shutdown_scheduled:
            return

        self._shutdown_scheduled = True
        logger.warning(f"System shutdown scheduled in {delay}s")

        if delay > 0:
            await asyncio.sleep(delay)

        try:
            proc = await asyncio.create_subprocess_shell(
                "shutdown -h now",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")
            self._shutdown_scheduled = False

    async def reboot(self, delay: int = 0) -> None:
        """
        Reboot the system.

        Args:
            delay: Delay in seconds before reboot
        """
        if self._shutdown_scheduled:
            return

        self._shutdown_scheduled = True
        logger.warning(f"System reboot scheduled in {delay}s")

        if delay > 0:
            await asyncio.sleep(delay)

        try:
            proc = await asyncio.create_subprocess_shell(
                "shutdown -r now",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        except Exception as e:
            logger.error(f"Reboot failed: {e}")
            self._shutdown_scheduled = False

    async def set_wifi_power_save(self, enabled: bool, interface: str = "wlan0") -> bool:
        """
        Set WiFi power saving mode.

        Args:
            enabled: Enable or disable power saving
            interface: WiFi interface

        Returns:
            True if successful
        """
        mode = "on" if enabled else "off"
        try:
            proc = await asyncio.create_subprocess_exec(
                "iw",
                "dev",
                interface,
                "set",
                "power_save",
                mode,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.warning(f"Power save setting failed: {stderr.decode()}")
                return False

            logger.info(f"WiFi power save: {mode}")
            return True

        except Exception as e:
            logger.error(f"Power save error: {e}")
            return False

    async def set_cpu_governor(self, governor: str = "powersave") -> bool:
        """
        Set CPU frequency governor.

        Args:
            governor: Governor name (powersave, performance, ondemand)

        Returns:
            True if successful
        """
        try:
            gov_path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
            if not os.path.exists(gov_path):
                logger.warning("CPU frequency scaling not available")
                return False

            with open(gov_path, "w") as f:
                f.write(governor)

            logger.info(f"CPU governor set to: {governor}")
            return True

        except PermissionError:
            logger.warning("Permission denied for CPU governor")
            return False
        except Exception as e:
            logger.error(f"CPU governor error: {e}")
            return False

    async def enable_low_power_mode(self) -> None:
        """Enable low power mode for maximum battery life."""
        logger.info("Enabling low power mode")

        # Disable WiFi power save (counterintuitive but needed for monitor mode)
        await self.set_wifi_power_save(False)

        # Set CPU to powersave
        await self.set_cpu_governor("powersave")

        # Disable HDMI
        try:
            await asyncio.create_subprocess_shell(
                "tvservice -o",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except Exception:
            pass

        # Disable activity LED
        try:
            with open("/sys/class/leds/ACT/trigger", "w") as f:
                f.write("none")
            with open("/sys/class/leds/ACT/brightness", "w") as f:
                f.write("0")
        except Exception:
            pass

    async def disable_low_power_mode(self) -> None:
        """Disable low power mode."""
        logger.info("Disabling low power mode")

        # Set CPU to ondemand
        await self.set_cpu_governor("ondemand")

        # Enable HDMI
        try:
            await asyncio.create_subprocess_shell(
                "tvservice -p",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except Exception:
            pass

    @staticmethod
    async def get_cpu_temp() -> float | None:
        """Get CPU temperature in Celsius."""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read().strip()) / 1000.0
                return round(temp, 1)
        except Exception:
            return None

    @staticmethod
    async def get_memory_usage() -> dict:
        """Get memory usage statistics."""
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()

            meminfo = {}
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = int(parts[1].strip().split()[0])
                    meminfo[key] = value

            total = meminfo.get("MemTotal", 0)
            available = meminfo.get("MemAvailable", 0)
            used = total - available
            percent = (used / total * 100) if total > 0 else 0

            return {
                "total_mb": total // 1024,
                "available_mb": available // 1024,
                "used_mb": used // 1024,
                "percent": round(percent, 1),
            }
        except Exception:
            return {"total_mb": 0, "available_mb": 0, "used_mb": 0, "percent": 0}

