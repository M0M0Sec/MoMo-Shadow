"""
MoMo-Shadow Main Orchestrator

Coordinates all components for stealth recon operations.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from shadow.config import ShadowConfig
from shadow.core.scanner import WiFiScanner, AccessPoint, ProbeRequest
from shadow.core.capture import CaptureEngine, Handshake
from shadow.core.deauth import DeauthAttack
from shadow.core.hopper import ChannelHopper
from shadow.ui.epaper import EPaperDisplay, DisplayState, DisplayStats
from shadow.network.ap import WiFiAP
from shadow.network.manager import InterfaceManager
from shadow.network.nexmon import NexmonManager, WiFiMode
from shadow.storage.database import Database
from shadow.hardware.battery import BatteryMonitor, BatteryState
from shadow.hardware.power import PowerManager

logger = logging.getLogger(__name__)


class ShadowState(Enum):
    """Shadow operation state."""

    INITIALIZING = "initializing"
    SETUP = "setup"  # AP mode for configuration
    IDLE = "idle"
    SCANNING = "scanning"
    CAPTURING = "capturing"
    STOPPED = "stopped"
    ERROR = "error"


class ShadowOrchestrator:
    """
    Main Shadow orchestrator.

    Coordinates:
    - WiFi scanning
    - Handshake capture
    - Display updates
    - Web UI
    - Battery monitoring
    """

    def __init__(self, config: ShadowConfig | None = None):
        """
        Initialize orchestrator.

        Args:
            config: Shadow configuration
        """
        self.config = config or ShadowConfig.load()

        # State
        self._state = ShadowState.INITIALIZING
        self._mode = self.config.autostart.mode
        self._start_time = datetime.now()
        self._target_bssid: str | None = None
        self._target_ssid: str | None = None
        self._handshakes: list[Handshake] = []

        # Components
        self.scanner: WiFiScanner | None = None
        self.capture_engine: CaptureEngine | None = None
        self.deauth: DeauthAttack | None = None
        self.hopper: ChannelHopper | None = None
        self.display: EPaperDisplay | None = None
        self.wifi_ap: WiFiAP | None = None
        self.interface_mgr: InterfaceManager | None = None
        self.nexmon: NexmonManager | None = None
        self.database: Database | None = None
        self.battery: BatteryMonitor | None = None
        self.power: PowerManager | None = None

        # Single interface mode (Nexmon)
        self._use_nexmon = self.config.scan.use_nexmon
        self._setup_mode = False
        self._setup_timeout_task: asyncio.Task | None = None

        # Tasks
        self._main_task: asyncio.Task | None = None
        self._display_task: asyncio.Task | None = None
        self._running = False

        # AP SSID (generated once)
        self._ap_ssid: str | None = None

    @property
    def state(self) -> ShadowState:
        """Get current state."""
        return self._state

    @property
    def mode(self) -> str:
        """Get current operation mode."""
        return self._mode

    @property
    def uptime(self) -> int:
        """Get uptime in seconds."""
        return int((datetime.now() - self._start_time).total_seconds())

    @property
    def handshake_count(self) -> int:
        """Get number of captured handshakes."""
        return len(self._handshakes)

    @property
    def handshakes(self) -> list[Handshake]:
        """Get captured handshakes."""
        return self._handshakes.copy()

    @property
    def battery_percent(self) -> int:
        """Get battery percentage."""
        if self.battery:
            return self.battery.status.percent
        return 100

    @property
    def target_ssid(self) -> str | None:
        """Get current target SSID."""
        return self._target_ssid

    async def initialize(self) -> bool:
        """Initialize all components."""
        logger.info("Initializing MoMo-Shadow...")
        logger.info(f"Mode: {'Nexmon (single interface)' if self._use_nexmon else 'Dual interface'}")

        try:
            # Power manager
            self.power = PowerManager()

            # Database
            self.database = Database(self.config.storage.data_dir + "/shadow.db")
            await self.database.initialize()

            # Battery monitor
            self.battery = BatteryMonitor(
                low_threshold=self.config.power.low_battery_threshold,
                critical_threshold=self.config.power.auto_shutdown,
            )
            await self.battery.initialize()
            await self.battery.start_monitoring()

            # Nexmon manager (for single interface mode)
            if self._use_nexmon:
                self.nexmon = NexmonManager(self.config.scan.interface)
                has_nexmon = await self.nexmon.check_nexmon()
                if not has_nexmon:
                    logger.warning("Nexmon not detected - monitor mode may not work")

            # Interface manager
            self.interface_mgr = InterfaceManager(self.config.scan.interface)

            # e-Paper display
            if self.config.display.enabled:
                self.display = EPaperDisplay(
                    rotation=self.config.display.rotation,
                )
                await self.display.initialize()

            # Start in SETUP mode (AP mode for configuration)
            if self.config.ap.enabled:
                await self._enter_setup_mode()
            else:
                # Skip setup, go directly to scanning
                await self._enter_monitor_mode()

            logger.info("Shadow initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            self._state = ShadowState.ERROR
            return False

    async def _enter_setup_mode(self) -> None:
        """Enter setup mode (AP mode for Web UI configuration)."""
        logger.info("Entering SETUP mode (AP mode)...")
        self._state = ShadowState.SETUP
        self._setup_mode = True

        # Generate AP SSID
        self._ap_ssid = self.config.ap.get_ssid()

        # Start WiFi AP
        self.wifi_ap = WiFiAP(
            interface=self.config.scan.interface,
            ssid=self._ap_ssid,
            password=self.config.ap.password,
            channel=self.config.ap.channel,
            hidden=self.config.ap.hidden,
        )
        await self.wifi_ap.start()

        logger.info(f"WiFi AP started: {self._ap_ssid}")
        logger.info(f"Connect and open http://192.168.4.1")
        logger.info(f"Auto-switching to monitor mode in {self.config.ap.setup_timeout}s...")

        # Start timeout for auto-switch to monitor mode
        self._setup_timeout_task = asyncio.create_task(
            self._setup_timeout_handler()
        )

    async def _setup_timeout_handler(self) -> None:
        """Handle setup timeout - auto switch to monitor mode."""
        await asyncio.sleep(self.config.ap.setup_timeout)

        if self._setup_mode:
            logger.info("Setup timeout - switching to monitor mode")
            await self.start_scanning()

    async def _enter_monitor_mode(self) -> None:
        """Enter monitor mode for scanning."""
        logger.info("Entering MONITOR mode...")

        # Stop AP if running
        if self.wifi_ap and self.wifi_ap.is_running:
            await self.wifi_ap.stop()
            self.wifi_ap = None

        self._setup_mode = False

        # Cancel setup timeout
        if self._setup_timeout_task:
            self._setup_timeout_task.cancel()
            self._setup_timeout_task = None

        # Switch to monitor mode
        if self._use_nexmon and self.nexmon:
            success = await self.nexmon.set_monitor_mode()
            if not success:
                logger.error("Failed to enable monitor mode")
                self._state = ShadowState.ERROR
                return

            monitor_iface = self.nexmon.monitor_interface
        else:
            # Use interface manager for external adapter
            success = await self.interface_mgr.set_monitor_mode()
            if not success:
                logger.warning("Monitor mode failed - scanning may not work")

            monitor_iface = self.config.scan.interface

        # Initialize scanner with monitor interface
        self.scanner = WiFiScanner(
            interface=monitor_iface,
            on_ap_found=self._on_ap_found,
            on_probe=self._on_probe,
        )

        # Capture engine
        self.capture_engine = CaptureEngine(
            interface=monitor_iface,
            captures_dir=self.config.storage.captures_dir,
            on_handshake=self._on_handshake,
        )

        # Deauth
        self.deauth = DeauthAttack(interface=monitor_iface)

        # Channel hopper
        self.hopper = ChannelHopper(
            interface=monitor_iface,
            channels=self.config.get_all_channels(),
            interval=self.config.scan.hop_interval,
        )

        self._state = ShadowState.IDLE
        logger.info(f"Monitor mode ready on {monitor_iface}")

    async def return_to_setup(self) -> None:
        """Return to setup mode (AP mode) for configuration."""
        logger.info("Returning to SETUP mode...")

        # Stop scanning
        if self.scanner:
            await self.scanner.stop()
        if self.hopper:
            await self.hopper.stop()

        # Switch back to managed mode
        if self._use_nexmon and self.nexmon:
            await self.nexmon.set_managed_mode()
        elif self.interface_mgr:
            await self.interface_mgr.set_managed_mode()

        # Enter setup mode
        await self._enter_setup_mode()

    async def start_scanning(self) -> None:
        """Start WiFi scanning (switches to monitor mode if in setup)."""
        if self._setup_mode:
            await self._enter_monitor_mode()

        await self._start_scanning()

    async def start(self) -> None:
        """Start Shadow operation."""
        if self._running:
            return

        self._running = True
        logger.info(f"Starting Shadow in {self._mode} mode")

        # Set interface to monitor mode
        if not await self.interface_mgr.set_monitor_mode():
            logger.warning("Failed to set monitor mode - scanning may not work")

        # Start based on mode
        if self._mode in ("passive", "capture"):
            await self._start_scanning()
        elif self._mode == "drop":
            await self._start_drop_mode()

        # Start display updates
        if self.display:
            self._display_task = asyncio.create_task(self._display_loop())

        # Main loop
        self._main_task = asyncio.create_task(self._main_loop())

    async def stop(self) -> None:
        """Stop Shadow operation."""
        logger.info("Stopping Shadow...")
        self._running = False

        # Stop components
        if self.scanner:
            await self.scanner.stop()
        if self.capture_engine:
            await self.capture_engine.stop_capture()
        if self.hopper:
            await self.hopper.stop()
        if self.battery:
            await self.battery.stop_monitoring()

        # Cancel tasks
        if self._main_task:
            self._main_task.cancel()
        if self._display_task:
            self._display_task.cancel()

        # Restore interface
        if self.interface_mgr:
            await self.interface_mgr.restore_mode()

        # Close database
        if self.database:
            await self.database.close()

        self._state = ShadowState.STOPPED
        logger.info("Shadow stopped")

    async def shutdown(self) -> None:
        """Shutdown device."""
        await self.stop()

        # Clear display
        if self.display:
            await self.display.shutdown()

        # Stop WiFi AP
        if self.wifi_ap:
            await self.wifi_ap.stop()

        # Shutdown
        if self.power:
            await self.power.shutdown(delay=2)

    async def reboot(self) -> None:
        """Reboot device."""
        await self.stop()

        if self.power:
            await self.power.reboot(delay=2)

    async def set_mode(self, mode: str) -> None:
        """
        Change operation mode.

        Args:
            mode: New mode (passive, capture, drop)
        """
        if mode == self._mode:
            return

        logger.info(f"Changing mode: {self._mode} -> {mode}")
        self._mode = mode

        # Stop current operation
        if self.scanner:
            await self.scanner.stop()
        if self.capture_engine:
            await self.capture_engine.stop_capture()
        if self.hopper:
            await self.hopper.stop()

        # Start new mode
        if mode in ("passive", "capture"):
            await self._start_scanning()
        elif mode == "drop":
            await self._start_drop_mode()

    async def set_target(self, bssid: str, ssid: str) -> None:
        """
        Set capture target.

        Args:
            bssid: Target BSSID
            ssid: Target SSID
        """
        self._target_bssid = bssid.lower()
        self._target_ssid = ssid
        logger.info(f"Target set: {ssid} ({bssid})")

    async def start_capture(self) -> bool:
        """Start handshake capture for current target."""
        if not self._target_bssid or not self._target_ssid:
            logger.warning("No target set")
            return False

        # Get target channel
        ap = self.scanner.get_ap(self._target_bssid) if self.scanner else None
        channel = ap.channel if ap else None

        # Stop hopping and stay on target channel
        if self.hopper and channel:
            await self.hopper.stop()
            await self.hopper.set_channel(channel)

        # Start capture
        self._state = ShadowState.CAPTURING
        return await self.capture_engine.start_capture(
            self._target_bssid,
            self._target_ssid,
            timeout=self.config.capture.timeout,
            channel=channel,
        )

    async def stop_capture(self) -> None:
        """Stop handshake capture."""
        if self.capture_engine:
            await self.capture_engine.stop_capture()

        # Resume hopping
        if self.hopper:
            await self.hopper.start()

        self._state = ShadowState.SCANNING

    async def send_deauth(self, bssid: str, client: str | None = None) -> None:
        """
        Send deauth packets.

        Args:
            bssid: Target AP BSSID
            client: Target client MAC (optional)
        """
        if self.deauth:
            await self.deauth.send_deauth(
                bssid,
                client,
                count=self.config.capture.deauth_count,
            )

    async def _start_scanning(self) -> None:
        """Start passive scanning."""
        self._state = ShadowState.SCANNING

        if self.scanner:
            await self.scanner.start()
        if self.hopper:
            await self.hopper.start()

    async def _start_drop_mode(self) -> None:
        """Start drop mode (minimal power, silent logging)."""
        self._state = ShadowState.SCANNING

        # Enable low power mode
        if self.power:
            await self.power.enable_low_power_mode()

        # Disable display
        if self.display:
            await self.display.sleep()

        # Start scanning
        if self.scanner:
            await self.scanner.start()
        if self.hopper:
            await self.hopper.start()

    async def _main_loop(self) -> None:
        """Main operation loop."""
        while self._running:
            try:
                # Check battery
                if self.battery:
                    status = self.battery.status
                    if status.state == BatteryState.CRITICAL:
                        logger.warning("Critical battery - shutting down")
                        await self.shutdown()
                        return

                # Auto-capture mode
                if self._mode == "capture" and self._target_bssid:
                    if self.capture_engine and self.capture_engine.state.value == "success":
                        if self.config.capture.auto_stop:
                            logger.info("Capture successful - stopping")
                            await self.stop_capture()

                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(5)

    async def _display_loop(self) -> None:
        """Display update loop."""
        while self._running:
            try:
                # Update display stats
                stats = DisplayStats(
                    state=self._get_display_state(),
                    ap_count=len(self.scanner.access_points) if self.scanner else 0,
                    client_count=len(self.scanner.clients) if self.scanner else 0,
                    probe_count=len(self.scanner.probes) if self.scanner else 0,
                    handshake_count=self.handshake_count,
                    battery_percent=self.battery_percent,
                    wifi_ap_ssid=self._ap_ssid or "",
                    wifi_ap_password=self.config.ap.password if self.config.display.show_password else "",
                    target_ssid=self._target_ssid or "",
                    uptime_seconds=self.uptime,
                )

                self.display.update_stats(stats)
                await self.display.render()

                await asyncio.sleep(self.config.display.refresh_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Display loop error: {e}")
                await asyncio.sleep(30)

    def _get_display_state(self) -> DisplayState:
        """Get display state from shadow state."""
        if self.battery and self.battery.status.state in (BatteryState.LOW, BatteryState.CRITICAL):
            return DisplayState.LOW_BATTERY
        elif self._state == ShadowState.CAPTURING:
            return DisplayState.CAPTURING
        elif self._state == ShadowState.SCANNING:
            return DisplayState.SCANNING
        elif self._state == ShadowState.ERROR:
            return DisplayState.ERROR
        else:
            return DisplayState.IDLE

    def _on_ap_found(self, ap: AccessPoint) -> None:
        """Handle new AP discovery."""
        logger.debug(f"New AP: {ap.ssid}")

        # Store in database
        if self.database:
            asyncio.create_task(
                self.database.upsert_ap(
                    ap.bssid,
                    ap.ssid,
                    ap.channel,
                    ap.signal_dbm,
                    ap.security.value,
                    ap.hidden,
                )
            )

    def _on_probe(self, probe: ProbeRequest) -> None:
        """Handle probe request."""
        logger.debug(f"Probe: {probe.client_mac} -> {probe.ssid}")

        if self.database:
            asyncio.create_task(
                self.database.add_probe(
                    probe.client_mac,
                    probe.ssid,
                    probe.signal_dbm,
                )
            )

    def _on_handshake(self, handshake: Handshake) -> None:
        """Handle captured handshake."""
        logger.info(f"Handshake captured: {handshake.ssid}")
        self._handshakes.append(handshake)

        # Store in database
        if self.database:
            asyncio.create_task(
                self.database.add_handshake(
                    handshake.bssid,
                    handshake.ssid,
                    handshake.client_mac,
                    handshake.capture_type.value,
                    handshake.pcap_path,
                    handshake.hashcat_hash,
                )
            )


async def run_shadow(config_path: str | None = None) -> None:
    """
    Run Shadow application.

    Args:
        config_path: Path to config file
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Load config
    config = ShadowConfig.load(config_path)

    # Create orchestrator
    shadow = ShadowOrchestrator(config)

    # Signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(shadow.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        # Initialize
        if not await shadow.initialize():
            logger.error("Failed to initialize")
            return

        # Start
        await shadow.start()

        # Wait for shutdown
        while shadow.state != ShadowState.STOPPED:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Shadow error: {e}")
    finally:
        await shadow.stop()


if __name__ == "__main__":
    asyncio.run(run_shadow())

