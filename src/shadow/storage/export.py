"""
Export Module

Export captures to hashcat/john format.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class HashcatExporter:
    """
    Export captures to hashcat format.

    Supports:
    - WPA2 handshakes (mode 22000/22001)
    - PMKID (mode 22000)
    """

    def __init__(self, output_dir: str = "/var/shadow/exports"):
        """
        Initialize exporter.

        Args:
            output_dir: Directory for export files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def export_pcap(self, pcap_path: str, output_name: str | None = None) -> str | None:
        """
        Convert pcap to hashcat format using hcxpcapngtool.

        Args:
            pcap_path: Path to pcap file
            output_name: Output filename (without extension)

        Returns:
            Path to hashcat file or None on failure
        """
        pcap = Path(pcap_path)
        if not pcap.exists():
            logger.error(f"PCAP not found: {pcap_path}")
            return None

        # Generate output filename
        if not output_name:
            output_name = pcap.stem

        output_path = self.output_dir / f"{output_name}.22000"

        try:
            # Run hcxpcapngtool
            proc = await asyncio.create_subprocess_exec(
                "hcxpcapngtool",
                "-o",
                str(output_path),
                str(pcap),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"hcxpcapngtool failed: {stderr.decode()}")
                return None

            if output_path.exists() and output_path.stat().st_size > 0:
                logger.info(f"Exported to {output_path}")
                return str(output_path)
            else:
                logger.warning("No hashes extracted from pcap")
                return None

        except FileNotFoundError:
            logger.error("hcxpcapngtool not found")
            return None
        except Exception as e:
            logger.error(f"Export error: {e}")
            return None

    async def export_all(self, captures_dir: str) -> list[str]:
        """
        Export all pcap files in directory.

        Args:
            captures_dir: Directory with pcap files

        Returns:
            List of exported hash file paths
        """
        captures = Path(captures_dir)
        exported = []

        for pcap in captures.glob("*.pcap"):
            result = await self.export_pcap(str(pcap))
            if result:
                exported.append(result)

        return exported

    def create_potfile_check(self, hash_file: str) -> str | None:
        """
        Create script to check against hashcat potfile.

        Args:
            hash_file: Path to hash file

        Returns:
            Path to check script or None
        """
        script = f"""#!/bin/bash
# Check {Path(hash_file).name} against potfile
hashcat -m 22000 --show {hash_file}
"""
        script_path = self.output_dir / f"check_{Path(hash_file).stem}.sh"
        script_path.write_text(script)
        script_path.chmod(0o755)
        return str(script_path)

    def generate_wordlist_cmd(self, hash_file: str) -> str:
        """
        Generate hashcat command for cracking.

        Args:
            hash_file: Path to hash file

        Returns:
            Hashcat command string
        """
        return f"hashcat -m 22000 -a 0 {hash_file} /path/to/wordlist.txt"

