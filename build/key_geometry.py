"""USA key meshes. The DK monogram is geometry inside the bow."""
import struct

# Half-open vertex ranges in the three native key layouts. The private
# prison key keeps the padlock's original vertices before its added bit.
PICKUP = (0x1718, 0x1B78)
BOSS_ACTOR = (0xD38, 0x11C8)
INSERTED = (0x7E8, 0x9C8)
OVERALL_SCALE = 0.95
SHAFT_SCALE = 1.10
HEAD_SCALE = 1.15
HANDLE_SCALE = 1.05


def along_key(value, tip, lower_joint, upper_joint, bow):
    """Scale each end about its outer endpoint; join them with a shorter shaft."""
    lower = tip + (lower_joint - tip) * HEAD_SCALE
    upper = bow + (upper_joint - bow) * HANDLE_SCALE
    assert lower < upper
    if value <= lower_joint:
        return tip + (value - tip) * HEAD_SCALE
    if value >= upper_joint:
        return bow + (value - bow) * HANDLE_SCALE
    return lower + (value - lower_joint) * (upper - lower) / (upper_joint - lower_joint)


def resize_pickup(data):
    # The eight vertices following the mesh are its display bounds.
    start, end = struct.unpack_from('>II', data, 0x48)
    assert (start, end) == (0xBD8, 0x1BF8)
    out = bytearray(data)
    bounds = end - 8*16
    for p in range(start, bounds, 16):
        x, y, z = struct.unpack_from('>3h', data, p)
        # The long shaft has its own vertices, interlocking with both collars.
        scale = HANDLE_SCALE
        if 0x12F8 <= p < 0x1608:  # Lower collar and teeth.
            scale = HEAD_SCALE
        elif 0x1608 <= p < 0x1718:
            scale = SHAFT_SCALE
        scale *= OVERALL_SCALE
        struct.pack_into('>3h', out, p, round(.5 + (x-.5)*scale),
                         round(OVERALL_SCALE * along_key(y, 0, 110, 196, 341)), round(.5 + (z-.5)*scale))
    # Width comes from the bow and depth from a collar. Refit the box to
    # the finished mesh so both caps keep the same culling extents.
    axes = list(zip(*(struct.unpack_from('>3h', out, p) for p in range(start, bounds, 16))))
    for p in range(bounds, end, 16):
        corner = struct.unpack_from('>3h', data, p)
        xyz = [max(axis) if side > 0 else min(axis) for side, axis in zip(corner, axes)]
        struct.pack_into('>3h', out, p, *xyz)
    return bytes(out)


def resize_inserted(data):
    # Bone 3 points along Z. Leave the lock/shackle, skeleton and all
    # matrices in their original space. The extra tooth mesh starts at D08.
    out = bytearray(data)
    for start, end in ((0x68, 0x9C8), (0xD08, 0xD08+108*16)):
        for p in range(start, end, 16):
            x, y, z = struct.unpack_from('>3h', data, p)
            scale = HEAD_SCALE if p >= 0xD08 else HANDLE_SCALE
            if 0x728 <= p < 0x7E8:
                scale = SHAFT_SCALE
            scale *= OVERALL_SCALE
            # Shrink toward the inserted tip so it still seats in the lock.
            depth = along_key(z, -112, 8, 149, 393)
            struct.pack_into('>3h', out, p, round(x*scale), round(y*scale),
                             round(-112 + OVERALL_SCALE * (depth + 112)))
    return bytes(out)


def mirror_monogram(data, glyph):
    """Reflect the glyph, its vertex normals and just its triangles' winding."""
    out = bytearray(data)
    first, end = glyph
    transverse = 1 if glyph == INSERTED else 0
    # The pickup's rim is centred at X=0.5. The skeletal keys use zero.
    twice_center = 1 if glyph == PICKUP else 0
    for p in range(first, end, 16):
        axis = p + 2*transverse
        value, = struct.unpack_from('>h', data, axis)
        struct.pack_into('>h', out, axis, twice_center-value)
        normal = p + 12 + transverse
        n, = struct.unpack_from('>b', data, normal)
        struct.pack_into('>b', out, normal, min(127, -n))

    word = lambda p: struct.unpack_from('>I', data, p)[0]
    if glyph == PICKUP:
        start, vertices = word(0x40), word(0x48)
        stop = vertices
    else:
        vertices = 40
        stop = vertices + word(4) - word(0)
        start = vertices + word(stop) - word(0)
    slots = {}
    seen = set()
    for p in range(start, stop, 8):
        cmd, arg = struct.unpack_from('>II', data, p)
        if cmd >> 24 == 1:
            count = (cmd >> 12) & 255
            dest = (cmd & 255)//2 - count
            for i in range(count):
                slots[dest+i] = vertices + (arg & 0xFFFFFF) + 16*i
        elif cmd >> 24 in (5, 6):
            for tri in ((p,) if cmd >> 24 == 5 else (p, p+4)):
                verts = [slots[n//2] for n in data[tri+1:tri+4]]
                if first <= verts[0] < end:
                    assert all(first <= v < end for v in verts)
                    seen.update(verts)
                    out[tri+2], out[tri+3] = out[tri+3], out[tri+2]
                else:
                    assert all(v < first or v >= end for v in verts)
    assert seen == set(range(first, end, 16))
    return bytes(out)
