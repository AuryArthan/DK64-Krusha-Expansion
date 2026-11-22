"""Owner-colored native key turns, without moving established private banks."""
import colorsys
import hashlib
import json
import math
from pathlib import Path
import struct
from recruitment_keys import COLORS
from key_geometry import END_SCALE, along_key

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


def colored_key_frame(native):
    """Resample the native turn about its shaft, retaining the 44px canvas.

    The texture is stored tip-up. Locate its actual endpoints per angle.
    Filter in premultiplied alpha before quantizing to the N64's RGBA5551.
    """
    size = 44
    pixels = struct.unpack('>1936H', native)
    filled = [i // size for i, v in enumerate(pixels) if v & 1]
    tip, bow = min(filled), max(filled) + 1
    length = bow - tip
    head_joint = tip + length * 110/341
    bow_joint = tip + length * 196/341
    original = (tip, head_joint, bow_joint, bow)
    enlarged = [along_key(v, *original) for v in original]
    output = [0] * len(pixels)
    for y in range(tip, bow):
        segment = 0 if y+.5 < enlarged[1] else 1 if y+.5 < enlarged[2] else 2
        fraction = (y+.5-enlarged[segment])/(enlarged[segment+1]-enlarged[segment])
        sy = original[segment] + fraction*(original[segment+1]-original[segment]) - .5
        iy = math.floor(sy)
        width_scale = 1 if segment == 1 else END_SCALE
        for x in range(size):
            sx = (x+.5-size/2)/width_scale + size/2-.5
            ix = math.floor(sx)
            alpha = red = green = blue = 0.
            for row in (iy, iy+1):
                if not 0 <= row < size:
                    continue
                for col in (ix, ix+1):
                    if col >= size:
                        continue
                    value = pixels[size*row+col]
                    if value & 1:
                        weight = (1-abs(sy-row))*(1-abs(sx-col))
                        alpha += weight
                        red += weight*(value >> 11)
                        green += weight*(value >> 6 & 31)
                        blue += weight*(value >> 1 & 31)
            if alpha >= .5:
                output[y*size+x] = round(red/alpha)<<11 | round(green/alpha)<<6 | round(blue/alpha)<<1 | 1
    updated = [i // size for i, v in enumerate(output) if v & 1]
    assert (min(updated), max(updated)+1) == (tip, bow)
    return struct.pack('>1936H', *output)


def payloads(rom, read_file):
    # Native boss-key descriptor807210B8, not adjacent battle crown807210EC.
    native = read_file(rom, 25, 5877)
    assert len(native) == 44 * 44 * 2
    assert all(not read_file(rom, 25, i) for i in range(TOKEN, TOKEN + 5))
    frame = colored_key_frame(native)
    return [tint(frame, color) for color in COLORS]


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
    colored_frames = [colored_key_frame(frame) for frame in frames[1:]]
    files = [tint(frame, color) for color in COLORS for frame in colored_frames]
    from mirror_prints import BANK_INDEX, payloads as print_payloads
    assert len(files) == BANK_INDEX
    files += print_payloads(source, read_file)
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
        table=ROTATION_TABLE, print_files=len(files)-BANK_INDEX, rom_start=start, rom_end=end, token=ROTATION_TOKEN,
        entries=[dict(index=i, owner=i // 15, frame=i % 15 + 1,
                      sha256=hashlib.sha256(data).hexdigest()) for i, data in enumerate(files[:BANK_INDEX])]
    ), indent=2) + '\n')
    print('Embedded75 native colored-key turn frames; end', hex(end))
