"""
e-Paper Display Driver

Waveshare 2.13" e-Paper display driver for Pi Zero 2W.
Resolution: 250x122 pixels
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Display constants
DISPLAY_WIDTH = 250
DISPLAY_HEIGHT = 122


class DisplayState(Enum):
    """Display state."""

    OFF = "off"
    IDLE = "idle"
    SCANNING = "scanning"
    CAPTURING = "capturing"
    SUCCESS = "success"
    ERROR = "error"
    LOW_BATTERY = "low_battery"


@dataclass
class DisplayStats:
    """Stats to show on display."""

    state: DisplayState = DisplayState.IDLE
    ap_count: int = 0
    client_count: int = 0
    probe_count: int = 0
    handshake_count: int = 0
    battery_percent: int = 100
    wifi_ap_ssid: str = ""
    wifi_ap_password: str = ""
    target_ssid: str = ""
    uptime_seconds: int = 0
    last_update: datetime | None = None


class EPaperDisplay:
    """
    Waveshare 2.13" e-Paper display driver.

    Features:
    - Low power consumption
    - Outdoor readable
    - Partial refresh support
    """

    def __init__(
        self,
        rotation: int = 0,
        mock_mode: bool = False,
    ):
        """
        Initialize e-Paper display.

        Args:
            rotation: Display rotation (0, 90, 180, 270)
            mock_mode: Use mock display (no hardware)
        """
        self.rotation = rotation
        self.mock_mode = mock_mode

        self._epd = None
        self._initialized = False
        self._stats = DisplayStats()
        self._font_small = None
        self._font_medium = None
        self._font_large = None
        self._font_icon = None

    async def initialize(self) -> bool:
        """Initialize display hardware."""
        if self._initialized:
            return True

        if self.mock_mode:
            logger.info("e-Paper display initialized (mock mode)")
            self._initialized = True
            return True

        try:
            # Import Waveshare library
            from waveshare_epd import epd2in13_V4

            self._epd = epd2in13_V4.EPD()
            self._epd.init()
            self._epd.Clear(0xFF)

            # Load fonts
            await self._load_fonts()

            self._initialized = True
            logger.info("e-Paper display initialized")
            return True

        except ImportError:
            logger.warning("waveshare_epd not installed - using mock mode")
            self.mock_mode = True
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Display init error: {e}")
            return False

    async def _load_fonts(self) -> None:
        """Load fonts for display."""
        try:
            from PIL import ImageFont

            # Try to load custom fonts, fall back to default
            font_dir = Path(__file__).parent / "fonts"

            try:
                self._font_small = ImageFont.truetype(
                    str(font_dir / "DejaVuSansMono.ttf"), 10
                )
                self._font_medium = ImageFont.truetype(
                    str(font_dir / "DejaVuSansMono.ttf"), 12
                )
                self._font_large = ImageFont.truetype(
                    str(font_dir / "DejaVuSansMono-Bold.ttf"), 16
                )
            except (OSError, IOError):
                # Use default fonts
                self._font_small = ImageFont.load_default()
                self._font_medium = ImageFont.load_default()
                self._font_large = ImageFont.load_default()

        except ImportError:
            logger.warning("PIL not installed")

    def update_stats(self, stats: DisplayStats) -> None:
        """Update display statistics."""
        self._stats = stats
        self._stats.last_update = datetime.now()

    async def render(self, full_refresh: bool = False) -> None:
        """
        Render display.

        Args:
            full_refresh: Force full refresh (slower but cleaner)
        """
        if not self._initialized:
            await self.initialize()

        try:
            from PIL import Image, ImageDraw

            # Create image
            image = Image.new("1", (DISPLAY_WIDTH, DISPLAY_HEIGHT), 255)
            draw = ImageDraw.Draw(image)

            # Render based on state
            if self._stats.state == DisplayState.SCANNING:
                self._render_scanning(draw)
            elif self._stats.state == DisplayState.CAPTURING:
                self._render_capturing(draw)
            elif self._stats.state == DisplayState.SUCCESS:
                self._render_success(draw)
            elif self._stats.state == DisplayState.ERROR:
                self._render_error(draw)
            elif self._stats.state == DisplayState.LOW_BATTERY:
                self._render_low_battery(draw)
            else:
                self._render_idle(draw)

            # Apply rotation
            if self.rotation:
                image = image.rotate(self.rotation, expand=True)

            # Display image
            if not self.mock_mode and self._epd:
                if full_refresh:
                    self._epd.init()
                    self._epd.display(self._epd.getbuffer(image))
                else:
                    self._epd.displayPartial(self._epd.getbuffer(image))

            logger.debug("Display rendered")

        except ImportError:
            logger.warning("PIL not installed")
        except Exception as e:
            logger.error(f"Display render error: {e}")

    def _render_header(self, draw: "ImageDraw") -> int:
        """Render header with status. Returns Y offset."""
        font = self._font_medium or None

        # Status bar
        draw.rectangle([0, 0, DISPLAY_WIDTH, 18], fill=0)

        # Title
        draw.text((4, 2), "SHADOW", font=font, fill=255)

        # Battery
        battery_str = f"{self._stats.battery_percent}%"
        draw.text((DISPLAY_WIDTH - 35, 2), battery_str, font=font, fill=255)

        # Battery icon
        bx = DISPLAY_WIDTH - 50
        draw.rectangle([bx, 4, bx + 12, 12], outline=255)
        draw.rectangle([bx + 12, 6, bx + 14, 10], fill=255)
        fill_width = int(10 * self._stats.battery_percent / 100)
        if fill_width > 0:
            draw.rectangle([bx + 1, 5, bx + 1 + fill_width, 11], fill=255)

        return 22

    def _render_idle(self, draw: "ImageDraw") -> None:
        """Render idle screen."""
        y = self._render_header(draw)
        font_s = self._font_small or None
        font_m = self._font_medium or None

        # WiFi AP info
        draw.text((4, y), "WiFi AP:", font=font_s, fill=0)
        draw.text((4, y + 12), self._stats.wifi_ap_ssid or "Not configured", font=font_m, fill=0)

        if self._stats.wifi_ap_password:
            draw.text((4, y + 28), f"Pass: {self._stats.wifi_ap_password}", font=font_s, fill=0)

        # Instructions
        y = 70
        draw.text((4, y), "Connect to WiFi AP", font=font_s, fill=0)
        draw.text((4, y + 12), "Open http://192.168.4.1", font=font_s, fill=0)

        # Uptime
        uptime_str = self._format_uptime(self._stats.uptime_seconds)
        draw.text((4, DISPLAY_HEIGHT - 14), f"Up: {uptime_str}", font=font_s, fill=0)

    def _render_scanning(self, draw: "ImageDraw") -> None:
        """Render scanning screen."""
        y = self._render_header(draw)
        font_s = self._font_small or None
        font_m = self._font_medium or None
        font_l = self._font_large or None

        # Mode
        draw.text((4, y), "MODE: SCANNING", font=font_m, fill=0)

        # Stats
        y += 20
        draw.text((4, y), f"APs: {self._stats.ap_count}", font=font_l, fill=0)
        draw.text((80, y), f"Clients: {self._stats.client_count}", font=font_m, fill=0)

        y += 20
        draw.text((4, y), f"Probes: {self._stats.probe_count}", font=font_m, fill=0)
        draw.text((100, y), f"HS: {self._stats.handshake_count}", font=font_m, fill=0)

        # Animation dots
        dots = "." * ((self._stats.uptime_seconds % 4) + 1)
        draw.text((4, DISPLAY_HEIGHT - 14), f"Scanning{dots}", font=font_s, fill=0)

    def _render_capturing(self, draw: "ImageDraw") -> None:
        """Render capture screen."""
        y = self._render_header(draw)
        font_s = self._font_small or None
        font_m = self._font_medium or None
        font_l = self._font_large or None

        # Mode
        draw.text((4, y), "MODE: CAPTURE", font=font_m, fill=0)

        # Target
        y += 18
        draw.text((4, y), "Target:", font=font_s, fill=0)
        target = self._stats.target_ssid[:20] if self._stats.target_ssid else "None"
        draw.text((4, y + 12), target, font=font_l, fill=0)

        # Progress
        y += 40
        draw.text((4, y), "Waiting for handshake...", font=font_m, fill=0)

        # Progress bar
        y += 16
        draw.rectangle([4, y, DISPLAY_WIDTH - 4, y + 10], outline=0)
        progress = (self._stats.uptime_seconds % 30) / 30
        fill_width = int((DISPLAY_WIDTH - 10) * progress)
        draw.rectangle([5, y + 1, 5 + fill_width, y + 9], fill=0)

    def _render_success(self, draw: "ImageDraw") -> None:
        """Render success screen."""
        y = self._render_header(draw)
        font_s = self._font_small or None
        font_m = self._font_medium or None
        font_l = self._font_large or None

        # Success icon (checkmark)
        cx, cy = DISPLAY_WIDTH // 2, 55
        draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], outline=0, width=2)
        draw.line([cx - 10, cy, cx - 3, cy + 8], fill=0, width=2)
        draw.line([cx - 3, cy + 8, cx + 12, cy - 8], fill=0, width=2)

        # Text
        draw.text((70, 85), "CAPTURED!", font=font_l, fill=0)

        # Target
        target = self._stats.target_ssid[:25] if self._stats.target_ssid else ""
        draw.text((4, DISPLAY_HEIGHT - 14), target, font=font_s, fill=0)

    def _render_error(self, draw: "ImageDraw") -> None:
        """Render error screen."""
        y = self._render_header(draw)
        font_m = self._font_medium or None
        font_l = self._font_large or None

        # Error icon (X)
        cx, cy = DISPLAY_WIDTH // 2, 55
        draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], outline=0, width=2)
        draw.line([cx - 10, cy - 10, cx + 10, cy + 10], fill=0, width=2)
        draw.line([cx - 10, cy + 10, cx + 10, cy - 10], fill=0, width=2)

        draw.text((85, 85), "ERROR", font=font_l, fill=0)

    def _render_low_battery(self, draw: "ImageDraw") -> None:
        """Render low battery warning."""
        font_l = self._font_large or None
        font_m = self._font_medium or None

        # Warning
        draw.text((60, 40), "LOW BATTERY", font=font_l, fill=0)
        draw.text((70, 65), f"{self._stats.battery_percent}%", font=font_l, fill=0)
        draw.text((50, 90), "Shutting down...", font=font_m, fill=0)

    def _format_uptime(self, seconds: int) -> str:
        """Format uptime as string."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    async def clear(self) -> None:
        """Clear display."""
        if self._epd and not self.mock_mode:
            self._epd.init()
            self._epd.Clear(0xFF)
        logger.debug("Display cleared")

    async def sleep(self) -> None:
        """Put display in sleep mode."""
        if self._epd and not self.mock_mode:
            self._epd.sleep()
        logger.info("Display entering sleep mode")

    async def shutdown(self) -> None:
        """Shutdown display."""
        await self.clear()
        await self.sleep()
        self._initialized = False
        logger.info("Display shutdown")

