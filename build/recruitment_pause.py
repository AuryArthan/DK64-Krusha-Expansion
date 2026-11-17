"""Owner-colored native key icons appended after the approved scene assets."""
import colorsys
import struct
from recruitment_keys import COLORS

FIRST = 224
TOKEN = 7250

def payloads(rom, read_file):
    # Native descriptor807210B8 (boss key), frame0 of16. The adjacent
    # descriptor807210EC is the battle crown, not another key variant.
    native = read_file(rom, 25, 5877)
    assert len(native) == 44 * 44 * 2
    assert all(not read_file(rom,25,i) for i in range(TOKEN,TOKEN+5))
    result = []
    for target in COLORS:
        hue, saturation, _ = colorsys.rgb_to_hsv(*(x / 255 for x in target))
        out = bytearray()
        for (v,) in struct.iter_unpack('>H', native):
            rgb = (v >> 11 & 31, v >> 6 & 31, v >> 1 & 31)
            _, sat, value = colorsys.rgb_to_hsv(*(x / 31 for x in rgb))
            r, g, b = (round(x * 31) for x in colorsys.hsv_to_rgb(hue, sat * saturation, value))
            out += struct.pack('>H', r << 11 | g << 6 | b << 1 | v & 1)
        result.append(bytes(out))
    return result
