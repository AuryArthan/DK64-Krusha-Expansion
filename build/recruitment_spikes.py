"""Three small faceted orange/pink crown spikes for the private prison."""
import math


def triangles(tangent, normal):
    result = []
    for side in (-1, 0, 1):
        if side:
            heights, radii = (183, 240, 297), (29, 18)
            offsets = ((side * 76, 20), (side * 92, 16), (side * 112, -16))
        else:
            heights, radii = (211, 270, 335), (32, 20)
            offsets = ((0, 0), (0, -15), (0, -40))
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
