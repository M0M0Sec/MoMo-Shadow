"""
Database Module

Async SQLite database for storing scan results.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class Database:
    """
    Async SQLite database.

    Stores:
    - Access points
    - Clients
    - Probe requests
    - Handshakes
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS access_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bssid TEXT UNIQUE NOT NULL,
        ssid TEXT,
        channel INTEGER,
        signal_dbm INTEGER,
        security TEXT,
        hidden BOOLEAN DEFAULT FALSE,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        beacon_count INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mac TEXT UNIQUE NOT NULL,
        bssid TEXT,
        signal_dbm INTEGER,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (bssid) REFERENCES access_points(bssid)
    );

    CREATE TABLE IF NOT EXISTS probes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_mac TEXT NOT NULL,
        ssid TEXT NOT NULL,
        signal_dbm INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS handshakes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bssid TEXT NOT NULL,
        ssid TEXT,
        client_mac TEXT NOT NULL,
        capture_type TEXT NOT NULL,
        pcap_path TEXT,
        hashcat_hash TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (bssid) REFERENCES access_points(bssid)
    );

    CREATE INDEX IF NOT EXISTS idx_ap_ssid ON access_points(ssid);
    CREATE INDEX IF NOT EXISTS idx_client_bssid ON clients(bssid);
    CREATE INDEX IF NOT EXISTS idx_probe_ssid ON probes(ssid);
    CREATE INDEX IF NOT EXISTS idx_handshake_bssid ON handshakes(bssid);
    """

    def __init__(self, db_path: str = "/var/momo-shadow/data/shadow.db"):
        """
        Initialize database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._conn: aiosqlite.Connection | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database connection and schema."""
        if self._initialized:
            return

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row

        # Create schema
        await self._conn.executescript(self.SCHEMA)
        await self._conn.commit()

        self._initialized = True
        logger.info(f"Database initialized: {self.db_path}")

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            self._initialized = False
            logger.info("Database closed")

    # Access Points
    async def upsert_ap(
        self,
        bssid: str,
        ssid: str,
        channel: int,
        signal_dbm: int,
        security: str,
        hidden: bool = False,
    ) -> None:
        """Insert or update access point."""
        await self.initialize()

        await self._conn.execute(
            """
            INSERT INTO access_points (bssid, ssid, channel, signal_dbm, security, hidden)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(bssid) DO UPDATE SET
                ssid = COALESCE(excluded.ssid, ssid),
                channel = excluded.channel,
                signal_dbm = excluded.signal_dbm,
                security = excluded.security,
                last_seen = CURRENT_TIMESTAMP,
                beacon_count = beacon_count + 1
            """,
            (bssid, ssid, channel, signal_dbm, security, hidden),
        )
        await self._conn.commit()

    async def get_aps(self, limit: int = 100) -> list[dict]:
        """Get access points ordered by signal strength."""
        await self.initialize()

        async with self._conn.execute(
            """
            SELECT * FROM access_points
            ORDER BY signal_dbm DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_ap(self, bssid: str) -> dict | None:
        """Get access point by BSSID."""
        await self.initialize()

        async with self._conn.execute(
            "SELECT * FROM access_points WHERE bssid = ?",
            (bssid,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    # Clients
    async def upsert_client(
        self,
        mac: str,
        bssid: str | None = None,
        signal_dbm: int = -100,
    ) -> None:
        """Insert or update client."""
        await self.initialize()

        await self._conn.execute(
            """
            INSERT INTO clients (mac, bssid, signal_dbm)
            VALUES (?, ?, ?)
            ON CONFLICT(mac) DO UPDATE SET
                bssid = COALESCE(excluded.bssid, bssid),
                signal_dbm = excluded.signal_dbm,
                last_seen = CURRENT_TIMESTAMP
            """,
            (mac, bssid, signal_dbm),
        )
        await self._conn.commit()

    async def get_clients(self, bssid: str | None = None, limit: int = 100) -> list[dict]:
        """Get clients, optionally filtered by AP."""
        await self.initialize()

        if bssid:
            query = "SELECT * FROM clients WHERE bssid = ? ORDER BY last_seen DESC LIMIT ?"
            params = (bssid, limit)
        else:
            query = "SELECT * FROM clients ORDER BY last_seen DESC LIMIT ?"
            params = (limit,)

        async with self._conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # Probes
    async def add_probe(
        self,
        client_mac: str,
        ssid: str,
        signal_dbm: int = -100,
    ) -> None:
        """Add probe request."""
        await self.initialize()

        await self._conn.execute(
            "INSERT INTO probes (client_mac, ssid, signal_dbm) VALUES (?, ?, ?)",
            (client_mac, ssid, signal_dbm),
        )
        await self._conn.commit()

    async def get_probes(self, ssid: str | None = None, limit: int = 100) -> list[dict]:
        """Get probe requests."""
        await self.initialize()

        if ssid:
            query = "SELECT * FROM probes WHERE ssid = ? ORDER BY timestamp DESC LIMIT ?"
            params = (ssid, limit)
        else:
            query = "SELECT * FROM probes ORDER BY timestamp DESC LIMIT ?"
            params = (limit,)

        async with self._conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # Handshakes
    async def add_handshake(
        self,
        bssid: str,
        ssid: str,
        client_mac: str,
        capture_type: str,
        pcap_path: str | None = None,
        hashcat_hash: str | None = None,
    ) -> int:
        """Add captured handshake."""
        await self.initialize()

        cursor = await self._conn.execute(
            """
            INSERT INTO handshakes (bssid, ssid, client_mac, capture_type, pcap_path, hashcat_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (bssid, ssid, client_mac, capture_type, pcap_path, hashcat_hash),
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def get_handshakes(self, bssid: str | None = None, limit: int = 100) -> list[dict]:
        """Get captured handshakes."""
        await self.initialize()

        if bssid:
            query = "SELECT * FROM handshakes WHERE bssid = ? ORDER BY timestamp DESC LIMIT ?"
            params = (bssid, limit)
        else:
            query = "SELECT * FROM handshakes ORDER BY timestamp DESC LIMIT ?"
            params = (limit,)

        async with self._conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # Stats
    async def get_stats(self) -> dict:
        """Get database statistics."""
        await self.initialize()

        stats = {}

        async with self._conn.execute("SELECT COUNT(*) FROM access_points") as cursor:
            row = await cursor.fetchone()
            stats["aps"] = row[0]

        async with self._conn.execute("SELECT COUNT(*) FROM clients") as cursor:
            row = await cursor.fetchone()
            stats["clients"] = row[0]

        async with self._conn.execute("SELECT COUNT(*) FROM probes") as cursor:
            row = await cursor.fetchone()
            stats["probes"] = row[0]

        async with self._conn.execute("SELECT COUNT(*) FROM handshakes") as cursor:
            row = await cursor.fetchone()
            stats["handshakes"] = row[0]

        return stats

    async def cleanup_old(self, days: int = 7) -> int:
        """Remove old entries."""
        await self.initialize()

        # Delete old probes
        cursor = await self._conn.execute(
            """
            DELETE FROM probes
            WHERE timestamp < datetime('now', ? || ' days')
            """,
            (-days,),
        )
        deleted = cursor.rowcount
        await self._conn.commit()

        logger.info(f"Cleaned up {deleted} old probe records")
        return deleted

