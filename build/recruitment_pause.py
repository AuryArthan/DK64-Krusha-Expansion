"""Owner-colored native key turns, without moving established private banks."""
import colorsys
import hashlib
import json
from pathlib import Path
import struct
from recruitment_keys import COLORS

FIRST = 224
TOKEN = 7250
ROTATION_TOKEN = 8000
ROTATION_TABLE = 29
BASE = 0x101C50


def tint(native, target):
    hue, saturation, _ = colorsys.rgb_to_hsv(*(x / 255 for x in target))
    out = bytearray()
    for (v,) in struct.iter_unpack('>H', native):
        rgb = (v >> 11 & 31, v >> 6 & 31, v >> 1 & 31)
        _, sat, value = colorsys.rgb_to_hsv(*(x / 31 for x in rgb))
        r, g, b = (round(x * 31) for x in colorsys.hsv_to_rgb(hue, sat * saturation, value))
        out += struct.pack('>H', r << 11 | g << 6 | b << 1 | v & 1)
    return bytes(out)


def payloads(rom, read_file):
    # Native boss-key descriptor807210B8, not adjacent battle crown807210EC.
    native = read_file(rom, 25, 5877)
    assert len(native) == 44 * 44 * 2
    assert all(not read_file(rom, 25, i) for i in range(TOKEN, TOKEN + 5))
    return [tint(native, color) for color in COLORS]


def append_rotation_assets(path):
    """Seventy-five remaining frames in unused29, AFTER the Mirror bank.

    Keep frame0's five existing table27 slots, all Mirror indices and bank
    addresses intact. Native shared-file reference counting owns these frames.
    Padding and CIC CRC run after this append, exactly as for the other banks.
    """
    from barrel_assets import read_file
    source = Path(path).read_bytes()
    u = lambda off: struct.unpack_from('>I', source, off)[0]
    assert u(BASE + (32 + ROTATION_TABLE) * 4) == 0
    assert all(not read_file(source, 25, token) for token in range(ROTATION_TOKEN, ROTATION_TOKEN + 75))
    frames = [read_file(source, 25, 5877 + i) for i in range(16)]
    assert all(len(frame) == 44 * 44 * 2 for frame in frames)
    files = [tint(frame, color) for color in COLORS for frame in frames[1:]]
    start = (len(source) + 15) & ~15
    end = start + (len(files) + 1) * 4
    offsets = []
    for data in files:
        offsets.append(end - BASE)
        end += len(data)
    offsets.append(end - BASE)
    assert end < 0x4000000
    with open(path, 'r+b') as f:
        f.seek(0, 2)
        f.write(bytes(start - len(source)))
        f.write(struct.pack('>%dI' % len(offsets), *offsets))
        for data in files:
            f.write(data)
        f.seek(BASE + ROTATION_TABLE * 4)
        f.write(struct.pack('>I', start - BASE))
        f.seek(BASE + (32 + ROTATION_TABLE) * 4)
        f.write(struct.pack('>I', len(files)))
    Path(str(path) + '.key-rotation-assets.json').write_text(json.dumps(dict(
        table=ROTATION_TABLE, rom_start=start, rom_end=end, token=ROTATION_TOKEN,
        entries=[dict(index=i, owner=i // 15, frame=i % 15 + 1,
                      sha256=hashlib.sha256(data).hexdigest()) for i, data in enumerate(files)]
    ), indent=2) + '\n')
    print('Embedded75 native colored-key turn frames; end', hex(end))
