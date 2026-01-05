"""
WiFi Access Point Module

Creates WiFi AP for device control.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

logger = logging.getLogger(__name__)


class WiFiAP:
    """
    WiFi Access Point manager.

    Creates a hostapd-based AP for device control.
    """

    HOSTAPD_CONF_TEMPLATE = """
interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid={hidden}
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""

    DNSMASQ_CONF_TEMPLATE = """
interface={interface}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
address=/#/192.168.4.1
"""

    def __init__(
        self,
        interface: str = "wlan0",
        ssid: str = "Shadow",
        password: str = "shadowpass123",
        channel: int = 6,
        hidden: bool = False,
    ):
        """
        Initialize WiFi AP.

        Args:
            interface: WiFi interface
            ssid: AP SSID
            password: AP password (min 8 chars)
            channel: WiFi channel
            hidden: Hide SSID
        """
        self.interface = interface
        self.ssid = ssid
        self.password = password
        self.channel = channel
        self.hidden = hidden

        self._hostapd_proc: asyncio.subprocess.Process | None = None
        self._dnsmasq_proc: asyncio.subprocess.Process | None = None
        self._hostapd_conf: Path | None = None
        self._dnsmasq_conf: Path | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if AP is running."""
        return self._running

    @property
    def ip_address(self) -> str:
        """Get AP IP address."""
        return "192.168.4.1"

    async def start(self) -> bool:
        """Start WiFi AP."""
        if self._running:
            logger.warning("AP already running")
            return True

        try:
            # Stop any existing services
            await self._stop_services()

            # Configure interface
            await self._configure_interface()

            # Create config files
            self._create_configs()

            # Start hostapd
            if not await self._start_hostapd():
                return False

            # Start dnsmasq
            if not await self._start_dnsmasq():
                await self._stop_hostapd()
                return False

            self._running = True
            logger.info(f"WiFi AP started: {self.ssid} on {self.interface}")
            return True

        except Exception as e:
            logger.error(f"Failed to start AP: {e}")
            await self.stop()
            return False

    async def stop(self) -> None:
        """Stop WiFi AP."""
        await self._stop_dnsmasq()
        await self._stop_hostapd()
        self._cleanup_configs()
        self._running = False
        logger.info("WiFi AP stopped")

    async def _configure_interface(self) -> None:
        """Configure network interface."""
        # Bring interface down
        await self._run_cmd(f"ip link set {self.interface} down")

        # Set IP address
        await self._run_cmd(f"ip addr flush dev {self.interface}")
        await self._run_cmd(f"ip addr add 192.168.4.1/24 dev {self.interface}")

        # Bring interface up
        await self._run_cmd(f"ip link set {self.interface} up")

        # Enable IP forwarding
        await self._run_cmd("sysctl -w net.ipv4.ip_forward=1")

    def _create_configs(self) -> None:
        """Create configuration files."""
        # Hostapd config
        hostapd_conf = self.HOSTAPD_CONF_TEMPLATE.format(
            interface=self.interface,
            ssid=self.ssid,
            channel=self.channel,
            hidden=1 if self.hidden else 0,
            password=self.password,
        )

        self._hostapd_conf = Path("/tmp/shadow_hostapd.conf")
        self._hostapd_conf.write_text(hostapd_conf)

        # Dnsmasq config
        dnsmasq_conf = self.DNSMASQ_CONF_TEMPLATE.format(interface=self.interface)
        self._dnsmasq_conf = Path("/tmp/shadow_dnsmasq.conf")
        self._dnsmasq_conf.write_text(dnsmasq_conf)

    def _cleanup_configs(self) -> None:
        """Remove configuration files."""
        if self._hostapd_conf and self._hostapd_conf.exists():
            self._hostapd_conf.unlink()
        if self._dnsmasq_conf and self._dnsmasq_conf.exists():
            self._dnsmasq_conf.unlink()

    async def _start_hostapd(self) -> bool:
        """Start hostapd."""
        try:
            self._hostapd_proc = await asyncio.create_subprocess_exec(
                "hostapd",
                str(self._hostapd_conf),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait a bit for hostapd to start
            await asyncio.sleep(2)

            if self._hostapd_proc.returncode is not None:
                stderr = await self._hostapd_proc.stderr.read()
                logger.error(f"hostapd failed: {stderr.decode()}")
                return False

            logger.debug("hostapd started")
            return True

        except FileNotFoundError:
            logger.error("hostapd not found")
            return False
        except Exception as e:
            logger.error(f"hostapd error: {e}")
            return False

    async def _stop_hostapd(self) -> None:
        """Stop hostapd."""
        if self._hostapd_proc:
            self._hostapd_proc.terminate()
            try:
                await asyncio.wait_for(self._hostapd_proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._hostapd_proc.kill()
            self._hostapd_proc = None

    async def _start_dnsmasq(self) -> bool:
        """Start dnsmasq."""
        try:
            self._dnsmasq_proc = await asyncio.create_subprocess_exec(
                "dnsmasq",
                "-C",
                str(self._dnsmasq_conf),
                "-d",  # Don't daemonize
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            await asyncio.sleep(1)

            if self._dnsmasq_proc.returncode is not None:
                stderr = await self._dnsmasq_proc.stderr.read()
                logger.error(f"dnsmasq failed: {stderr.decode()}")
                return False

            logger.debug("dnsmasq started")
            return True

        except FileNotFoundError:
            logger.error("dnsmasq not found")
            return False
        except Exception as e:
            logger.error(f"dnsmasq error: {e}")
            return False

    async def _stop_dnsmasq(self) -> None:
        """Stop dnsmasq."""
        if self._dnsmasq_proc:
            self._dnsmasq_proc.terminate()
            try:
                await asyncio.wait_for(self._dnsmasq_proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._dnsmasq_proc.kill()
            self._dnsmasq_proc = None

    async def _stop_services(self) -> None:
        """Stop any existing hostapd/dnsmasq."""
        await self._run_cmd("killall hostapd", ignore_errors=True)
        await self._run_cmd("killall dnsmasq", ignore_errors=True)
        await asyncio.sleep(1)

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
                logger.warning(f"Command failed: {cmd} - {stderr.decode()}")
                return False

            return True

        except Exception as e:
            if not ignore_errors:
                logger.error(f"Command error: {cmd} - {e}")
            return False

