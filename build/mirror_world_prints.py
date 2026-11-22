"""Additional inscriptions used only by the mirrored versions of these meshes."""
import struct
from pathlib import Path

RING = (0xAF6, 0xAF7, 0xAF8, 0xAFB)
MAP_PRINTS = {
    6: (0xBA,), 55: (0xBA,), 30: (0x3F1,), 51: (0x741, 0x742),
    61: (0x7CA,), 87: (0x8DA, 0x8DB, 0x8DE),
    **dict.fromkeys((203, 204, 205, 206, 207, 215), RING),
}
MODEL_PRINTS = {
    0xD5: (0xC13, 0xC14), 0x104: (0xC31, 0xC35),
    0x117: (0xC47,), 0x11D: (0xC64,), 0x11F: (0xC47,),
    0x142: tuple(range(0xCCF, 0xCD5)), 0x188: (0xD1E,),
    0x194: (0xD30, 0xD36), 0x1C3: (0xD95, 0xD9E, 0xD96, 0xD9D),
    0x280: (0xE49,), 0x284: (0xE4C,),
}
MATERIALS = sorted({m for group in (*MAP_PRINTS.values(), *MODEL_PRINTS.values()) for m in group})
FIRST_TOKEN = 8122  # 97 in private table 29, following the hint-door frames
# Both ends of the boxing slogan spill onto the neighboring logo tiles.
SWAPS = {a: b for x, y in ((0xAF6, 0xAFB), (0xAF7, 0xAF8), (0xD95, 0xD9E), (0xD96, 0xD9D))
         for a, b in ((x, y), (y, x))}


def reflect_region(pixels, width, left, right, bottom, top):
    result = list(pixels)
    for y in range(bottom, top + 1):
        start, stop = y * width + left, y * width + right + 1
        result[start:stop] = pixels[start:stop][::-1]
    return result


def unpack_ci4(data):
    return [i for v in data for i in (v >> 4, v & 15)]


def rgb555(value):
    return value >> 11, value >> 6 & 31, value >> 1 & 31


def crate(raw, rom, read):
    # The lid supplies the unpainted version of the very same planks.
    # Its quantizer chose a different palette, so remap the exposed wood.
    paint = unpack_ci4(raw)
    wood = unpack_ci4(read(rom, 25, 0x19))
    def colors(index):
        return [rgb555(v) for v, in struct.iter_unpack('>H', read(rom, 25, index))]

    src, dest = colors(0x1A), colors(0xD1F)
    def distance(a, b):
        return sum((x-y)**2 for x, y in zip(a, b))
    bare = [min(range(16), key=lambda n: distance(src[v], dest[n])) for v in wood]
    out = paint.copy()
    ink = {}
    for i, v in enumerate(paint):
        y, x = divmod(i, 64)
        if v == 1 or (13 <= x <= 48 and 6 <= y <= 54 and distance(dest[v],src[wood[i]]) > 65):
            out[i] = bare[i]
            ink[y*64+63-x] = v
    for i, v in ink.items():
        out[i] = v
    return out


def payloads(rom, read):
    header = Path(__file__).resolve().parents[1] / 'include' / 'mirror_world_prints.h'
    constants = dict(line.split()[1:] for line in header.read_text().splitlines() if line.startswith('#define '))
    assert int(constants['MIRROR_WORLD_TOKEN']) == FIRST_TOKEN
    assert int(constants['MIRROR_WORLD_COUNT']) == len(MATERIALS)
    assert int(constants['MIRROR_WORLD_BANK']) == FIRST_TOKEN - 8025
    output = []
    for n, mat in enumerate(MATERIALS):
        assert not read(rom, 25, FIRST_TOKEN+n)
        raw = read(rom, 25, SWAPS.get(mat, mat))
        width = 32 if mat in (0xD96, 0xD9D) else 64
        indexed = mat in (0xBA, 0xD30, 0xD36, 0xD1E, 0xC31, 0xC35)
        if indexed:
            pixels = unpack_ci4(raw)
        elif mat == 0xE4C:
            pixels = list(raw)  # I8
        else:
            pixels = [v for v, in struct.iter_unpack('>H', raw)]
        height = len(pixels)//width
        assert height in (16, 32, 64) and len(pixels) == width*height
        if mat == 0xD1E:
            result = crate(raw, rom, read)
        else:
            bounds = (0, width-1, 0, height-1)
            if mat == 0x3F1:
                bounds = (11, 60, 6, 26)  # brass nameplate, excluding the pointing hand
            elif mat in (0xC47, 0xC64):
                bounds = (6, 57, 13, 24)  # printed word, above the vertical arrows
            result = reflect_region(pixels, width, *bounds)
        if indexed:
            data = bytes(a << 4 | b for a,b in zip(result[::2], result[1::2]))
        elif mat == 0xE4C:
            data = bytes(result)
        else:
            data = struct.pack('>%dH' % len(result), *result)
        assert len(data) == len(raw)
        output.append(data)
    return output
