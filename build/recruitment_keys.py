"""Five private rescue-key model2 resources; no native boss-key actor or inventory ID."""
from pathlib import Path
import json, struct, zlib, math
from barrel_assets import read_file
ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'data/placements/recruitment-keys.json'
# R09 slots175/176 remain immutable. New materials/geometry append after them.
MODEL_TYPES=(60,62,63,64,65)
MODEL=177
PALETTE=187
PALETTE_TOKEN=7840
COLORS=((255,220,45),(245,45,45),(50,105,255),(205,65,245),(65,220,80))
MODEL_TYPE=MODEL_TYPES[0] # historical DK-only diagnostics
MIRROR=MODEL+1

def rows():return json.loads(PLAN.read_text())['keys']

def prepare(rom_path):
    rom=Path(rom_path).read_bytes()
    for typ in MODEL_TYPES:
        assert not read_file(rom,4,typ)
        for mid in range(221):
            b=read_file(rom,9,mid)
            if not b:continue
            n=struct.unpack_from('>I',b)[0]
            assert all(struct.unpack_from('>H',b,4+i*48+40)[0]!=typ for i in range(n))
    for token in range(PALETTE_TOKEN,PALETTE_TOKEN+5):assert not read_file(rom,25,token)
    static=zlib.decompress(rom[0xC29D4:],47);base=0x80744460
    native=static[0x80753EF0-base:0x80753EF0-base+42*20]
    assert all(struct.unpack_from('>H',native,i*20)[0]not in MODEL_TYPES for i in range(42))
    keys=rows();assert len(keys)==5 and {p['owner']for p in keys}==set(range(5))
    assert len({p['id']for p in keys})==len({p['object_id']for p in keys})==5
    for p in keys:
        assert p['id']==('RK-DK','RK-DIDDY','RK-LANKY','RK-TINY','RK-CHUNKY')[p['owner']]
        assert p['object_id']==401+p['owner']
        assert len(p['xyz'])==3 and all(math.isfinite(v)for v in p['xyz'])
        assert math.isfinite(p['scale'])and 0<p['scale']<1
        assert p['map']==34 and p['type']==MODEL_TYPES[p['owner']]
        assert 0<=p['object_id']<530 and p['object_id']!=400
        b=read_file(rom,9,p['map']);n=struct.unpack_from('>I',b)[0]
        assert all(struct.unpack_from('>H',b,4+i*48+42)[0]!=p['object_id'] for i in range(n))
        assert all(not (static[0x80755A20-base+i*8]==p['map'] and struct.unpack_from('>H',static,0x80755A20-base+i*8+2)[0]==p['object_id']) for i in range(113))
        assert all(struct.unpack_from('>HH',static,0x80747D50-base+i*4)!=(p['map'],p['object_id']) for i in range(8))
        script=read_file(rom,10,p['map'])
        # Reject any reference to the chosen ID, even in another operand role.
        assert p['object_id'] not in struct.unpack('>%dH'%(len(script)//2),script[:len(script)//2*2])
    h='/* Generated R10 private key identities, separate from native rewards. */\n'
    from recruitment_key_sound import payload as sound
    h+=f'#define RECRUITMENT_KEY_PALETTE_TOKEN {PALETTE_TOKEN}\n#define RECRUITMENT_KEY_PALETTE {PALETTE}\n#define RECRUITMENT_KEY_COUNT 5\n#define RECRUITMENT_KEY_SOUND_ASSET 229\n#define RECRUITMENT_KEY_SOUND_BYTES {len(sound(rom))}\n'
    h+='static const struct { unsigned short map, object_id, type, model, mirror; unsigned char owner; } recruitmentKeys[] = {\n'
    h+=''.join('    {%d,%d,%d,%d,%d,%d},\n'%(p['map'],p['object_id'],p['type'],MODEL+p['owner']*2,MODEL+p['owner']*2+1,p['owner'])for p in keys)+'};\n'
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
        struct.pack_into('>HH',rec,40,p['type'],p['object_id']);extra+=rec
    path.write_bytes(struct.pack('>I',n+len(keys))+data[4:4+n*48]+extra+data[4+n*48:])

def payloads(rom):
    from mirror_assets import flip
    from recruitment_materials import metal_rgb
    normal=read_file(rom,4,316)
    mirrored,count=flip(normal,4);assert count>0
    result=[normal,mirrored] # approved R09 assets remain byte-exact
    from key_geometry import PICKUP, resize_pickup, mirror_monogram
    resized = resize_pickup(normal)
    for owner in range(5):
        model=bytearray(resized)
        assert struct.unpack_from('>II',model,0xC0)==(0xE200001C,0x0C192038)
        # Keep render-mode selection in the per-instance draw adapter. A
        # primitive-alpha blend works without the native fog-alpha shortcut.
        struct.pack_into('>II',model,0xC0,0,0)
        assert struct.unpack_from('>II',model,0xE0)==(0xFCFFFFFF,0xFFFCF238)
        struct.pack_into('>I',model,0xE4,0xFFFCF63B) # both cycles alpha=PRIMITIVE
        assert struct.unpack_from('>II',model,0x128)==(0xFD100000,0xC6F)
        struct.pack_into('>I',model,0x12C,PALETTE_TOKEN+owner)
        alternate,n=flip(bytes(model),4);assert n==count
        result.extend([bytes(model),mirror_monogram(alternate, PICKUP)])
    palette=read_file(rom,25,0xC6F);assert len(palette)==32
    for owner,target in enumerate(COLORS):
        out=bytearray()
        for (v,)in struct.iter_unpack('>H',palette):
            rgb=(v>>11&31,v>>6&31,v>>1&31)
            red,green,blue=metal_rgb(rgb,target)
            out+=struct.pack('>H',red<<11|green<<6|blue<<1|v&1)
        result.append(bytes(out))
    assert len(result)==17
    return result
