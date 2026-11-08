"""Prepare Krusha's private Tiny victory bytecode from the verified USA ROM.

Tiny's opening two thirds lead into Disco Chunky's moving pointing stance.
Original script/resource tables are untouched; the scoped interpreter adapter
uses this resident copy and Krusha's own voice cues.
"""
from pathlib import Path
import hashlib, struct
from barrel_assets import read_file

ROOT=Path(__file__).resolve().parents[1]

def make_script(rom):
    assert hashlib.sha1(rom).hexdigest()=='cf806ff2603640a748fca5026ded28802f1f4a50'
    bank=read_file(rom,13,0)
    a,b=struct.unpack_from('>II',bank,0x173*4)
    script=bytearray(bank[a:b])
    assert len(script)==108 and script[:16].hex()=='243f800000000000001501d340000000'
    # Krusha's native tag-barrel selection/victory script uses voice 0x275.
    a,b=struct.unpack_from('>II',bank,0x43A*4)
    assert bytes.fromhex('3902750a') in bank[a:b]
    for voice in (0xB6,0xBA):
        needle=bytes([0x39,0,voice,0])
        assert script.count(needle)==1
        pos=script.index(needle)
        script[pos+1:pos+3]=struct.pack('>H',0x275)
    # Native boot-time Rap observation: Chunky actor200 changes raw2C9
    # (enter pointing pose) to2CA (animated/breathing hold). Use the latter,
    # not a frozen keyframe or the disco costume/model. Tiny's124-frame
    # victory keeps its first83 frames, followed by41 frames of the hold.
    cut=script.index(bytes.fromhex('0a429c0000'))  # original frame78 cue
    wait=lambda f:b'\x0a'+struct.pack('>f',f)
    cue=bytes.fromhex('39027500')
    script=script[:cut]+wait(78)+cue+wait(83)+bytes.fromhex('1502ca40000000')+wait(8)+cue+wait(41)+bytes.fromhex('4b0040002900')
    return script

def prepare(rom_path):
    script=make_script(Path(rom_path).read_bytes())
    text='/* Private Tiny opening + moving Disco Chunky ending, Krusha voices. */\n'
    text+='static const u8 krushaVictoryScript[] = {\n'
    text+=''.join('0x%02X,%s'%(v,'\n' if i%12==11 else ' ') for i,v in enumerate(script))+'\n};\n'
    (ROOT/'include/krusha_victory.generated.h').write_text(text)
