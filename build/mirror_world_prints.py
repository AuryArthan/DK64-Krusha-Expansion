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
# Keep existing table 29 slots stable when adding materials. Some shipping
# labels occur in both static level geometry and separately streamed props.
CARGO_MAPS = {
    0x049: (4, 5, 26, 29, 57, 58, 61, 62, 178, 185, 203, 204, 205, 206, 207, 215),
    0x04D: (4, 5, 26, 30, 57, 58, 59, 61, 62, 185, 203, 204, 205, 206, 207, 215),
    0x2AE: (17, 28, 57, 152, 196),
    0x34B: (26, 29, 185), 0x34D: (26, 29, 57, 185), 0x7AF: (57, 58, 61, 62, 178),
}
for material, maps in CARGO_MAPS.items():
    for map_id in maps:
        MAP_PRINTS[map_id] = (*MAP_PRINTS.get(map_id, ()), material)
MODEL_PRINTS[0x120] = (0x049, 0x34B)
HELM_IV = (0xD5B, 0xD5C, 0xD5D, 0xD5E)
MODEL_PRINTS[0x1B1] = HELM_IV
MATERIALS.extend((*CARGO_MAPS, *HELM_IV))
# Map, image width and codec come from each material's F3DEX2 tile.
RACE_PRINTS = {
    0x04F: (64, 'ci4', (4,)), 0x0AC: (32, 'rgba', (6, 55, 171)),
    0x296: (48, 'rgba', (17, 28, 152)), 0x38D: (64, 'ci4', (26,)),
    **dict.fromkeys(range(0x3D4, 0x3D8), (64, 'rgba', (27,))),
    0x51F: (64, 'ci4', (34, 153, 213)), 0x9EE: (64, 'rgba', (154,)),
    0xAA3: (64, 'rgba', (184,)), 0xAA4: (32, 'rgba', (184,)),
    0xAD4: (76, 'rgba', (191,)), 0xAD5: (36, 'rgba', (191,)),
}
for material, (_, _, maps) in RACE_PRINTS.items():
    for map_id in maps:
        MAP_PRINTS[map_id] = (*MAP_PRINTS.get(map_id, ()), material)
MODEL_PRINTS[0x11E] = (0x9EE,)
MODEL_PRINTS[0x1C3] += (0x51F,)  # Same small control panel on the arcade cabinet.
MATERIALS.extend(RACE_PRINTS)
FIRST_TOKEN = 8122  # 97 in private table 29, following the hint-door frames
# Four course-map images already occupy the slots immediately after RACE_PRINTS.
# Append these prints after the images so both the original tokens and the
# table-29 offsets used by the HUD remain stable.
COURSE_SLOT = len(MATERIALS)
BLOCKS = tuple(range(0x397, 0x3AA))
TRACK_BLOCKS = (*BLOCKS[:-1], 0x3CD, 0x3CE, 0x3CF, 0x3D0, 0xAB1, 0xABA)
MAP_PRINTS[26] += BLOCKS
MAP_PRINTS[185] += TRACK_BLOCKS
MAP_PRINTS[25] = (0x325, 0x338)  # Music stand and Nintendo console label.
for map_id in (176, 198):  # Training Grounds and its ending copy.
    MAP_PRINTS[map_id] = (0xA8B,)  # N64 sticker on discarded banana peels.
MAP_PRINTS[171] += (0xA5C,)  # DK rug
MODEL_PRINTS[0xCF] = (0x3A5, 0x3A6, 0x3A8, 0x3CF, 0x3D0)
NEW_PRINTS = tuple(dict.fromkeys((*BLOCKS, *TRACK_BLOCKS, 0x325, 0xA5C)))
EXTRA_PRINTS = (*NEW_PRINTS, 0x338, 0xA8B)
MATERIALS.extend(EXTRA_PRINTS)


def material_token(material):
    index = MATERIALS.index(material)
    return FIRST_TOKEN + index if index < COURSE_SLOT else 7900 + index - COURSE_SLOT


def block_faces(raw, material):
    # Some 64x32 strips contain two independent blocks. Keep each letter
    # on its own block. The left purple D and orange 3 are on their sides.
    width = 64 if material in (0x398, 0x399, 0x39A, 0x39E) else 32
    assert len(raw) == width * 32 * 2
    pixels = struct.unpack('>%dH' % (width * 32), raw)
    out = []
    for y in range(32):
        for x in range(width):
            if x < 32 and material in (0x39A, 0x39E):
                out.append(pixels[(31-y)*width+x])
            else:
                out.append(pixels[y*width+(x ^ 31)])
    return struct.pack('>%dH' % len(out), *out)


# Both ends of the boxing slogan spill onto the neighboring logo tiles.
SWAPS = {a: b for x, y in ((0xAF6, 0xAFB), (0xAF7, 0xAF8), (0xD95, 0xD9E), (0xD96, 0xD9D), (0x3D4, 0x3D7), (0x3D5, 0x3D6))
         for a, b in ((x, y), (y, x))}


def reflect_rgba(raw, width):
    rows = struct.Struct('>'+'H'*width)
    return b''.join(rows.pack(*row[::-1]) for row in rows.iter_unpack(raw))


def reflect_rgba_mips(raw):
    # The map decal ends at 4x4. The shirt has another 24 bytes of padded
    # sub-4px mip levels, which keep their native encoding.
    assert len(raw) in (2720, 2744)
    out = bytearray(raw)
    start = 0
    for width in (32, 16, 8, 4):
        end = start + width*width*2
        out[start:end] = reflect_rgba(raw[start:end], width)
        start = end
    return bytes(out)


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


def helm_numeral(rom, read, material, pixels):
    # Left/right pairs cover the bottom and top of one 128px-wide door.
    # The blue IV straddles the vertical seam. Keep the hinges and bevels.
    left = material < 0xD5D
    neighbor = material + (2 if left else -2)
    other = [v for v, in struct.iter_unpack('>H', read(rom, 25, neighbor))]
    def paint_mask(tile):
        ink = set()
        for p, value in enumerate(tile):
            red, green, blue = rgb555(value)
            if blue > max(red, green) + 2:
                row, col = divmod(p, 64)
                # Include the antialiased edge and the dark drop shadow.
                for y in range(max(0, row-2), min(32, row+3)):
                    for x in range(max(0, col-2), min(64, col+3)):
                        ink.add(y*64+x)
        return ink

    old_ink, opposite_ink = paint_mask(pixels), paint_mask(other)
    result = pixels.copy()
    columns = range(44, 64) if left else range(20)
    ys = range(10, 32) if material in (0xD5B, 0xD5D) else range(11)
    for y in ys:
        for x in columns:
            dest, src = y*64+x, y*64+63-x
            if dest in old_ink or src in opposite_ink:
                result[dest] = other[src]
    return result


def payloads(rom, read):
    header = Path(__file__).resolve().parents[1] / 'include' / 'mirror_world_prints.h'
    constants = dict(line.split(maxsplit=2)[1:] for line in header.read_text().splitlines() if line.startswith('#define '))
    assert int(constants['MIRROR_WORLD_TOKEN']) == FIRST_TOKEN
    assert int(constants['MIRROR_WORLD_COUNT']) == COURSE_SLOT
    assert int(constants['MIRROR_WORLD_BANK']) == FIRST_TOKEN - 8025
    output = []
    for n, mat in enumerate(MATERIALS):
        assert not read(rom, 25, material_token(mat))
        if n == COURSE_SLOT:
            output.extend(course_tiles(rom, read, constants, len(output)))
        raw = read(rom, 25, SWAPS.get(mat, mat))
        if mat == 0xA8B:
            assert len(raw) == 2720
            output.append(reflect_rgba_mips(raw))
            continue
        if mat in NEW_PRINTS and mat not in (0x325, 0xA5C):
            output.append(block_faces(raw, mat))
            continue
        width = 32 if mat in (0xD96, 0xD9D, 0x325) else 64
        indexed = mat in CARGO_MAPS or mat in (0xA5C, 0xBA, 0xD30, 0xD36, 0xD1E, 0xC31, 0xC35)
        if mat in RACE_PRINTS:
            width, codec, _ = RACE_PRINTS[mat]
            indexed = codec == 'ci4'
        if indexed:
            pixels = unpack_ci4(raw)
        elif mat == 0xE4C:
            pixels = list(raw)  # I8
        else:
            pixels = [v for v, in struct.iter_unpack('>H', raw)]
        height = len(pixels)//width
        assert height in (16, 21, 32, 42, 48, 64) and len(pixels) == width*height
        if mat == 0xD1E:
            result = crate(raw, rom, read)
        elif mat in HELM_IV:
            result = helm_numeral(rom, read, mat, pixels)
        elif mat == 0x2AE:
            # WINCH runs vertically in the atlas. Reflect its nameplate along
            # V, leaving the adjacent mechanism and button surfaces untouched.
            result = pixels.copy()
            for y in range(15, 49):
                start = y*64+16
                source = (63-y)*64+16
                result[start:start+11] = pixels[source:source+11]
        else:
            bounds = (0, width-1, 0, height-1)
            if mat == 0x3F1:
                bounds = (11, 60, 6, 26)  # brass nameplate, excluding the pointing hand
            elif mat in (0xC47, 0xC64, 0x9EE):
                bounds = (6, 57, 13, 24)  # printed word, above the vertical arrows
            elif mat == 0x38D:
                bounds = (7, 57, 32, 53)  # CARD above the slot
            if mat == 0x51F:
                # Separate decals on the left, at the red button and by the
                # upper switches. Preserve the controls each label belongs to.
                result = pixels
                for bounds in ((6, 20, 6, 17), (45, 59, 8, 15),
                               (8, 19, 20, 26), (45, 55, 20, 26)):
                    result = reflect_region(result, width, *bounds)
            else:
                result = reflect_region(pixels, width, *bounds)
        if indexed:
            data = bytes(a << 4 | b for a,b in zip(result[::2], result[1::2]))
        elif mat == 0xE4C:
            data = bytes(result)
        else:
            data = struct.pack('>%dH' % len(result), *result)
        assert len(data) == len(raw)
        output.append(data)
    assert int(constants['MIRROR_EXTRA_COUNT']) == len(EXTRA_PRINTS)
    assert int(constants['MIRROR_EXTRA_BANK']) == 97 + COURSE_SLOT + 4
    assert int(constants['MIRROR_EXTRA_TOKEN']) == material_token(NEW_PRINTS[0])
    return output


def course_tiles(rom, read, constants, prior_count):
    output = []
    # The race HUD draws four IA8 tiles upright. Swap their centres at the
    # call sites and reverse each scanline in its own private image.
    assert int(constants['MIRROR_RACE_BANK']) == 97 + prior_count
    for native in range(0x46, 0x4A):
        tile = read(rom, 14, native)
        assert len(tile) == 64*64
        output.append(b''.join(tile[p:p+64][::-1] for p in range(0, len(tile), 64)))
    return output
