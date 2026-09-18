"""Generate Expo icon / splash PNGs (no third-party image library)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "apps" / "mobile" / "assets"

SAFFRON = (196, 92, 38)
CREAM = (251, 246, 238)
MAROON = (107, 45, 60)


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_png(path: Path, pixels: list[list[tuple[int, int, int]]]) -> None:
    height = len(pixels)
    width = len(pixels[0])
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b in row:
            raw.extend((r, g, b))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


def solid(size: int, color: tuple[int, int, int]) -> list[list[tuple[int, int, int]]]:
    return [[color] * size for _ in range(size)]


def icon(size: int = 1024) -> list[list[tuple[int, int, int]]]:
    pixels = solid(size, SAFFRON)
    cx = cy = size / 2
    outer = size * 0.32
    inner = size * 0.22
    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            d = (dx * dx + dy * dy) ** 0.5
            if inner <= d <= outer:
                pixels[y][x] = CREAM
            elif d < inner * 0.45:
                pixels[y][x] = MAROON
    return pixels


def splash_icon(size: int = 512) -> list[list[tuple[int, int, int]]]:
    pixels = solid(size, CREAM)
    cx = cy = size / 2
    outer = size * 0.34
    inner = size * 0.24
    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            d = (dx * dx + dy * dy) ** 0.5
            if inner <= d <= outer:
                pixels[y][x] = SAFFRON
            elif d < inner * 0.45:
                pixels[y][x] = MAROON
    return pixels


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    write_png(ASSETS / "icon.png", icon(1024))
    write_png(ASSETS / "adaptive-icon.png", icon(1024))
    write_png(ASSETS / "splash-icon.png", splash_icon(512))
    write_png(ASSETS / "favicon.png", icon(48))
    print(f"Wrote icons in {ASSETS}")


if __name__ == "__main__":
    main()
