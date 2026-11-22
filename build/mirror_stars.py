"""Give the two sides of a mirrored DK challenge star independent lettering."""
import struct


def two_sided_star(data):
    # Model2's thirteen offsets at 0x40..0x70 delimit both display lists,
    # vertices and the remaining native sections. Vertex loads are relative
    # to segment 8, so moving the vertex section preserves their offsets.
    offsets = struct.unpack_from('>13I', data, 0x40)
    start, _, vertices = offsets[:3]
    assert start == 0x78 and offsets[-1] == len(data)
    output = bytearray(data[:start])
    slots = {}
    insertions = {}
    cull_back = False
    material = None
    seen = set()
    p = start
    while p < vertices:
        cmd, arg = struct.unpack_from('>II', data, p)
        op = cmd >> 24
        if op == 0xD9:
            cull_back = (cull_back and bool(cmd & 0x400)) or bool(arg & 0x400)
        elif op == 1:
            count = cmd >> 12 & 255
            first = (cmd & 255)//2 - count
            for j in range(count):
                slots[first+j] = struct.unpack_from('>hh', data, vertices+(arg & 0xffffff)+16*j+8)
        elif op == 0xFD:
            material = arg
        if op != 5 or material not in (0xD38, 0xD39):
            output.extend(data[p:p+8])
            p += 8
            continue
        # Keep the original mapping for the back. The front receives the
        # reflected S coordinates. Opposite windings and back-face culling
        # make exactly one print visible, even when viewed nearly edge-on.
        triangles = []
        used = set()
        before = len(output)
        begin = p
        while p < vertices and data[p] == 5:
            tri = data[p:p+8]
            triangles.append(tri)
            used.update(v//2 for v in tri[1:4])
            p += 8
        if not cull_back:
            output.extend(struct.pack('>II', 0xD9FFFFFF, 0x400))
        for tri in triangles:
            output.extend(tri[:2]+tri[2:4][::-1]+tri[4:])
        for slot in sorted(used):
            u, v = slots[slot]
            output.extend(struct.pack('>Ihh', 0x02140000 | slot*2, 2016-u, v))
        output.extend(b''.join(triangles))
        if not cull_back:
            output.extend(struct.pack('>II', 0xD9FFFBFF, 0))
        insertions[p] = len(output) - before - (p - begin)
        seen.add(material)
    assert seen == {0xD38, 0xD39}
    output.extend(data[vertices:])
    for i, offset in enumerate(offsets):
        delta = sum(n for pos,n in insertions.items() if pos <= offset)
        struct.pack_into('>I', output, 0x40+4*i, offset+delta)
    return bytes(output)
