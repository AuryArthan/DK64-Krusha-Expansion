"""Three small faceted orange/pink crown spikes for the private prison."""
import math
ENLARGEMENT = 1.10 * 1.15 * 1.05
# Three world units. The widest enlarged root ring otherwise floats over the
# curved roof at its outer edge. All eight vertices must enter the roof, rather
# than merely placing the centre of the horn on it. Independently mesh-audited.
LOWERING = 13


def triangles(tangent, normal):
    result = []
    # Forehead to nape, on the mouth's normal axis. The largest is near
    # the dome summit; the two smaller horns descend along its back.
    for heights,radii,depths in (
        ((211,270,335),(32,20),(20,8,-10)),
        ((190,235,282),(26,16),(-65,-78,-95)),
        ((135,177,220),(20,12),(-133,-145,-161)),
    ):
        root=heights[0]
        heights=tuple(root+(height-root)*ENLARGEMENT-LOWERING for height in heights)
        radii=tuple(radius*ENLARGEMENT for radius in radii)
        offsets=tuple((0,n)for n in depths)
        centers = [(tangent[0] * t + normal[0] * n, y,
                    tangent[1] * t + normal[1] * n)
                   for y, (t, n) in zip(heights, offsets)]
        rings = [[(c[0] + radius * math.cos(j * math.pi / 4), c[1],
                   c[2] + radius * math.sin(j * math.pi / 4)) for j in range(8)]
                 for c, radius in zip(centers, radii)]
        colors = ((226, 113, 76), (244, 145, 114), (255, 181, 169))
        for j in range(8):
            k = (j + 1) % 8
            faces = ((rings[0][j], rings[1][k], rings[0][k]),
                     (rings[0][j], rings[1][j], rings[1][k]),
                     (rings[1][j], centers[2], rings[1][k]))
            levels = ((0, 1, 0), (0, 1, 1), (1, 2, 1))
            for points, indices in zip(faces, levels):
                vertex_colors = []
                for point, level in zip(points, indices):
                    angle = math.atan2(point[2] - centers[level][2],
                                       point[0] - centers[level][0])
                    shade = .98 if level == 2 else .68 + .32 * max(0, math.cos(angle - .8))
                    vertex_colors.append(tuple(round(c * shade) for c in colors[level]))
                result.append((points, vertex_colors))
    assert len(result) == 72
    return result
