#!/usr/bin/env python3
"""
Clipchamp LevelDB / binary log filename extractor

Usage:
    python clipchamp_filename_extractor.py "C:\\path\\to\\000212.log"

The tool:
- reads the binary file without modifying it
- extracts ASCII filenames such as P1001015.mp4
- extracts the same filenames when stored as UTF-16LE
- counts each filename occurrence
- prints byte positions for reproducibility

No external packages are required.
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

FILENAME_RE = re.compile(rb"P\d{4,}\.mp4", re.IGNORECASE)


def find_ascii(data: bytes) -> dict[str, list[int]]:
    """Find ASCII Pxxxxx.mp4 filenames and return positions."""
    positions: dict[str, list[int]] = defaultdict(list)

    for match in FILENAME_RE.finditer(data):
        name = match.group().decode("ascii", errors="replace")
        positions[name].append(match.start())

    return dict(positions)


def find_utf16le(data: bytes) -> dict[str, list[int]]:
    """Find UTF-16LE encoded Pxxxxx.mp4 filenames and return positions."""
    positions: dict[str, list[int]] = defaultdict(list)

    # Build a UTF-16LE regex from the ASCII filename grammar.
    # P + at least 4 digits + .mp4
    digit = b"(?:[0-9]\x00)"
    utf16_pattern = re.compile(
        b"P\x00" + digit + digit + digit + digit +
        b"(?:[0-9]\x00)*" +
        b"\x2e\x00m\x00p\x004\x00",
        re.IGNORECASE,
    )

    for match in utf16_pattern.finditer(data):
        raw = match.group()
        try:
            name = raw.decode("utf-16le")
        except UnicodeDecodeError:
            continue
        positions[name].append(match.start())

    return dict(positions)


def merge_positions(
    *maps: dict[str, list[int]]
) -> dict[str, list[int]]:
    """Merge position dictionaries and keep positions sorted."""
    merged: dict[str, list[int]] = defaultdict(list)

    for mapping in maps:
        for name, pos_list in mapping.items():
            merged[name].extend(pos_list)

    return {name: sorted(pos_list) for name, pos_list in merged.items()}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage:")
        print(r'  python clipchamp_filename_extractor.py "C:\path\to\000212.log"')
        return 2

    log_path = Path(sys.argv[1])

    if not log_path.is_file():
        print(f"ERROR: file not found: {log_path}")
        return 1

    data = log_path.read_bytes()

    ascii_hits = find_ascii(data)
    utf16_hits = find_utf16le(data)
    hits = merge_positions(ascii_hits, utf16_hits)

    print("=" * 72)
    print("Clipchamp Filename Extractor")
    print("=" * 72)
    print(f"FILE : {log_path}")
    print(f"SIZE : {len(data):,} bytes")
    print()

    if not hits:
        print("No Pxxxxx.mp4 filenames were found.")
        return 0

    print(f"{'FILENAME':<20} {'COUNT':>8}  POSITIONS")
    print("-" * 72)

    for name in sorted(hits, key=str.casefold):
        pos = hits[name]
        print(f"{name:<20} {len(pos):>8}  {pos}")

    print()
    print(f"UNIQUE FILENAMES : {len(hits)}")
    print(f"TOTAL MATCHES    : {sum(len(v) for v in hits.values())}")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
