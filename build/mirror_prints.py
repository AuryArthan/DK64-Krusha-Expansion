"""Mirror-only printed materials. Tokens are referenced only by alternate geometry."""
import struct

TOKEN = 8100
BANK_INDEX = 75  # After the five sets of 15 rotating pause-key frames in table 29.
SIGNS = (0xA70, 0xA72, 0xA73, 0xA74, 0xA86)
DIRECTORIES = (0x352, 0x37C, 0x38F, 0x3AE)
FACTORY = (*DIRECTORIES, 0x3B3, 0x385)
SHIRT, BARREL = 0xEE4, 0x134A
MATERIALS = (*SIGNS, 0x00A, *FACTORY, SHIRT, BARREL)
# DK's 0xF0 door carries his portrait. The other four have a two-part
# colored question mark as their closed frame in texture table 7.
DOORS = {0x67: 0x14A, 0xEF: 0x1F8, 0xF1: 0x1FA, 0xF2: 0x1FC}
DOOR_FRAMES = tuple(f for first in DOORS.values() for f in (first, first + 1))


def mirror_words(raw, bare, material):
    """Reflect lettering within its original space, retaining taper and pointers.

    Boxes are inclusive, in upright artwork coordinates. Reconstruct the
    antialiased white paint against the native bare plank's blue channel.
    The lab plank uses a wrapped wood grain offset of twenty texels.
    """
    areas = {
        0xA70: [(3, 1, 40, 17), (8, 18, 41, 31)],
        0xA72: [(12, 0, 56, 12), (27, 16, 60, 29)],
        0xA73: [(6, 0, 60, 14), (26, 15, 61, 30)],
        0xA74: [(2, 0, 49, 14), (5, 15, 38, 29)],
    }
    original = list(struct.unpack('>2048H', raw))
    plank = struct.unpack('>2048H', bare)
    def index(x, y):
        return (31-y)*64+x
    def rgb(v):
        return [v >> 11, (v >> 6) & 31, (v >> 1) & 31]
    result = original.copy()
    for left, top, right, bottom in areas[material]:
        for y in range(top, bottom+1):
            paint = {}
            for x in range(left, right+1):
                # The left edge of the WAY arrow almost touches the Y.
                if material == 0xA70 and 7 <= y <= 9 and x >= 39:
                    continue
                i = index(x, y)
                wood = plank[index((x+(20 if material == 0xA74 else 0)) % 64, y)]
                bg, ink = rgb(wood), rgb(original[i])
                strength = (ink[2]-bg[2])/max(1, 31-bg[2])
                if strength <= .075:
                    continue
                result[i] = wood
                dest_x = right + left - x
                if material == 0xA73 and top == 0:
                    # Increasing U moves TRAINING left on the mirrored board.
                    # Close four empty columns between letters so both the
                    # T at the post and the G at the taper fit at native size.
                    dest_x += 5 + sum(x > gap for gap in (22, 30, 40, 44))
                paint[dest_x] = (strength, ink, bg)
            for x, (strength, ink, bg) in paint.items():
                i = index(x, y)
                dst = rgb(result[i])
                out = [min(31, max(0, round(ink[c]+(dst[c]-bg[c])*(1-strength)))) for c in range(3)]
                result[i] = out[0]<<11 | out[1]<<6 | out[2]<<1 | (original[i]&1)
    return struct.pack('>2048H', *result)


def reflect_rgba(raw, width):
    rows = struct.Struct('>'+'H'*width)
    return b''.join(rows.pack(*row[::-1]) for row in rows.iter_unpack(raw))


def shirt_mips(raw):
    # Native actor mipmaps are padded to a full eight-byte TMEM word per
    # row below 4 pixels. Preserve those final rows (imperceptible at distance).
    assert len(raw) == 2744
    out = bytearray(raw)
    start = 0
    for width in (32, 16, 8, 4):
        end = start + width*width*2
        out[start:end] = reflect_rgba(raw[start:end], width)
        start = end
    return bytes(out)


def payloads(rom, read):
    output = []
    for n, material in enumerate(MATERIALS):
        assert not read(rom, 25, TOKEN+n)
        raw = read(rom, 25, material)
        if material in SIGNS[:4]:
            data = mirror_words(raw, read(rom, 25, 0xA6F), material)
        elif material in FACTORY:
            # CI4 indices, 64 pixels per row. Keep the native palette.
            assert len(raw) == 2048
            data = bytes((v >> 4) | ((v & 15) << 4) for p in range(0, len(raw), 32)
                         for v in raw[p:p+32][::-1])
        elif material == SHIRT:
            data = shirt_mips(raw)
        else:
            assert len(raw) == 4096
            data = reflect_rgba(raw, 32 if material == BARREL else 64)
        assert len(data) == len(raw)
        output.append(data)
    for frame in DOOR_FRAMES:
        # The mirrored left half needs the reflected right half, and vice versa.
        raw = read(rom, 7, frame ^ 1)
        assert len(raw) == 4096
        output.append(reflect_rgba(raw, 32))
    return output


def mark_geometry(data, table, model):
    """Redirect exact print commands, preserving texture palettes and UV seams."""
    word = lambda p: struct.unpack_from('>I', data, p)[0]
    if table == 1 and model in (1, 26, 176):
        selected = {1: (0x00A,), 26: FACTORY, 176: SIGNS}[model]
        start, end = word(0x34), word(0x38)
    elif (table, model) in ((5, 0xC0), (5, 18), (27, 0)):
        selected = (SHIRT,) if table == 5 and model == 18 else (BARREL,)
        end = 40 + word(4) - word(0)
        start = 40 + word(end) - word(0)
    else:
        return data
    b = bytearray(data)
    seen = set()
    for p in range(start, end, 8):
        if data[p] != 0xFD:
            continue
        material = word(p+4)
        if material in selected:
            assert 0xF0 not in data[p+8:p+32:8], 'Unexpected shared palette'
            struct.pack_into('>I', b, p+4, TOKEN+MATERIALS.index(material))
            seen.add(material)
    assert seen == set(selected), (table, model, seen)
    return bytes(b)
