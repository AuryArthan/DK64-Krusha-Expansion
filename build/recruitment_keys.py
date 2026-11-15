"""Private rescue-key model2 pilot; no native boss-key actor or inventory ID."""
from pathlib import Path
import json, struct, zlib, math
from barrel_assets import read_file
ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'docs/planning/krusha-adventure-expansion/placements/recruitment-key-pilot.json'
MODEL_TYPE=60
MODEL=175
MIRROR=176

def rows():return json.loads(PLAN.read_text())['keys']

def prepare(rom_path):
    rom=Path(rom_path).read_bytes()
    assert not read_file(rom,4,MODEL_TYPE)
    for mid in range(221):
        b=read_file(rom,9,mid)
        if not b:continue
        n=struct.unpack_from('>I',b)[0]
        assert all(struct.unpack_from('>H',b,4+i*48+40)[0]!=MODEL_TYPE for i in range(n))
    static=zlib.decompress(rom[0xC29D4:],47);base=0x80744460
    native=static[0x80753EF0-base:0x80753EF0-base+42*20]
    assert all(struct.unpack_from('>H',native,i*20)[0]!=MODEL_TYPE for i in range(42))
    keys=rows();assert len(keys)==1, 'R09 is a single-owner pilot'
    for p in keys:
        assert p['id']=='RK-DK' and p['object_id']==401
        assert len(p['xyz'])==3 and all(math.isfinite(v)for v in p['xyz'])
        assert math.isfinite(p['scale'])and 0<p['scale']<1
        assert p['map']==34 and p['type']==MODEL_TYPE and p['owner']==0
        assert 0<=p['object_id']<530 and p['object_id']!=400
        b=read_file(rom,9,p['map']);n=struct.unpack_from('>I',b)[0]
        assert all(struct.unpack_from('>H',b,4+i*48+42)[0]!=p['object_id'] for i in range(n))
        assert all(not (static[0x80755A20-base+i*8]==p['map'] and struct.unpack_from('>H',static,0x80755A20-base+i*8+2)[0]==p['object_id']) for i in range(113))
        assert all(struct.unpack_from('>HH',static,0x80747D50-base+i*4)!=(p['map'],p['object_id']) for i in range(8))
        script=read_file(rom,10,p['map'])
        # Reject any reference to the chosen ID, even in another operand role.
        assert p['object_id'] not in struct.unpack('>%dH'%(len(script)//2),script[:len(script)//2*2])
    h='/* Generated R09 private key identities; not boss-key/colored-save IDs. */\n'
    h+=f'#define RECRUITMENT_KEY_TYPE {MODEL_TYPE}\n#define RECRUITMENT_KEY_MODEL {MODEL}\n#define RECRUITMENT_KEY_MIRROR {MIRROR}\n'
    h+='static const struct { unsigned short map, object_id; unsigned char owner; } recruitmentKeys[] = {\n'
    h+=''.join('    {%d,%d,%d},\n'%(p['map'],p['object_id'],p['owner'])for p in rows())+'};\n'
    (ROOT/'include/recruitment_keys.generated.h').write_text(h)

def patch_setup(filename,mid):
    keys=[p for p in rows()if p['map']==mid]
    if not keys:return
    path=Path(filename);data=path.read_bytes();n=struct.unpack_from('>I',data)[0]
    ids={struct.unpack_from('>H',data,4+i*48+42)[0]for i in range(n)}
    rom=(ROOT/'rom/dk64.z64').read_bytes();donor=read_file(rom,9,17)
    template=next(donor[4+i*48:4+(i+1)*48]for i in range(struct.unpack_from('>I',donor)[0])if struct.unpack_from('>H',donor,4+i*48+40)[0]==316)
    extra=bytearray()
    for p in keys:
        assert p['object_id'] not in ids;ids.add(p['object_id'])
        rec=bytearray(template);struct.pack_into('>4f',rec,0,*p['xyz'],p['scale'])
        struct.pack_into('>3f',rec,24,0,0,0)
        struct.pack_into('>HH',rec,40,MODEL_TYPE,p['object_id']);extra+=rec
    path.write_bytes(struct.pack('>I',n+len(keys))+data[4:4+n*48]+extra+data[4+n*48:])

def payloads(rom):
    from mirror_assets import flip
    normal=read_file(rom,4,316)
    mirrored,count=flip(normal,4)
    assert count>0 and len(normal)==len(mirrored)
    return [normal,mirrored]
