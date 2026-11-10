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
    # Eight transparent rows above and below keep the vanilla screen anchor.
    title = Image.new('RGBA', (224, 144))
    title.paste(vanilla, (0, 8))
    expansion = Image.open(assets / 'expansion-source.png').convert('RGBA')
    assert expansion.size == (2172, 724)
    # Exact 1.36 enlargement about the old (72,112) midpoint, now(72,120)
    # after padding. A25x local grid represents130.56x43.52 exactly while
    # retaining LANCZOS filtering and whole native texel output.
    patch = Image.new('RGBA', (132*25, 46*25))
    patch.alpha_composite(expansion.resize((3264, 1088), Image.Resampling.LANCZOS), (18, 31))
    title.alpha_composite(patch.resize((132, 46), Image.Resampling.LANCZOS), (6, 97))
    # The ROM's RGBA5551 has binary alpha. Explicit coverage threshold avoids
    # turning faint resampling fringes into opaque dark speckles.
    title.putalpha(title.getchannel('A').point(lambda a: 255 if a >= 128 else 0))
    title.save('bin/ExpansionTitle.png')
