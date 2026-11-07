"""Encode the supplied shout HUD portrait without changing shared face assets."""
from pathlib import Path
from PIL import Image
from barrel_assets import encode_face

def payloads():
    path=Path(__file__).resolve().parent.parent/'assets/krusha/hud/krusha-shout-64.png'
    with Image.open(path) as image:
        return encode_face(image)
