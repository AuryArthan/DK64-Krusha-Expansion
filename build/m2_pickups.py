"""M2 native pickup pilot. Private types never alter native save-bit counts."""
from pathlib import Path
import json, struct, zlib
from barrel_assets import read_file
ROOT=Path(__file__).resolve().parent.parent
PLAN=ROOT/'docs/planning/krusha-adventure-expansion/placements/assistant-draft-v1.json'
# Japes pilot registry; the three-object contact proof is preserved under runtime/.
GROUND_SLOTS=tuple(range(10))+tuple(range(13,33))+tuple(range(231,241))
BALLOON_SLOTS=(10,11,12)
KINDS={'single':(2,13,7100,8),'bunch':(4,43,7201,12),'coin':(6,29,7108,8)}

def plan_pins():
    return {p['pickup_slot']:p for p in json.loads(PLAN.read_text())['pins'] if 'pickup_slot' in p}

def rows():
    pins=plan_pins()
    rom=(ROOT/'rom/dk64.z64').read_bytes();setup=read_file(rom,9,7);n=struct.unpack_from('>I',setup)[0]
    used={struct.unpack_from('>H',setup,4+i*48+42)[0] for i in range(n)}
    script=read_file(rom,10,7);refs=set(struct.unpack('>%dH'%(len(script)//2),script[:len(script)//2*2]))
    free=[i for i in range(505,530) if i not in used and i not in refs]+[i for i in range(505) if i not in used and i not in refs]
    assert len(free)>=len(GROUND_SLOTS)
    return [dict(pins[slot],object_id=free[i],type=KINDS[pins[slot]['kind']][0]) for i,slot in enumerate(GROUND_SLOTS)]

def balloons():
    pins=plan_pins()
    # Japes has paths0..21. Native path lookup has only26 entries.
    return [dict(pins[slot],spawner_id=600+i,path_id=22+i) for i,slot in enumerate(BALLOON_SLOTS)]

def prepare(rom_path):
    rom=Path(rom_path).read_bytes();setup=read_file(rom,9,7)
    n=struct.unpack_from('>I',setup)[0]
    ids={struct.unpack_from('>H',setup,4+i*48+42)[0] for i in range(n)}
    for p in rows():assert 0<=p['object_id']<530 and p['object_id'] not in ids
    for kind,(typ,source,first,count) in KINDS.items():
        assert read_file(rom,4,typ)==b''
        for m in range(216):
            data=read_file(rom,9,m)
            if not data:continue
            num=struct.unpack_from('>I',data)[0]
            assert all(struct.unpack_from('>H',data,4+i*48+40)[0]!=typ for i in range(num))
    data=zlib.decompress(rom[0xC29D4:],47)
    # Suction also consults native per-object flag/owner metadata. A free setup
    # ID must not accidentally reuse one of those hardcoded Japes identities.
    special={struct.unpack_from('>H',data,0x80755A20-0x80744460+i*8+2)[0]
             for i in range(113) if data[0x80755A20-0x80744460+i*8]==7}
    special|={struct.unpack_from('>H',data,0x80747D50-0x80744460+i*4+2)[0]
              for i in range(8) if struct.unpack_from('>H',data,0x80747D50-0x80744460+i*4)[0]==7}
    assert not special & {p['object_id'] for p in rows()}
    native=data[0x80753EF0-0x80744460:0x80753EF0-0x80744460+42*20]
    defs=bytearray(native)
    for kind,row in [('single',0),('bunch',10),('coin',9)]:
        value=bytearray(native[row*20:(row+1)*20]);struct.pack_into('>H',value,0,KINDS[kind][0]);struct.pack_into('>hh',value,12,7,0);defs+=value
    # M3's dynamic private blueprint; native actor scanning still stops at42.
    blueprint=bytearray(native[26*20:27*20])
    struct.pack_into('>H',blueprint,0,7);struct.pack_into('>hh',blueprint,12,7,0);defs+=blueprint
    words=struct.unpack('>230I',defs)
    header='/* Generated from verified original USA data by build/m2_pickups.py. */\n'
    header+='const u32 m2CollectDefs[230] = {\n'+''.join('0x%08X,%s'%(w,'\n' if i%5==4 else ' ') for i,w in enumerate(words))+'};\n'
    header+='static const struct { u16 slot, object_id, type; u8 units, coin; } m2Pickups[] = {\n'
    for p in rows():header+='    {%d,%d,%d,%d,%d},\n'%(p['pickup_slot'],p['object_id'],p['type'],{'single':1,'bunch':5,'coin':0}[p['kind']],p['kind']=='coin')
    header+='};\n'
    header+='static const struct { u16 slot, spawner_id; } m2Balloons[] = {\n'+''.join('    {%d,%d},\n'%(p['pickup_slot'],p['spawner_id']) for p in balloons())+'};\n'
    (ROOT/'include/m2_pickups.generated.h').write_text(header)

def patch_setup(filename):
    path=Path(filename);data=path.read_bytes();n=struct.unpack_from('>I',data)[0];original=data[4:4+n*48];extra=bytearray()
    for p in rows():
        kind=p['kind'];source=KINDS[kind][1]
        template=next(original[i*48:(i+1)*48] for i in range(n) if struct.unpack_from('>H',original,i*48+40)[0]==source)
        rec=bytearray(template);struct.pack_into('>3f',rec,0,*p['xyz']);struct.pack_into('>HH',rec,40,p['type'],p['object_id']);extra+=rec
    tail=data[4+n*48:];conveyors=struct.unpack_from('>I',tail)[0];offset=4+conveyors*36
    actors=struct.unpack_from('>I',tail,offset)[0];actor_data=tail[offset+4:offset+4+actors*56]
    actor_ids={struct.unpack_from('>H',actor_data,i*56+52)[0] for i in range(actors)}
    template=next(actor_data[i*56:(i+1)*56] for i in range(actors) if struct.unpack_from('>H',actor_data,i*56+50)[0]+16==91)
    additions=bytearray()
    for p in balloons():
        assert p['spawner_id'] not in actor_ids
        rec=bytearray(template);struct.pack_into('>3f',rec,0,*p['xyz']);struct.pack_into('>II',rec,16,p['path_id'],3)
        # K.Rool balloon147 is excluded from native permanent-flag allocation.
        # Only the explicitly identified Japes instances use the private handler.
        struct.pack_into('>HH',rec,50,147-16,p['spawner_id']);additions+=rec
    path.write_bytes(struct.pack('>I',n+len(rows()))+original+extra+tail[:offset]+struct.pack('>I',actors+len(balloons()))+actor_data+additions+tail[offset+4+actors*56:])

def patch_paths(filename):
    path=Path(filename);data=path.read_bytes();count=struct.unpack_from('>H',data)[0]
    assert count==22
    offset=2;ids=set()
    for i in range(count):
        ident,num,_=struct.unpack_from('>3H',data,offset);ids.add(ident);offset+=6+num*10
    assert offset==len(data)
    extra=bytearray()
    for p in balloons():
        assert p['path_id']<26 and p['path_id'] not in ids
        extra+=struct.pack('>3H',p['path_id'],4,0)
        for dx,dz in [(-45,-25),(45,-25),(45,25),(-45,25)]:
            x,y,z=p['xyz'];extra+=struct.pack('>4hBB',0,round(x+dx),round(y),round(z+dz),1,0)
    path.write_bytes(struct.pack('>H',count+len(balloons()))+data[2:]+extra)

def payloads(rom):
    result=[]
    for typ,source,first,count in KINDS.values():
        model=bytearray(read_file(rom,4,source));assert len(model)==340
        old=struct.unpack_from('>I',model,0x9C)[0]
        assert struct.unpack_from('>I',model,0xA8)[0]==count
        struct.pack_into('>I',model,0x9C,first);struct.pack_into('>H',model,0x124,first)
        if struct.unpack_from('>H',model,0x2A)[0]==old:struct.pack_into('>H',model,0x2A,first)
        for i in range(count-1):struct.pack_into('>I',model,0xAC+i*4,first+1+i)
        result.append(bytes(model))
    from character_colors import identity_color
    gray=identity_color()[0]
    for index in range(0x112,0x11E):
        native=read_file(rom,7,index);out=bytearray()
        for (value,) in struct.iter_unpack('>H',native):
            r,g,b=(value>>11)&31,(value>>6)&31,(value>>1)&31
            light=min(31,round((.2126*r+.7152*g+.0722*b)*gray/(255*.9278)))
            out+=struct.pack('>H',light<<11|light<<6|light<<1|value&1)
        result.append(bytes(out))
    for index in range(0x16BB,0x16C3):
        native=read_file(rom,25,index);out=bytearray()
        for (value,) in struct.iter_unpack('>H',native):
            r,g,b=(value>>11)&31,(value>>6)&31,(value>>1)&31
            # Native Chunky balloon: green body and gold banana emblem.
            # Keep its yellow/orange texels verbatim; silver only the body.
            if r >= g and g > b:
                out+=struct.pack('>H',value)
                continue
            light=min(31,round((.2126*r+.7152*g+.0722*b)*gray/(255*.9278)))
            out+=struct.pack('>H',light<<11|light<<6|light<<1|value&1)
        result.append(bytes(out))
    assert len(result)==23
    return result

def patch_code(fh,symbols):
    base=0x805FB300
    def word(a):fh.seek(a-base);return int.from_bytes(fh.read(4),'big')
    def patch(a,expected,new):
        assert word(a)==expected,hex(a)
        fh.seek(a-base);fh.write(new.to_bytes(4,'big'))
    # Native2D model2 ownership-opacity call; original routine remains callable.
    patch(0x806380B0,0x0C18E4AF,0x0C000000|(int(symbols['m2pickupopacity'],16)&0xFFFFFFF)>>2)
    target=int(symbols['m2collectdefs'],16)
    for h,l,offset in [(0x806F48D0,0x806F48D4,0),(0x806F4E7C,0x806F4E8C,0),(0x806F51C0,0x806F51CC,12),(0x806F5554,0x806F5560,2),(0x806F626C,0x806F6278,0),(0x806F6AC4,0x806F6ACC,0),(0x806F7428,0x806F7448,0),(0x806F7994,0x806F7998,42*20)]:
        hi,lo=word(h),word(l);signed=(lo&65535)-(65536 if lo&32768 else 0)
        assert hi>>26==15 and ((hi&65535)<<16)+signed==0x80753EF0+offset,(hex(h),hex(lo))
        # The actor loop retains its native 42-row bound via its relocated end.
        ptr=target+offset;patch(h,hi,hi&0xFFFF0000|((ptr+32768)>>16&65535));patch(l,lo,lo&0xFFFF0000|ptr&65535)
    patch(0x806F4A8C,0x2401002A,0x2401002E)
    # The existing tag-anywhere build already allocates530 model2 slots/map.
    patch(0x80632188,0x0C1CC575,0x0C000000|(int(symbols['m2setuphidden'],16)&0xFFFFFFF)>>2)

    fh.seek(0x806FACE8-base)
    assert fh.read(8)==bytes.fromhex('27bdffe0afbf0014')
    fh.seek(0x806FACE8-base)
    fh.write((0x08000000|(int(symbols['m2hudsprite'],16)&0xFFFFFFF)>>2).to_bytes(4,'big')+bytes(4))

    fh.seek(0x80675810-base)
    assert fh.read(8)==bytes.fromhex('27bdffd0afbf002c')
    fh.seek(0x80675810-base)
    fh.write((0x08000000|(int(symbols['m2actorcollision'],16)&0xFFFFFFF)>>2).to_bytes(4,'big')+bytes(4))
