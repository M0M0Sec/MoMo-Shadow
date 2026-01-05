"""
Channel Hopper Module

Manages WiFi channel hopping for scanning.
"""

from __future__ import annotations

import asyncio
import logging
import random

logger = logging.getLogger(__name__)


class ChannelHopper:
    """
    WiFi channel hopper.

    Cycles through channels for comprehensive scanning.
    """

    def __init__(
        self,
        interface: str,
        channels: list[int] | None = None,
        interval: float = 0.5,
        randomize: bool = False,
    ):
        """
        Initialize channel hopper.

        Args:
            interface: WiFi interface
            channels: List of channels to hop (default: 1,6,11)
            interval: Hop interval in seconds
            randomize: Randomize channel order
        """
        self.interface = interface
        self.channels = channels or [1, 6, 11]
        self.interval = interval
        self.randomize = randomize

        self._running = False
        self._task: asyncio.Task | None = None
        self._current_channel = 0
        self._hop_count = 0

    @property
    def current_channel(self) -> int:
        """Get current channel."""
        return self._current_channel

    @property
    def hop_count(self) -> int:
        """Get total hop count."""
        return self._hop_count

    async def set_channel(self, channel: int) -> bool:
        """
        Set interface to specific channel.

        Args:
            channel: Channel number

        Returns:
            True if successful
        """
        try:
            # Use iw command to set channel
            proc = await asyncio.create_subprocess_exec(
                "iw",
                "dev",
                self.interface,
                "set",
                "channel",
                str(channel),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode == 0:
                self._current_channel = channel
                logger.debug(f"Channel set to {channel}")
                return True
            else:
                logger.warning(f"Failed to set channel {channel}: {stderr.decode()}")
                return False

        except FileNotFoundError:
            logger.warning("iw command not found - channel hopping disabled")
            return False
        except Exception as e:
            logger.error(f"Channel set error: {e}")
            return False

    async def start(self) -> None:
        """Start channel hopping."""
        if self._running:
            return

        self._running = True
        logger.info(f"Starting channel hopper: {self.channels}")

        async def hop_loop() -> None:
            channels = self.channels.copy()

            while self._running:
                if self.randomize:
                    random.shuffle(channels)

                for channel in channels:
                    if not self._running:
                        break

                    await self.set_channel(channel)
                    self._hop_count += 1
                    await asyncio.sleep(self.interval)

        self._task = asyncio.create_task(hop_loop())

    async def stop(self) -> None:
        """Stop channel hopping."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Channel hopper stopped")

    async def pause_on_channel(self, channel: int, duration: float) -> None:
        """
        Pause hopping and stay on specific channel.

        Args:
            channel: Channel to stay on
            duration: Duration in seconds
        """
        was_running = self._running

        if was_running:
            await self.stop()

        await self.set_channel(channel)
        await asyncio.sleep(duration)

        if was_running:
            await self.start()

