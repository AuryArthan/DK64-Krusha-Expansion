"""Private silver native locked-barrel model; original actors/assets stay intact."""
from pathlib import Path
import struct
from character_colors import identity_color

MODEL = 170
TEXTURE = 171
MIRROR = 172
MODEL_TOKEN = 0xEF  # One-based; file0xEE follows the private Klump file0xED.
TEXTURE_TOKEN = 7830


def prepare():
    root = Path(__file__).resolve().parents[1]
    (root / 'include/recruitment_barrel.generated.h').write_text(
        '/* Generated private R07 locked-barrel identities. */\n'
        f'#define RECRUITMENT_BARREL_MODEL {MODEL}\n'
        f'#define RECRUITMENT_BARREL_TEXTURE {TEXTURE}\n'
        f'#define RECRUITMENT_BARREL_MIRROR {MIRROR}\n'
        f'#define RECRUITMENT_BARREL_MODEL_TOKEN {MODEL_TOKEN}\n'
        f'#define RECRUITMENT_BARREL_TEXTURE_TOKEN {TEXTURE_TOKEN}\n')


def payloads(rom):
    from barrel_assets import read_file
    from mirror_assets import flip
    assert not read_file(rom, 25, TEXTURE_TOKEN), 'R07 texture token must be unused'
    model = bytearray(read_file(rom, 5, 0xD1))
    base, texture_list = struct.unpack_from('>I', model)[0], struct.unpack_from('>I', model, 16)[0]
    offset = texture_list - base + 40
    assert model[offset:] == struct.pack('>4H6H', 1, 5, 12, 1, *range(0x135C, 0x1361), 0)
    # All five legal native palette selections use the same silver texture.
    # The sixth display actor carries palette index0, never native index5.
    struct.pack_into('>5H', model, offset + 8, *([TEXTURE_TOKEN] * 5))
    native = read_file(rom, 25, 0x1360)
    pixels = list(struct.unpack('>1024H', native))
    luminance = lambda v: ((v >> 11) & 31) * .2126 + ((v >> 6) & 31) * .7152 + ((v >> 1) & 31) * .0722
    peak = max(luminance(v) for v in pixels if v & 1)
    target = identity_color()[0]
    def silver(v):
        gray = max(0, min(31, round(luminance(v) / peak * target * 31 / 255)))
        return (gray << 11) | (gray << 6) | (gray << 1) | (v & 1)
    texture = struct.pack('>1024H', *(silver(v) for v in pixels))
    mirrored, count = flip(bytes(model), 5)
    assert count > 0 and len(mirrored) == len(model)
    return [bytes(model), texture, mirrored]
