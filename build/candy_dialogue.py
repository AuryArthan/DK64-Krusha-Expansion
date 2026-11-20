"""Append two private speech bubbles to Candy's original text bank."""
from pathlib import Path
import struct

LESSON_BEFORE = (
    "TEACH YOU TO PLAY?? SORRY HONEY, AIN'T NO WAY A HUMP OF MEAT LIKE YOU "
    "WILL EVER HIT A MUSICAL NOTE..."
)
LESSON_AFTER = (
    "WHAT A VOICE! YOU KNOW... THAT ROAR OF YOURS IS LIKELY JUST AS POWERFUL AS "
    "THE OTHER KONGS' INSTRUMENT ABILITIES. JUST PRESS AND HOLD",
    112,  # Native Z button sprite.
    "THEN PRESS",
    114,  # Native C-Up button sprite.
    "TO USE IT. HEADPHONES REFILL YOUR SHOUT ENERGY. AND NO NEED TO PAY ME A DIME "
    "HONEY, CONSIDER THIS VOICE LESSON ON ME."
)


def patch_candy_dialogue(filename):
    path = Path(filename)
    original = path.read_bytes()
    # Indices 22 and 23 are selected by m3QueueShopDialogue.
    assert original[0] == 22
    pos = 1
    for _ in range(original[0]):
        blocks = original[pos]
        pos += 1
        for _ in range(blocks):
            kind, segments = original[pos:pos + 2]
            assert kind in (1, 2)
            pos += 6 + segments * (8 if kind == 1 else 4)
    offset = struct.unpack_from('>H', original, pos)[0]
    assert pos + 2 + offset == len(original)
    text = bytearray(original[pos + 2:])
    boxes = bytearray()
    for lesson in ((LESSON_BEFORE,), LESSON_AFTER):
        boxes.append(len(lesson))
        for block in lesson:
            if isinstance(block, int):
                boxes += struct.pack('>BBHHI', 2, 1, block, 0, 0)
            else:
                encoded = block.encode('ascii')
                boxes += struct.pack('>BBIHHI', 1, 1, len(text), len(encoded), 0, 0)
                text.extend(encoded)
    path.write_bytes(bytes([original[0] + 2]) + original[1:pos] + boxes +
                     struct.pack('>H', len(text)) + text)
