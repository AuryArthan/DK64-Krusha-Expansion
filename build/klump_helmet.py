"""Add a polished gold helmet spike to the private Big Klump actor model."""
import math
import struct


# The pad uses its four native base textures directly. Its first reserved
# private texture slot is available for the horn in both actor models.
HORN_TEXTURE = 7430


def horn_reflection(brass):
    from recruitment_keys import COLORS
    from recruitment_materials import metal_rgb, polished_lock_rgb

    assert len(brass) == 32 * 32 * 2
    texture = bytearray()
    for (pixel,) in struct.iter_unpack(">H", brass):
        rgb = tuple(pixel >> shift & 31 for shift in (11, 6, 1))
        gold = metal_rgb(rgb, COLORS[0])
        polished = polished_lock_rgb(rgb, COLORS[0])
        # Keep a narrow glint against the gold, using 30% of the lock's
        # added white and leaving the underlying reflection visible.
        r, g, b = (round(base + .30 * (bright - base)) for base, bright in zip(gold, polished))
        texture.extend(struct.pack(">H", r << 11 | g << 6 | b << 1 | pixel & 1))
    return bytes(texture)


def add_helmet_spike(model, lock_model):
    base, end_pointer = struct.unpack_from(">II", model)
    end = 40 + end_pointer - base
    start_pointer = struct.unpack_from(">I", model, end)[0]
    start = 40 + start_pointer - base
    insertion = 0x3270
    # Head bone 2 is active here and the very next native command replaces
    # all 32 RSP vertex slots. The horn can borrow the cache, then restore native shading.
    assert (start, end) == (0x3178, 0x54A8)
    assert model[insertion-8:insertion+8] == bytes.fromhex("da38000304000080 0102004003000290")
    crown = struct.unpack_from(">3h", model, 40 + 121 * 16)
    assert crown == (-4, 93, 6)

    vertices = bytearray()
    commands = bytearray()

    # The six outer rim points slope up toward Klump’s face. The fitted
    # plane has y = .0827*x + .2253*z + c. Rotate the entire spike around
    # its existing mounting point so its axis is the rim’s upward normal.
    def unit(v):
        length = math.hypot(*v)
        return tuple(n / length for n in v)

    def cross(a, b):
        return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])

    up = unit((-.0827, 1, -.2253))
    right = unit((1, .0827, 0))
    forward = cross(right, up)
    # Sink the whole 72-unit spike 4% along its axis. Quantize the offset
    # once so every vertex moves together on the model's integer grid.
    mount_depth = .04 * 72
    cx, cy, cz = (coord - round(mount_depth * axis) for coord, axis in zip(crown, up))

    def orient(x, y, z):
        return tuple(right[i]*x + up[i]*y + forward[i]*z for i in range(3))

    def ring(radius, height, rise, phase=0):
        for i in range(8):
            angle = math.tau * (i + phase) / 8
            x, z = math.cos(angle), math.sin(angle)
            dx, dy, dz = orient(radius*x, height, radius*z)
            normal = unit(orient(x, rise, z))
            vertices.extend(struct.pack(">3hH2h3bB", cx + round(dx), cy + round(dy),
                                        cz + round(dz), 0, 0, 0,
                                        *(round(127*n) for n in normal), 255))

    ring(22, -15, 0)
    ring(22, -2, .85)
    ring(12, 3, .28)
    # Eight coincident tips keep the highlight continuous along each facet.
    ring(0, 57, .28, .5)
    count = len(vertices) // 16
    assert count == 32

    # Use the yellow padlock’s reflective material with the horn's softer gold.
    # The lock delegates its tile size to segment 5. A fixed 32x32 tile needs
    # no lock-specific segment binding on the Klump actor.
    material = bytearray(lock_model[0x1060:0x10E8])
    assert struct.unpack_from(">II", material, 0x30) == (0xFD100000, 0xBAB)
    assert struct.unpack_from(">II", material, 0x68) == (0xDE000000, 0x05000000)
    # Klump's primitive tint can darken the lock highlight substantially.
    # First cycle draws the lock normally. The second lifts its RGB with
    # (1 - combined) * combined + combined, retaining full black and white
    # and the original alpha. Reuse the shell's opaque two-cycle mode.
    assert model[0x3338:0x3348] == bytes.fromhex("e3000a0100100000 e200001c0c192078")
    material[8:24] = model[0x3338:0x3348]
    assert struct.unpack_from(">II", material, 0x18) == (0xFC119623, 0xFF2FFFFF)
    # gsDPSetCombineLERP: native lock first cycle; second cycle RGB
    # (ONE, COMBINED, COMBINED, COMBINED), alpha passes COMBINED through.
    struct.pack_into(">II", material, 0x18, 0xFC1196C0, 0xF0FFFE38)
    struct.pack_into(">I", material, 0x34, HORN_TEXTURE)
    struct.pack_into(">II", material, 0x68, 0xF2000000, 0x0007C07C)
    commands.extend(material)
    load = 0x01000000 | (count << 12) | (count << 1)
    commands.extend(struct.pack(">II", load, 0x03000000 + start - 40))
    triangles = []
    for i in range(8):
        j = (i + 1) % 8
        for lower in (0, 8):
            a, b = lower + i, lower + j
            triangles.extend(((a, a + 8, b), (b, a + 8, b + 8)))
        triangles.append((16 + i, 24 + i, 16 + j))

    def indices(tri):
        a, b, c = tri
        return (a << 17) | (b << 9) | (c << 1)

    for i in range(0, len(triangles), 2):
        commands.extend(struct.pack(">II", 0x06000000 | indices(triangles[i]), indices(triangles[i + 1])))

    # Clear texture generation and lighting, then replay the original opaque
    # untextured setup before the native face vertices replace the cache.
    commands.extend(struct.pack(">II", 0xD9F9FFFF, 0))
    commands.extend(model[start:0x31B8])

    # Original segmented vertex references stay valid. Adjust the model's
    # absolute section pointers and its back-pointer to the display list.
    growth = len(vertices) + len(commands)
    result = bytearray(model[:start] + vertices + model[start:insertion] + commands + model[insertion:])
    for offset in (4, 8, 12, 16):
        pointer = struct.unpack_from(">I", model, offset)[0]
        assert pointer >= end_pointer
        struct.pack_into(">I", result, offset, pointer + growth)
    struct.pack_into(">I", result, end + growth, start_pointer + len(vertices))
    return bytes(result)
