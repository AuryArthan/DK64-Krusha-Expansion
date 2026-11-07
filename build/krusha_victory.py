"""Prepare Krusha's private Tiny victory bytecode from the verified USA ROM.

Only the two Tiny voice instructions change. Original script/resource tables
are untouched; Krusha's scoped interpreter adapter uses this resident copy.
"""
from pathlib import Path
import hashlib, struct
from barrel_assets import read_file

ROOT=Path(__file__).resolve().parents[1]

def prepare(rom_path):
    rom=Path(rom_path).read_bytes()
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
    text='/* Generated from verified USA Tiny GB script, Krusha-only voices. */\n'
    text+='static const u8 krushaVictoryScript[] = {\n'
    text+=''.join('0x%02X,%s'%(v,'\n' if i%12==11 else ' ') for i,v in enumerate(script))+'\n};\n'
    (ROOT/'include/krusha_victory.generated.h').write_text(text)
