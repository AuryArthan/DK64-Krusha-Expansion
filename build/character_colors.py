"""Krusha identity effects derived from the approved startup silhouette."""
from collections import Counter
from pathlib import Path
import struct
from statistics import median
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SHOCKWAVE_TEXTURE_IDS = tuple(range(7003, 7009))


def identity_color():
    with Image.open(ROOT / 'bin/Nintendo_Krusha.png') as image:
        image = image.convert('RGB')
        # The rightmost head is Krusha. Ignore black/antialiased background.
        grays = Counter(p for p in image.crop((image.width-38, 0, image.width, image.height)).getdata()
                        if p[0] == p[1] == p[2] and p[0] >= 100)
    return grays.most_common(1)[0][0]


def shockwave_payloads(rom, read_file):
    # spawnActor uses one-based model numbers: model 0xAD is file 0xAC.
    assert struct.unpack_from('>I', rom, 0x101C50 + (32+5)*4)[0] == 0xEC
    model = bytearray(read_file(rom, 5, 0xAC))
    assert len(model) == 0x308
    native_ids = struct.unpack_from('>6H', model, 0x2FC)
    assert native_ids == tuple(range(0x1321, 0x1327))
    struct.pack_into('>6H', model, 0x2FC, *SHOCKWAVE_TEXTURE_IDS)
    # Keep the native authored hot rim/shadows and brightening over six frames.
    # Anchor frame zero's visible median to our identity silver; use the same
    # gain for every frame so animation brightness remains native.
    first = read_file(rom, 25, native_ids[0])
    luma = lambda r,g,b: .2126*r + .7152*g + .0722*b
    reference = median(luma(*first[i:i+3]) for i in range(0,len(first),4) if first[i+3])
    gain = identity_color()[0] / reference
    textures = []
    for index in native_ids:
        assert read_file(rom, 25, SHOCKWAVE_TEXTURE_IDS[index-native_ids[0]]) == b''
        texture = bytearray(read_file(rom, 25, index))
        assert len(texture) == 32*32*4  # Native RGBA32; retain every alpha byte.
        for offset in range(0, len(texture), 4):
            shade = min(255, round(luma(*texture[offset:offset+3]) * gain))
            texture[offset:offset+3] = bytes([shade]*3)
        textures.append(bytes(texture))
    return [bytes(model)] + textures


def write_identity_header():
    r,g,b = identity_color()
    assert r == g == b
    (ROOT/'include/krusha_identity.h').write_text(
        '/* Generated from bin/Nintendo_Krusha.png before C compilation. */\n'
        '#ifndef KRUSHA_IDENTITY_H\n#define KRUSHA_IDENTITY_H\n'
        f'#define KRUSHA_IDENTITY_GRAY {r}\n#endif\n')
