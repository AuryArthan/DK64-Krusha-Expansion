"""Baked metal highlights for private recruitment keys and locks only.

Use the source texture's luminance to preserve its existing reflective detail.
No environment mapping, new textures, particle emitters or native-palette edits.
"""
import colorsys


def metal_rgb(rgb, target):
    hue, saturation, _ = colorsys.rgb_to_hsv(*(c / 255 for c in target))
    value = max(rgb) / 31
    light = sum(c * w for c, w in zip(rgb, (.2126, .7152, .0722))) / 31
    highlight = max(0, (light - .58) / .42) ** 1.5 * .65
    base = colorsys.hsv_to_rgb(hue, saturation, value)
    return tuple(round(31 * (c * (1 - highlight) + value * highlight)) for c in base)


def polished_lock_rgb(rgb, target):
    """Broaden the native brass reflection's bright core into a silver glint."""
    base = metal_rgb(rgb, target)
    # The brass map tops out at yellow. Its green channel distinguishes the
    # hottest part of the reflection from saturated orange around its rim.
    t = min(1.0, max(0.0, (rgb[1] / 31 - .43) / .47))
    specular = .90 * t * t * (3 - 2 * t)
    return tuple(round(channel + (31 - channel) * specular) for channel in base)
