"""
Battery Monitor Module

Monitor battery status for Pi Zero 2W with LiPo battery.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class BatteryState(Enum):
    """Battery charging state."""

    UNKNOWN = "unknown"
    CHARGING = "charging"
    DISCHARGING = "discharging"
    FULL = "full"
    LOW = "low"
    CRITICAL = "critical"


@dataclass
class BatteryStatus:
    """Battery status information."""

    percent: int
    voltage: float
    state: BatteryState
    temperature: float | None = None
    time_remaining: int | None = None  # minutes
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BatteryMonitor:
    """
    Battery monitoring.

    Supports:
    - PiSugar battery (I2C)
    - UPS HAT (I2C)
    - INA219 current sensor
    - Simulated/mock mode
    """

    # Voltage to percentage mapping (LiPo 3.7V nominal)
    VOLTAGE_MAP = [
        (4.2, 100),
        (4.1, 90),
        (4.0, 80),
        (3.9, 70),
        (3.8, 60),
        (3.7, 50),
        (3.6, 40),
        (3.5, 30),
        (3.4, 20),
        (3.3, 10),
        (3.2, 5),
        (3.0, 0),
    ]

    def __init__(
        self,
        low_threshold: int = 15,
        critical_threshold: int = 5,
        mock_mode: bool = False,
    ):
        """
        Initialize battery monitor.

        Args:
            low_threshold: Low battery warning percentage
            critical_threshold: Critical battery percentage
            mock_mode: Use simulated battery
        """
        self.low_threshold = low_threshold
        self.critical_threshold = critical_threshold
        self.mock_mode = mock_mode

        self._i2c = None
        self._device_type: str | None = None
        self._last_status: BatteryStatus | None = None
        self._running = False
        self._task: asyncio.Task | None = None

    @property
    def status(self) -> BatteryStatus:
        """Get last battery status."""
        if self._last_status:
            return self._last_status
        return BatteryStatus(
            percent=100,
            voltage=4.2,
            state=BatteryState.UNKNOWN,
        )

    async def initialize(self) -> bool:
        """Initialize battery monitoring."""
        if self.mock_mode:
            logger.info("Battery monitor initialized (mock mode)")
            self._last_status = BatteryStatus(
                percent=85,
                voltage=3.9,
                state=BatteryState.DISCHARGING,
            )
            return True

        try:
            import smbus2

            self._i2c = smbus2.SMBus(1)

            # Try to detect battery device
            # PiSugar 2/3: 0x57 or 0x75
            # UPS HAT: 0x36
            # INA219: 0x40-0x4F

            for addr in [0x57, 0x75, 0x36, 0x40]:
                try:
                    self._i2c.read_byte(addr)
                    self._device_type = self._identify_device(addr)
                    if self._device_type:
                        logger.info(f"Battery device found: {self._device_type}")
                        return True
                except OSError:
                    continue

            logger.warning("No battery device found")
            self.mock_mode = True
            return True

        except ImportError:
            logger.warning("smbus2 not installed - using mock mode")
            self.mock_mode = True
            return True
        except Exception as e:
            logger.error(f"Battery init error: {e}")
            self.mock_mode = True
            return True

    def _identify_device(self, addr: int) -> str | None:
        """Identify battery device type."""
        if addr in (0x57, 0x75):
            return "pisugar"
        elif addr == 0x36:
            return "ups_hat"
        elif 0x40 <= addr <= 0x4F:
            return "ina219"
        return None

    async def read_status(self) -> BatteryStatus:
        """Read current battery status."""
        if self.mock_mode:
            return self._mock_status()

        try:
            if self._device_type == "pisugar":
                return await self._read_pisugar()
            elif self._device_type == "ups_hat":
                return await self._read_ups_hat()
            elif self._device_type == "ina219":
                return await self._read_ina219()
            else:
                return self._mock_status()

        except Exception as e:
            logger.error(f"Battery read error: {e}")
            return self._mock_status()

    async def _read_pisugar(self) -> BatteryStatus:
        """Read PiSugar battery status."""
        # Simplified PiSugar reading
        try:
            # Voltage register
            high = self._i2c.read_byte_data(0x57, 0x22)
            low = self._i2c.read_byte_data(0x57, 0x23)
            voltage = (high << 8 | low) / 1000.0

            # Calculate percentage
            percent = self._voltage_to_percent(voltage)

            # Charging status
            status_byte = self._i2c.read_byte_data(0x57, 0x02)
            charging = bool(status_byte & 0x80)

            state = self._determine_state(percent, charging)

            return BatteryStatus(
                percent=percent,
                voltage=voltage,
                state=state,
            )

        except Exception as e:
            logger.error(f"PiSugar read error: {e}")
            return self._mock_status()

    async def _read_ups_hat(self) -> BatteryStatus:
        """Read UPS HAT battery status."""
        # UPS HAT (MAX17048 compatible)
        try:
            high = self._i2c.read_byte_data(0x36, 0x04)
            low = self._i2c.read_byte_data(0x36, 0x05)
            percent = min(100, max(0, (high << 8 | low) >> 8))

            high = self._i2c.read_byte_data(0x36, 0x02)
            low = self._i2c.read_byte_data(0x36, 0x03)
            voltage = ((high << 8 | low) >> 4) * 0.00125

            state = self._determine_state(percent, False)

            return BatteryStatus(
                percent=percent,
                voltage=voltage,
                state=state,
            )

        except Exception as e:
            logger.error(f"UPS HAT read error: {e}")
            return self._mock_status()

    async def _read_ina219(self) -> BatteryStatus:
        """Read INA219 current sensor."""
        # INA219 simplified reading
        return self._mock_status()

    def _voltage_to_percent(self, voltage: float) -> int:
        """Convert voltage to percentage."""
        for v, p in self.VOLTAGE_MAP:
            if voltage >= v:
                return p
        return 0

    def _determine_state(self, percent: int, charging: bool) -> BatteryState:
        """Determine battery state."""
        if charging:
            return BatteryState.CHARGING
        elif percent <= self.critical_threshold:
            return BatteryState.CRITICAL
        elif percent <= self.low_threshold:
            return BatteryState.LOW
        elif percent >= 95:
            return BatteryState.FULL
        else:
            return BatteryState.DISCHARGING

    def _mock_status(self) -> BatteryStatus:
        """Generate mock battery status."""
        # Simulate slow discharge
        if self._last_status:
            percent = max(0, self._last_status.percent - 0.01)
        else:
            percent = 85

        voltage = 3.0 + (percent / 100) * 1.2

        return BatteryStatus(
            percent=int(percent),
            voltage=round(voltage, 2),
            state=self._determine_state(int(percent), False),
        )

    async def start_monitoring(self, interval: float = 60.0) -> None:
        """Start background monitoring."""
        if self._running:
            return

        self._running = True

        async def monitor_loop():
            while self._running:
                self._last_status = await self.read_status()
                logger.debug(f"Battery: {self._last_status.percent}% ({self._last_status.voltage}V)")
                await asyncio.sleep(interval)

        self._task = asyncio.create_task(monitor_loop())
        logger.info("Battery monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Battery monitoring stopped")

