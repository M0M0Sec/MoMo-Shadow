"""
WiFi Scanner Module

Passive WiFi scanning with scapy.
Captures APs, clients, and probe requests.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


class SecurityType(Enum):
    """WiFi security type."""

    OPEN = "OPEN"
    WEP = "WEP"
    WPA = "WPA"
    WPA2 = "WPA2"
    WPA3 = "WPA3"
    UNKNOWN = "UNKNOWN"


@dataclass
class AccessPoint:
    """Discovered access point."""

    bssid: str
    ssid: str
    channel: int
    signal_dbm: int
    security: SecurityType
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    clients: set[str] = field(default_factory=set)
    beacon_count: int = 0
    hidden: bool = False

    def update(self, signal_dbm: int, channel: int) -> None:
        """Update AP with new observation."""
        self.signal_dbm = signal_dbm
        self.channel = channel
        self.last_seen = datetime.now()
        self.beacon_count += 1


@dataclass
class ProbeRequest:
    """Captured probe request."""

    client_mac: str
    ssid: str
    signal_dbm: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Client:
    """Discovered client."""

    mac: str
    bssid: str | None = None  # Associated AP
    signal_dbm: int = -100
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    probes: list[str] = field(default_factory=list)


class WiFiScanner:
    """
    Passive WiFi scanner.

    Captures:
    - Access points (beacons)
    - Clients (data frames)
    - Probe requests
    """

    def __init__(
        self,
        interface: str = "wlan0",
        on_ap_found: Callable[[AccessPoint], None] | None = None,
        on_probe: Callable[[ProbeRequest], None] | None = None,
        on_client: Callable[[Client], None] | None = None,
    ):
        """
        Initialize scanner.

        Args:
            interface: WiFi interface in monitor mode
            on_ap_found: Callback for new AP discovery
            on_probe: Callback for probe requests
            on_client: Callback for client discovery
        """
        self.interface = interface
        self._on_ap_found = on_ap_found
        self._on_probe = on_probe
        self._on_client = on_client

        self._access_points: dict[str, AccessPoint] = {}
        self._clients: dict[str, Client] = {}
        self._probes: list[ProbeRequest] = []

        self._running = False
        self._scan_task: asyncio.Task | None = None
        self._packet_count = 0
        self._start_time: datetime | None = None

    @property
    def access_points(self) -> list[AccessPoint]:
        """Get discovered access points sorted by signal."""
        return sorted(
            self._access_points.values(),
            key=lambda ap: ap.signal_dbm,
            reverse=True,
        )

    @property
    def clients(self) -> list[Client]:
        """Get discovered clients."""
        return list(self._clients.values())

    @property
    def probes(self) -> list[ProbeRequest]:
        """Get captured probe requests."""
        return self._probes.copy()

    @property
    def stats(self) -> dict:
        """Get scanner statistics."""
        return {
            "aps": len(self._access_points),
            "clients": len(self._clients),
            "probes": len(self._probes),
            "packets": self._packet_count,
            "runtime": (datetime.now() - self._start_time).total_seconds()
            if self._start_time
            else 0,
        }

    def _parse_security(self, packet) -> SecurityType:
        """Parse security type from beacon frame."""
        try:
            # Check for RSN (WPA2/WPA3)
            if packet.haslayer("Dot11EltRSN"):
                rsn = packet.getlayer("Dot11EltRSN")
                # Check for SAE (WPA3)
                if hasattr(rsn, "akm_suites"):
                    for suite in rsn.akm_suites:
                        if suite.suite == 8:  # SAE
                            return SecurityType.WPA3
                return SecurityType.WPA2

            # Check for WPA
            if packet.haslayer("Dot11EltVendorSpecific"):
                return SecurityType.WPA

            # Check capability for WEP
            if packet.haslayer("Dot11Beacon"):
                cap = packet.cap
                if cap & 0x10:  # Privacy bit
                    return SecurityType.WEP

            return SecurityType.OPEN

        except Exception:
            return SecurityType.UNKNOWN

    def _handle_packet(self, packet) -> None:
        """Handle captured packet."""
        self._packet_count += 1

        try:
            # Import here to avoid issues when scapy not available
            from scapy.layers.dot11 import Dot11, Dot11Beacon, Dot11ProbeReq, RadioTap

            if not packet.haslayer(Dot11):
                return

            dot11 = packet.getlayer(Dot11)

            # Get signal strength
            signal_dbm = -100
            if packet.haslayer(RadioTap):
                radiotap = packet.getlayer(RadioTap)
                if hasattr(radiotap, "dBm_AntSignal"):
                    signal_dbm = radiotap.dBm_AntSignal

            # Beacon frame (AP)
            if packet.haslayer(Dot11Beacon):
                self._handle_beacon(packet, signal_dbm)

            # Probe request (Client looking for network)
            elif packet.haslayer(Dot11ProbeReq):
                self._handle_probe_request(packet, signal_dbm)

            # Data frame (Client traffic)
            elif dot11.type == 2:  # Data frame
                self._handle_data_frame(packet, signal_dbm)

        except Exception as e:
            logger.debug(f"Packet handling error: {e}")

    def _handle_beacon(self, packet, signal_dbm: int) -> None:
        """Handle beacon frame."""
        try:
            from scapy.layers.dot11 import Dot11, Dot11Elt

            dot11 = packet.getlayer(Dot11)
            bssid = dot11.addr3

            if not bssid or bssid == "ff:ff:ff:ff:ff:ff":
                return

            # Get SSID
            ssid = ""
            hidden = False
            elt = packet.getlayer(Dot11Elt)
            while elt:
                if elt.ID == 0:  # SSID
                    ssid = elt.info.decode("utf-8", errors="ignore")
                    if not ssid or ssid == "\x00" * len(ssid):
                        hidden = True
                        ssid = f"<hidden_{bssid[-5:].replace(':', '')}>"
                elif elt.ID == 3:  # Channel
                    channel = elt.info[0] if elt.info else 0
                elt = elt.payload.getlayer(Dot11Elt)

            # Get channel from packet if not in IE
            channel = getattr(packet, "Channel", 0) or 0

            # Parse security
            security = self._parse_security(packet)

            # Update or create AP
            if bssid in self._access_points:
                self._access_points[bssid].update(signal_dbm, channel)
            else:
                ap = AccessPoint(
                    bssid=bssid,
                    ssid=ssid,
                    channel=channel,
                    signal_dbm=signal_dbm,
                    security=security,
                    hidden=hidden,
                )
                self._access_points[bssid] = ap
                logger.info(f"New AP: {ssid} ({bssid}) ch{channel} {signal_dbm}dBm")

                if self._on_ap_found:
                    self._on_ap_found(ap)

        except Exception as e:
            logger.debug(f"Beacon handling error: {e}")

    def _handle_probe_request(self, packet, signal_dbm: int) -> None:
        """Handle probe request."""
        try:
            from scapy.layers.dot11 import Dot11, Dot11Elt

            dot11 = packet.getlayer(Dot11)
            client_mac = dot11.addr2

            if not client_mac:
                return

            # Get probed SSID
            ssid = ""
            elt = packet.getlayer(Dot11Elt)
            while elt:
                if elt.ID == 0:  # SSID
                    ssid = elt.info.decode("utf-8", errors="ignore")
                    break
                elt = elt.payload.getlayer(Dot11Elt)

            if ssid:  # Only log directed probes
                probe = ProbeRequest(
                    client_mac=client_mac,
                    ssid=ssid,
                    signal_dbm=signal_dbm,
                )
                self._probes.append(probe)
                logger.debug(f"Probe: {client_mac} -> {ssid}")

                if self._on_probe:
                    self._on_probe(probe)

                # Update client probes
                if client_mac not in self._clients:
                    self._clients[client_mac] = Client(mac=client_mac)
                if ssid not in self._clients[client_mac].probes:
                    self._clients[client_mac].probes.append(ssid)

        except Exception as e:
            logger.debug(f"Probe handling error: {e}")

    def _handle_data_frame(self, packet, signal_dbm: int) -> None:
        """Handle data frame (client traffic)."""
        try:
            from scapy.layers.dot11 import Dot11

            dot11 = packet.getlayer(Dot11)

            # Get addresses based on To/From DS flags
            to_ds = dot11.FCfield & 0x1
            from_ds = dot11.FCfield & 0x2

            client_mac = None
            bssid = None

            if to_ds and not from_ds:  # To AP
                client_mac = dot11.addr2
                bssid = dot11.addr1
            elif from_ds and not to_ds:  # From AP
                client_mac = dot11.addr1
                bssid = dot11.addr2

            if client_mac and bssid:
                # Skip broadcast
                if client_mac == "ff:ff:ff:ff:ff:ff":
                    return

                # Update or create client
                if client_mac in self._clients:
                    self._clients[client_mac].bssid = bssid
                    self._clients[client_mac].signal_dbm = signal_dbm
                    self._clients[client_mac].last_seen = datetime.now()
                else:
                    client = Client(
                        mac=client_mac,
                        bssid=bssid,
                        signal_dbm=signal_dbm,
                    )
                    self._clients[client_mac] = client
                    logger.debug(f"New client: {client_mac} -> {bssid}")

                    if self._on_client:
                        self._on_client(client)

                # Add client to AP
                if bssid in self._access_points:
                    self._access_points[bssid].clients.add(client_mac)

        except Exception as e:
            logger.debug(f"Data frame handling error: {e}")

    async def start(self) -> None:
        """Start scanning."""
        if self._running:
            return

        self._running = True
        self._start_time = datetime.now()
        logger.info(f"Starting WiFi scanner on {self.interface}")

        async def scan_loop() -> None:
            try:
                from scapy.all import sniff

                # Run sniff in thread pool
                loop = asyncio.get_event_loop()
                while self._running:
                    await loop.run_in_executor(
                        None,
                        lambda: sniff(
                            iface=self.interface,
                            prn=self._handle_packet,
                            store=False,
                            timeout=1,
                        ),
                    )
            except ImportError:
                logger.error("scapy not installed - running in mock mode")
                while self._running:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Scan error: {e}")

        self._scan_task = asyncio.create_task(scan_loop())

    async def stop(self) -> None:
        """Stop scanning."""
        self._running = False

        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
            self._scan_task = None

        logger.info("WiFi scanner stopped")

    def get_ap(self, bssid: str) -> AccessPoint | None:
        """Get AP by BSSID."""
        return self._access_points.get(bssid)

    def get_ap_by_ssid(self, ssid: str) -> AccessPoint | None:
        """Get AP by SSID."""
        for ap in self._access_points.values():
            if ap.ssid.lower() == ssid.lower():
                return ap
        return None

    def clear(self) -> None:
        """Clear all discovered data."""
        self._access_points.clear()
        self._clients.clear()
        self._probes.clear()
        self._packet_count = 0

