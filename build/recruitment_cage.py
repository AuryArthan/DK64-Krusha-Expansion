"""Extend the private cage's upper bars straight beyond the owned camera frame.

Preserve all native body vertices and triangles. Continue each triangular bar
from its three Y659 endpoints along its original center line, at unchanged
thickness. There is no lid, connecting roof or change to the original cages.
"""
import math
import struct

MODEL = 222
MODEL_TOKEN = 250  # One-based actor token after the five independent keys.
COUNT = MODEL + 2
NATIVE_TIP_Y = 659
END_Y = 850


def bar_extensions(source):
    """Eight records of original tip vertices and a common linear displacement."""
    u = lambda off: struct.unpack_from('>I', source, off)[0]
    end = u(4) - u(0) + 40
    start = u(end) - u(0) + 40
    groups = {'joint': {}, 'tip': {}}
    for off in range(40, start, 16):
        x, y, z = struct.unpack_from('>3h', source, off)
        level = 'tip' if y == NATIVE_TIP_Y else 'joint' if y in (526, 534) else None
        if level is None:
            continue
        sector = round((math.atan2(z, x)*180/math.pi - 22.5)/45) % 8
        groups[level].setdefault(sector, {}).setdefault((x, y, z), source[off:off+16])
    assert all(len(g) == 8 and all(len(v) == 3 for v in g.values()) for g in groups.values())
    result = []
    for sector in range(8):
        # Follow the LAST native section above the upper rail. The longer
        # Y263->659 average flattens its inward bend and looks convex.
        lower, tip = groups['joint'][sector], groups['tip'][sector]
        center = lambda points: tuple(sum(p[i] for p in points)/3 for i in range(3))
        a, b = center(lower), center(tip)
        dx, dz = b[0]-a[0], b[2]-a[2]
        meeting_y = b[1] - (b[0]*dx+b[2]*dz)*(b[1]-a[1])/(dx*dx+dz*dz)
        assert 880 < meeting_y < 900 and END_Y < meeting_y
        factor = (END_Y - b[1])/(b[1] - a[1])
        delta = (round((b[0]-a[0])*factor), END_Y-NATIVE_TIP_Y,
                 round((b[2]-a[2])*factor))
        ring = sorted(tip, key=lambda p: math.atan2(p[2]-b[2], p[0]-b[0]))
        vertices = []
        for point in ring:
            start_vertex = tip[point]
            end_vertex = bytearray(start_vertex)
            struct.pack_into('>3h', end_vertex, 0, *(point[i]+delta[i] for i in range(3)))
            vertices.append((start_vertex, bytes(end_vertex)))
        result.append(dict(sector=sector, vertices=vertices, delta=delta,
                           last_joint=a, native_tip=b, meeting_y=meeting_y))
    return result


def extended_cage(source):
    """Append only side quads, using native metal, normals and skeleton."""
    u = lambda off: struct.unpack_from('>I', source, off)[0]
    base = u(0)
    end = u(4) - base + 40
    start = u(end) - base + 40
    assert len(source) == 6016 and (start, end) == (0xF18, 0x1490)
    assert source[end-16:end] == bytes.fromhex('d9f9ffff00000000df00000000000000')
    vertices = bytearray()
    for bar in bar_extensions(source):
        ring = bar['vertices']
        for i in range(3):
            a, b = ring[i]
            c, d = ring[(i+1) % 3]
            vertices += c+a+b+c+b+d  # Two outward-facing triangles per side.
    assert len(vertices) == 144*16
    commands = bytearray()
    for first in range(0, 144, 24):
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
    assert struct.unpack_from('>h', source, 30)[0] == NATIVE_TIP_Y
    struct.pack_into('>h', out, 30, END_Y)
    assert out[40:start] == source[40:start]
    assert out[start+len(vertices):end-16+len(vertices)] == source[start:end-16]
    assert out[end+delta+4:] == source[end+4:]
    return bytes(out)
