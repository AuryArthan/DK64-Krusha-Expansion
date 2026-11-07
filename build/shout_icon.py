"""Encode the supplied shout HUD portrait without changing shared face assets."""
from pathlib import Path
from PIL import Image
from barrel_assets import encode_face

def prepared_image():
    path=Path(__file__).resolve().parent.parent/'assets/krusha/hud/krusha-shout-source.png'
    with Image.open(path) as source:
        face=source.convert('RGBA').resize((48,48),Image.Resampling.LANCZOS)
    # Integer inset in the existing native geometry. Keep the counter anchor,
    # two-tile split and renderer scale; no new fractional draw-time scaling.
    result=Image.new('RGBA',(64,64),(0,0,0,0))
    result.paste(face,(8,8))
    return result

def payloads():
    path=Path(__file__).resolve().parent.parent/'assets/krusha/hud/krusha-shout-64.png'
    with Image.open(path) as image:
        assert image.convert('RGBA').tobytes()==prepared_image().tobytes(),'Regenerate the prepared shouting icon'
        return encode_face(image)
