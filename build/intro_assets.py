"""Native-size intro textures, derived without redrawing the supplied artwork."""
from pathlib import Path
from PIL import Image
from mirror_assets import read_file


def prepare(rom):
    assets = Path('assets/intro')
    # Keep every pixel of the author's 99x79 pixel-art logo. Pad to a
    # four-texel row boundary for RGBA16; render at one native pixel per texel.
    arth = Image.open(assets / 'arthan-source.png').convert('RGBA')
    assert arth.size == (99, 79)
    padded = Image.new('RGBA', (100, 80))
    padded.paste(arth, (0, 0))
    padded.save('bin/Arthan.png')

    # Extract the clean vanilla logo from the supplied USA ROM. The upstream
    # Title.png has the old banner painted across its lower-left corner.
    data = read_file(Path(rom).read_bytes(), 14, 44)
    assert len(data) == 224 * 128 * 2
    pixels = []
    for pos in range(0, len(data), 2):
        value = int.from_bytes(data[pos:pos+2], 'big')
        pixels.append(((value >> 11) * 255 // 31,
                       ((value >> 6) & 31) * 255 // 31,
                       ((value >> 1) & 31) * 255 // 31, 255 * (value & 1)))
    vanilla = Image.new('RGBA', (224, 128))
    vanilla.putdata(pixels)
    title = vanilla.copy()
    expansion = Image.open(assets / 'expansion-source.png').convert('RGBA')
    assert expansion.size == (2172, 724)
    title.alpha_composite(expansion.resize((96, 32), Image.Resampling.LANCZOS), (24, 96))
    # The ROM's RGBA5551 has binary alpha. Explicit coverage threshold avoids
    # turning faint resampling fringes into opaque dark speckles.
    title.putalpha(title.getchannel('A').point(lambda a: 255 if a >= 128 else 0))
    title.save('bin/ExpansionTitle.png')
