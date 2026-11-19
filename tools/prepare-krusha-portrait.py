#!/usr/bin/env python3
"""Install supplied Krusha art, derive the native portrait and startup silhouette.

This is deterministic asset conversion, not image generation. Existing artwork
for the other Kongs and the 232x48 startup layout are preserved exactly.
"""
from pathlib import Path
import argparse,hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'build'))
from character_colors import identity_color
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
ASSETS=ROOT/'assets/krusha/barrel'
LOGO=ROOT/'bin/Nintendo_Krusha.png'

def prepare(source, gray=None):
    gray=identity_color()[0] if gray is None else gray
    assert 100<=gray<=255, 'Expected a visible gray palette value100..255'
    raw=source.read_bytes()
    with Image.open(source) as supplied:
        image=supplied.convert('RGBA')
    assert image.width==image.height and image.width>=64, 'Expected square source art at least 64x64'
    logo=Image.open(LOGO).convert('RGBA')
    assert logo.size==(232,48)
    # Retain the accepted lineup's last-head box, spacing and native pixel grid.
    # Threshold the source's almost-transparent PNG noise before downsampling
    # the silhouette. The portrait retains the supplied RGBA without this step.
    first_five=logo.crop((0,0,185,48)).tobytes()
    alpha=image.getchannel('A').point(lambda a:255 if a>=128 else 0)
    mask=alpha.resize((37,37),Image.Resampling.LANCZOS)
    logo.paste((0,0,0,255),(185,0,232,48))
    logo.paste(Image.new('RGBA',(37,37),(gray,gray,gray,255)),(188,5),mask)
    assert logo.crop((0,0,185,48)).tobytes()==first_five
    target=ASSETS/'krusha-face-source.png'
    if source.resolve()!=target.resolve():target.write_bytes(raw)
    portrait=image.resize((64,64),Image.Resampling.LANCZOS)
    portrait.save(ASSETS/'krusha-face-64.png')
    logo.save(LOGO)
    digest=hashlib.sha256(raw).hexdigest()
    old_metadata=ASSETS/'portrait-source.json'
    previous=json.loads(old_metadata.read_text()) if old_metadata.exists() else {}
    source_name=previous.get('source_filename',source.name) if previous.get('source_sha256')==digest else source.name
    metadata=dict(source_filename=source_name,source_sha256=digest,
                  source_dimensions=list(image.size),portrait_dimensions=[64,64],
                  portrait_sha256=hashlib.sha256((ASSETS/'krusha-face-64.png').read_bytes()).hexdigest(),
                  portrait_resampler='Pillow RGBA LANCZOS, full square; no cropping',
                  startup_dimensions=[232,48],startup_silhouette_box=[188,5,225,42],
                  startup_rgb=[gray,gray,gray],startup_mask='Source alpha >=128, then LANCZOS 37x37',
                  original_five_pixel_sha256=hashlib.sha256(first_five).hexdigest())
    (ASSETS/'portrait-source.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path,nargs='?',default=ASSETS/'krusha-face-source.png')
    p.add_argument('--gray',type=int,help='Override the current identity gray100..255')
    args=p.parse_args();prepare(args.source,args.gray)
