"""Readable world markings for the USA mirror geometry bank.

Rules address a printed material inside one model. The renderer can replace
some images at runtime (digit wheels, portal animation frames), so those
panels keep their original texture commands and animation-table offsets.
"""
import struct


def rules(table, model):
    """Return horizontal UV sums, texture swaps and panel reflection types."""
    uv, swaps, panels = {}, {}, {}

    def pair(left, right, extent=992):
        uv[left] = uv[right] = extent
        swaps[left], swaps[right] = right, left

    if table == 5 and model == 100:  # B. Locker, three animated segments
        pair(0x0C000000, 0x0E000000)
        uv[0x0D000000] = 992
    elif table == 5 and 0xC5 <= model <= 0xCA:
        uv[(0xDFB, 0xDF8, 0xDF3, 0xD45, 0xDF0, 0x134F)[model-0xC5]] = 992
    elif table == 5 and model == 0x24:
        uv[0xF4E] = 1024  # Mad Jack's painted question mark
    elif table == 5 and model == 0xDF:
        uv[0x1379] = 1024  # DK stamp in the center of a Rainbow Coin patch
    elif table == 5 and model == 0x9D:
        pair(0x1301, 0x1302, 1024)  # TO and YS meet across the chest panel.
    elif table == 5 and model == 0x38:
        # Four upright digits plus the upper and lower faces of the toy block.
        uv.update(dict.fromkeys((0x1041, 0x1045, 0x1046, 0x1049, 0x104B, 0x104C), 1024))
    elif table == 5 and model in (0x1F, 0x7C, 0x8D):
        # Four 16-texel strips repeat around the TNT barrel. Reflect
        # around the front seam, also keeping every native mip level.
        pair(0xF22, 0xF23, 512)
        pair(0xF2B, 0xF2C, 512)
    elif table == 5 and model == 3:
        uv[0xE8D] = 992  # DK's tie, including its native mipmaps
    elif table == 5 and model in (0x68, 0x87, 0xD4):
        uv[0x1266] = 1024  # N64 decal on the animated Golden Banana actors
    elif table == 27 and model == 65:
        uv[0xB7D] = 1024  # Krusha's copy of the world Golden Banana
    elif table != 4:
        return uv, swaps, panels
    elif model == 0x250:
        pair(0xE30, 0xE31)  # DK plaque split across Galleon’s underwater gate.
    elif model in (0x48, 0x28F):
        # Nintendo and Rareware Adventure rewards. Every turn frame uses the
        # same four corners, with native S coordinates from -32 to 1376.
        uv[0x12C if model == 0x48 else 0x389] = 1344
    elif model in (0x74, 0x290):
        uv[0xB7D] = 1024  # collectible and decorative Golden Bananas
    elif model == 0x288:
        uv[0xAD5] = 1120  # Fairy Isle reward's 36-pixel Rareware decal
    elif model in (0x11A, 0x11C):
        # The printed face is four CI4 tiles. Swap matching palettes too.
        top = (0xC48, 0xC50) if model == 0x11A else (0xC60, 0xC62)
        pair(*top, 2016)
        pair(0xC4A, 0xC54, 2016)
    elif model == 0x1B1:
        panels = dict.fromkeys(range(0xD5B, 0xD5F), 'helm_back')
    elif model == 0x1A6:
        uv[0xD45] = 992  # Helm four-crown requirement
    elif model == 0x1A7:
        uv.update(dict.fromkeys((0xD48, 0xD49), 1376))  # two 44px coin plaques
    elif model in (0x8B, 0x8C):
        first = 0xBA5 if model == 0x8B else 0xBA7
        uv.update(dict.fromkeys((first, first+1), 992))  # digit and its shadow
    elif model in (0x251, 0x252):
        uv[0xE32 + model - 0x251] = 992
    elif model == 0x79:
        uv[0xB85] = 2016  # Snide's 64-pixel wooden board
    elif model == 0x7A:
        uv[0xB8E] = 2016  # Funky's ARMORY stencil
    elif model == 0x73:
        pair(0xB72, 0xB73)
        pair(0xB74, 0xB75)
    elif model == 0x124:
        pair(0xC7A, 0xC7B)  # Each side uses both halves of Candy's name
    elif model == 0x2AB:
        panels = dict.fromkeys(range(0x391, 0x394), 'quota')
    elif model == 0x2AD:
        panels = dict.fromkeys(range(0x3A3, 0x3A7), 'portal')
    elif model == 0x2AE:
        uv[0x391] = 992  # Same animated number plate for all eight locks
    elif 0x210 <= model <= 0x214:
        uv[(0xDF0, 0xDF3, 0xD45, 0xDF8, 0xDFB)[model-0x210]] = 992
    elif 0xF4 <= model <= 0x103:
        uv[0x1FE + 2*(model-0xF4)] = 992
    elif 0x14A <= model <= 0x14D:
        uv[(0x3A1, 0xAB1, 0x3CE, 0x3A6)[model-0x14A]] = 992
    elif 0x147 <= model <= 0x149:
        first = 0xCE0 + 4*(model-0x147)
        pair(first, first+1, 1504)
        pair(first+2, first+3, 1504)
    elif 0xA4 <= model <= 0xA7:
        halves = [(0xBBD,0xBBE), (0xBBF,0xBC0), (0xBBC,0xBC1), (0xBC2,0xBC3)]
        pair(*halves[model-0xA4])
    elif 0x247 <= model <= 0x24A:
        uv[(0xDFB,0xDF8,0xDF3,0xD45)[model-0x247]] = 992
    elif model == 0xDC:
        uv[0xC17] = 2016  # The four printed sides, CI4 with a separate palette
    return uv, swaps, panels


def fix_shared_corners(b, original, uses, edits):
    """A few switch faces share UVs with their bevel. Change the cached ST only
    between draws. Two TRI1 commands fit in one TRI2, leaving the model size,
    vertex loads, material addresses and animated texture slots intact.
    """
    transitions = []
    for v, draws in uses.items():
        if v not in edits or all(marked for _, _, marked in draws):
            continue
        assert edits[v][0] == 'u'
        extent = edits.pop(v)[1]
        u, t = struct.unpack_from('>hh', original, v + 8)
        first_marked = draws[0][2]
        if first_marked:
            struct.pack_into('>h', b, v+8, extent-u)
        changes = [(left, right) for left, right in zip(draws, draws[1:])
                   if left[2] != right[2]]
        assert len(changes) == 1
        old, new = changes[0]
        assert old[1] == new[1]
        # All shared corners in these small models cross one material boundary.
        transitions.append((old[0], new[0], old[1], extent-u if new[2] else u, t))
    if not transitions:
        return
    after = max(item[0] for item in transitions)
    before = min(item[1] for item in transitions)
    assert after < before and 1 not in original[after+8:before:8]
    n = len(transitions)
    # Pack the end of the old surface, or the start of the new surface.
    start = after - (2*n-1)*8
    suffix = all(b[k] == 5 for k in range(start,after+8,8))
    if not suffix:
        start = before
    assert all(b[k] == 5 for k in range(start,start+16*n,8))
    tris = []
    for k in range(start,start+16*n,16):
        tris.append(bytes([6])+b[k+1:k+4]+bytes([0])+b[k+9:k+12])
    mods = [struct.pack('>Ihh',0x02140000 | (slot*2),u,t)
            for _,_,slot,u,t in transitions]
    b[start:start+16*n] = b''.join(tris+mods if suffix else mods+tris)


def correct_labels(data, table, model):
    if table == 4 and model in (0x98, 0xEC, 0x1D2):
        # Camera film and both DK race coins. Their billboard quad stores
        # four raw ST pairs after the frame descriptor. The HUD owns its quad.
        b = bytearray(data)
        first_frame = 0x1AF if model == 0x98 else 0x1F0
        assert len(b) == 0x154 and struct.unpack_from('>H', data, 0x124)[0] == first_frame
        st = struct.unpack_from('>8h', data, 0x140)
        assert st == (1536, 0, 1536, 1344, -32, 1344, -32, 0)
        for i in range(4):
            struct.pack_into('>h', b, 0x140 + 4*i, 1504 - st[2*i])
        return bytes(b)
    if (table, model) in ((4, 316), (5, 0xA4), (5, 0xCC)):
        from key_geometry import PICKUP, BOSS_ACTOR, INSERTED, mirror_monogram
        glyph = PICKUP if table == 4 else (BOSS_ACTOR if model == 0xA4 else INSERTED)
        return mirror_monogram(data, glyph)
    if table == 4 and model in (0x196, 0x1CD, 0x235):
        from mirror_stars import two_sided_star
        return two_sided_star(data)
    uv, swaps, panels = rules(table, model)
    selected = uv.keys() | panels.keys()
    if not selected:
        return data
    b = bytearray(data)

    def word(p):
        return struct.unpack_from('>I', b, p)[0]

    if table == 4 or (table, model) == (27, 65):
        start, end = word(0x40), word(0x48)
        vertices = end
    else:
        end = 0x28 + word(4) - word(0)
        start = 0x28 + word(end) - word(0)
        vertices = 0x28

    slots, edits, seen = {}, {}, set()
    uses = {}
    material = None
    for p in range(start, end, 8):
        cmd, arg = struct.unpack_from('>II', data, p)
        op = cmd >> 24
        if op == 1:  # F3DEX2 G_VTX, relative to the model's vertex segment
            count = (cmd >> 12) & 255
            first = (cmd & 255)//2 - count
            for j in range(count):
                slots[first+j] = vertices + (arg & 0xFFFFFF) + 16*j
        elif op == 0xFD:
            # A TLUT load does not change the indexed image being drawn.
            if 0xF0 not in data[p+8:p+40:8]:
                material = arg
                if arg in swaps:
                    struct.pack_into('>I', b, p+4, swaps[arg])
            elif table == 4 and model in (0x11A, 0x11C) and arg-1 in swaps:
                struct.pack_into('>I', b, p+4, swaps[arg-1]+1)
        elif (op == 0xD7 and (cmd & 255) == 0) or op == 0xFC:
            # Reset at the start of a new material, including untextured trim.
            material = None
        elif op in (5, 6, 7):
            for word_offset, tri in ((0, cmd),) if op == 5 else ((0, cmd), (4, arg)):
                slots_used = [((tri >> shift) & 255)//2 for shift in (16, 8, 0)]
                panel = panels.get(material)
                marked = material in selected
                if panel == 'helm_back':
                    # Both sides use the same four prints. The hub-facing
                    # surface reads IV with the corrected print alone. Reflect
                    # the opposite face about local Z=0 to read IV there too.
                    xs = {struct.unpack_from('>h', data, slots[i])[0] for i in slots_used}
                    assert xs in ({-9}, {3})
                    marked = xs == {3}
                for slot in slots_used:
                    v = slots[slot]
                    uses.setdefault(v, []).append((p,slot,marked))
                    if not marked:
                        continue
                    seen.add(material)
                    edit = ('u', uv[material]) if material in uv else (panel,0)
                    prior_edit = edits.setdefault(v, edit)
                    assert prior_edit == edit
                if marked and panel:
                    # A second in-plane reflection restores native winding.
                    off = p + word_offset + 2
                    b[off], b[off+1] = b[off+1], b[off]
    fix_shared_corners(b, data, uses, edits)
    assert seen == selected, (table, model, seen, uv, panels)
    for v, (kind, extent) in edits.items():
        offset = v + (8 if kind == 'u' else 4 if kind == 'helm_back' else 0)
        old, = struct.unpack_from('>h', data, offset)
        if kind == 'u':
            value = extent - old
        elif kind == 'helm_back':
            value = -old
        elif kind == 'quota':
            value = 1 - old  # [-44,45], with matching digit boundaries
        else:
            value = 1 - old if old else 0  # portal tiles meet at local X=0
        struct.pack_into('>h', b, offset, value)
    return bytes(b)
