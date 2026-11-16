"""Closed metal lid for the private recruitment cage, using its native material.

Keep every original vertex, bone and body triangle. Insert a small watertight
octagonal cap above the eight native post tips; native cages remain unchanged.
The shallow raised center leaves headroom and gives the roof a readable profile.
"""
import math
import struct

MODEL = 222
MODEL_TOKEN = 250  # One-based actor token after the five independent keys.
COUNT = MODEL + 2
RIM_Y = 659
PEAK_Y = 733
THICKNESS = 8
CORNERS = ((174, 72), (72, 174), (-72, 174), (-174, 72),
           (-174, -72), (-72, -174), (72, -174), (174, -72))


def roof_triangles():
    upper = [(x, RIM_Y + THICKNESS, z) for x, z in CORNERS]
    lower = [(x, RIM_Y, z) for x, z in CORNERS]
    result = []
    for i in range(8):
        j = (i + 1) % 8
        result.extend((((0, PEAK_Y, 0), upper[j], upper[i]),
                       ((0, PEAK_Y - THICKNESS, 0), lower[i], lower[j]),
                       (upper[i], upper[j], lower[j]),
                       (upper[i], lower[j], lower[i])))
    # Every geometric edge belongs to exactly two faces in opposite directions.
    edges = {}
    for tri in result:
        for a, b in zip(tri, tri[1:] + tri[:1]):
            key = tuple(sorted((a, b)))
            edges.setdefault(key, []).append((a, b))
    assert all(len(v) == 2 and v[0] == v[1][::-1] for v in edges.values())
    return result


def closed_cage(source):
    """Relocate the native actor layout, retaining its material and skeleton."""
    u = lambda off: struct.unpack_from('>I', source, off)[0]
    base = u(0)
    end = u(4) - base + 40
    start = u(end) - base + 40
    assert len(source) == 6016 and (start, end) == (0xF18, 0x1490)
    assert source[end-16:end] == bytes.fromhex('d9f9ffff00000000df00000000000000')
    vertices = bytearray()
    for tri in roof_triangles():
        a, b, c = tri
        ab, ac = [[p[i] - a[i] for i in range(3)] for p in (b, c)]
        normal = [ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2],
                  ab[0]*ac[1]-ab[1]*ac[0]]
        length = math.sqrt(sum(v*v for v in normal))
        normal = [round(v / length * 127) for v in normal]
        for point in tri:
            vertices += struct.pack('>3hH2h3bB', *point, 0, 0, 0, *normal, 255)
    commands = bytearray()
    # Reuse the already-bound native metal texture, lighting and texture-gen.
    for first in range(0, 96, 24):
        commands += struct.pack('>II', 0x01018030, 0x03000000 + start - 40 + first*16)
        for index in range(0, 24, 6):
            commands += struct.pack('>II', 0x06000000 | index*2 << 16 |
                                    (index+1)*2 << 8 | (index+2)*2,
                                    (index+3)*2 << 16 | (index+4)*2 << 8 | (index+5)*2)
    delta = len(vertices) + len(commands)
    out = bytearray(source[:start] + vertices + source[start:end-16] + commands + source[end-16:])
    for offset in (4, 8, 12, 16):
        assert u(offset) >= base + end - 40
        struct.pack_into('>I', out, offset, u(offset) + delta)
    struct.pack_into('>I', out, end + delta, u(end) + len(vertices))
    # Native model's vertical extent, not an actor/collision dimension.
    assert struct.unpack_from('>h', source, 30)[0] == RIM_Y
    struct.pack_into('>h', out, 30, PEAK_Y)
    assert out[40:start] == source[40:start]
    assert out[start+len(vertices):end-16+len(vertices)] == source[start:end-16]
    assert out[end+delta+4:] == source[end+4:]
    return bytes(out)
