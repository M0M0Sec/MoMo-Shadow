"""
Handshake Capture Module

Captures WPA2/WPA3 4-way handshakes and PMKID.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class CaptureType(Enum):
    """Type of captured credential."""

    HANDSHAKE = "handshake"
    PMKID = "pmkid"


class CaptureState(Enum):
    """Capture state."""

    IDLE = "idle"
    WAITING = "waiting"
    CAPTURING = "capturing"
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class Handshake:
    """Captured handshake data."""

    bssid: str
    ssid: str
    client_mac: str
    capture_type: CaptureType
    timestamp: datetime = field(default_factory=datetime.now)
    pcap_path: str | None = None
    hashcat_hash: str | None = None
    messages: list[int] = field(default_factory=list)  # EAPOL messages captured

    @property
    def is_complete(self) -> bool:
        """Check if handshake is complete (has messages 1-4 or PMKID)."""
        if self.capture_type == CaptureType.PMKID:
            return True
        # Need at least messages 1,2 or 2,3 for cracking
        return len(self.messages) >= 2 and (
            (1 in self.messages and 2 in self.messages)
            or (2 in self.messages and 3 in self.messages)
        )

    def to_hashcat(self) -> str | None:
        """Convert to hashcat format."""
        return self.hashcat_hash


@dataclass
class CaptureStats:
    """Capture statistics."""

    target_bssid: str
    target_ssid: str
    start_time: datetime
    end_time: datetime | None = None
    state: CaptureState = CaptureState.IDLE
    eapol_count: int = 0
    deauth_sent: int = 0
    handshakes: list[Handshake] = field(default_factory=list)


class CaptureEngine:
    """
    Handshake capture engine.

    Captures EAPOL frames and extracts handshakes/PMKID.
    """

    def __init__(
        self,
        interface: str,
        captures_dir: str = "/var/shadow/captures",
        on_handshake: Callable[[Handshake], None] | None = None,
    ):
        """
        Initialize capture engine.

        Args:
            interface: WiFi interface in monitor mode
            captures_dir: Directory to save captures
            on_handshake: Callback when handshake captured
        """
        self.interface = interface
        self.captures_dir = Path(captures_dir)
        self._on_handshake = on_handshake

        self._running = False
        self._capture_task: asyncio.Task | None = None
        self._current_target: tuple[str, str] | None = None  # (bssid, ssid)
        self._stats: CaptureStats | None = None

        # EAPOL tracking
        self._eapol_frames: dict[str, dict] = {}  # client_mac -> {msg_num: frame}

        # Ensure captures directory exists
        self.captures_dir.mkdir(parents=True, exist_ok=True)

    @property
    def state(self) -> CaptureState:
        """Get current capture state."""
        return self._stats.state if self._stats else CaptureState.IDLE

    @property
    def stats(self) -> CaptureStats | None:
        """Get capture statistics."""
        return self._stats

    async def start_capture(
        self,
        bssid: str,
        ssid: str,
        timeout: int = 120,
        channel: int | None = None,
    ) -> bool:
        """
        Start capturing handshakes for target AP.

        Args:
            bssid: Target AP BSSID
            ssid: Target AP SSID
            timeout: Capture timeout in seconds
            channel: Channel to capture on

        Returns:
            True if capture started successfully
        """
        if self._running:
            logger.warning("Capture already in progress")
            return False

        self._current_target = (bssid.lower(), ssid)
        self._stats = CaptureStats(
            target_bssid=bssid,
            target_ssid=ssid,
            start_time=datetime.now(),
            state=CaptureState.WAITING,
        )
        self._eapol_frames.clear()
        self._running = True

        logger.info(f"Starting capture for {ssid} ({bssid})")

        async def capture_loop() -> None:
            try:
                from scapy.all import sniff

                start_time = asyncio.get_event_loop().time()
                loop = asyncio.get_event_loop()

                while self._running:
                    # Check timeout
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed >= timeout:
                        logger.info("Capture timeout reached")
                        self._stats.state = CaptureState.TIMEOUT
                        break

                    # Sniff for EAPOL frames
                    await loop.run_in_executor(
                        None,
                        lambda: sniff(
                            iface=self.interface,
                            prn=self._handle_packet,
                            store=False,
                            timeout=1,
                            filter="ether proto 0x888e",  # EAPOL
                        ),
                    )

                    # Check if we have complete handshake
                    if self._stats.handshakes:
                        for hs in self._stats.handshakes:
                            if hs.is_complete:
                                logger.info(f"Complete handshake captured!")
                                self._stats.state = CaptureState.SUCCESS
                                self._running = False
                                break

            except ImportError:
                logger.error("scapy not installed")
                self._stats.state = CaptureState.ERROR
            except Exception as e:
                logger.error(f"Capture error: {e}")
                self._stats.state = CaptureState.ERROR
            finally:
                self._stats.end_time = datetime.now()

        self._capture_task = asyncio.create_task(capture_loop())
        return True

    async def stop_capture(self) -> CaptureStats | None:
        """Stop current capture."""
        self._running = False

        if self._capture_task:
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
            self._capture_task = None

        if self._stats:
            self._stats.end_time = datetime.now()
            if self._stats.state == CaptureState.CAPTURING:
                self._stats.state = CaptureState.IDLE

        logger.info("Capture stopped")
        return self._stats

    def _handle_packet(self, packet) -> None:
        """Handle captured packet."""
        try:
            from scapy.layers.dot11 import Dot11, RadioTap
            from scapy.layers.eap import EAPOL

            if not packet.haslayer(EAPOL):
                return

            self._stats.eapol_count += 1
            self._stats.state = CaptureState.CAPTURING

            # Get addresses
            if packet.haslayer(Dot11):
                dot11 = packet.getlayer(Dot11)
                addr1 = dot11.addr1  # Destination
                addr2 = dot11.addr2  # Source
                addr3 = dot11.addr3  # BSSID

                # Determine client and AP
                bssid = addr3.lower() if addr3 else None
                if not bssid:
                    return

                # Check if this is our target
                if self._current_target and bssid != self._current_target[0]:
                    return

                # Determine client MAC
                client_mac = addr2 if addr2 != bssid else addr1

                # Get EAPOL data
                eapol = packet.getlayer(EAPOL)
                eapol_data = bytes(eapol)

                # Determine message number from key info
                if len(eapol_data) >= 6:
                    key_info = int.from_bytes(eapol_data[5:7], "big")
                    msg_num = self._get_eapol_message_num(key_info, eapol_data)

                    if msg_num:
                        logger.debug(f"EAPOL M{msg_num} from {client_mac}")

                        # Track frames
                        if client_mac not in self._eapol_frames:
                            self._eapol_frames[client_mac] = {}
                        self._eapol_frames[client_mac][msg_num] = packet

                        # Check for complete handshake
                        self._check_handshake(client_mac, bssid)

        except Exception as e:
            logger.debug(f"EAPOL handling error: {e}")

    def _get_eapol_message_num(self, key_info: int, data: bytes) -> int | None:
        """Determine EAPOL message number from key info."""
        # Key Info flags
        key_ack = (key_info >> 7) & 1
        key_mic = (key_info >> 8) & 1
        secure = (key_info >> 9) & 1
        install = (key_info >> 6) & 1

        # Message 1: ACK set, MIC not set
        if key_ack and not key_mic:
            return 1
        # Message 2: MIC set, ACK not set, not secure
        elif key_mic and not key_ack and not secure:
            return 2
        # Message 3: ACK set, MIC set, secure, install
        elif key_ack and key_mic and secure and install:
            return 3
        # Message 4: MIC set, secure, ACK not set
        elif key_mic and secure and not key_ack:
            return 4

        return None

    def _check_handshake(self, client_mac: str, bssid: str) -> None:
        """Check if we have a complete handshake."""
        if client_mac not in self._eapol_frames:
            return

        frames = self._eapol_frames[client_mac]
        messages = list(frames.keys())

        # Check for valid combinations
        if (1 in messages and 2 in messages) or (2 in messages and 3 in messages):
            # We have a potentially complete handshake
            ssid = self._current_target[1] if self._current_target else "unknown"

            # Check if already recorded
            for hs in self._stats.handshakes:
                if hs.client_mac == client_mac:
                    hs.messages = messages
                    return

            # Create new handshake record
            handshake = Handshake(
                bssid=bssid,
                ssid=ssid,
                client_mac=client_mac,
                capture_type=CaptureType.HANDSHAKE,
                messages=messages,
            )

            # Save to file
            pcap_path = self._save_handshake(handshake, frames)
            if pcap_path:
                handshake.pcap_path = str(pcap_path)

            self._stats.handshakes.append(handshake)
            logger.info(f"Handshake captured: {ssid} ({client_mac})")

            if self._on_handshake:
                self._on_handshake(handshake)

    def _save_handshake(self, handshake: Handshake, frames: dict) -> Path | None:
        """Save handshake to pcap file."""
        try:
            from scapy.all import wrpcap

            # Generate filename
            safe_ssid = "".join(c if c.isalnum() else "_" for c in handshake.ssid)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_ssid}_{handshake.bssid.replace(':', '')}_{timestamp}.pcap"
            pcap_path = self.captures_dir / filename

            # Write frames
            packets = list(frames.values())
            wrpcap(str(pcap_path), packets)

            logger.info(f"Saved handshake to {pcap_path}")
            return pcap_path

        except Exception as e:
            logger.error(f"Failed to save handshake: {e}")
            return None

    def get_captures(self) -> list[Handshake]:
        """Get all captured handshakes."""
        if self._stats:
            return self._stats.handshakes.copy()
        return []

