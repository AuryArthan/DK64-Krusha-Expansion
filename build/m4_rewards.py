"""Japes M4 private Golden Bananas. Original setup order/flag pools stay intact."""
from pathlib import Path
import json, struct, zlib
from barrel_assets import read_file

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'docs/planning/krusha-adventure-expansion/placements/assistant-draft-v1.json'
TYPE=9

def rows():
    from m2_pickups import rows as m2_rows
    pins=[p for p in json.loads(PLAN.read_text())['pins'] if p.get('reward_id') in (1,2,3) and p['map'] in (7,33)]
    rom=(ROOT/'rom/dk64.z64').read_bytes();result=[]
    for mid in (7,33):
        data=read_file(rom,9,mid);n=struct.unpack_from('>I',data)[0]
        used={struct.unpack_from('>H',data,4+i*48+42)[0] for i in range(n)}
        script=read_file(rom,10,mid);used.update(struct.unpack('>%dH'%(len(script)//2),script[:len(script)//2*2]))
        if mid==7:used.update(p['object_id'] for p in m2_rows())
        static=zlib.decompress(rom[0xC29D4:],47)
        used.update(struct.unpack_from('>H',static,0x80755A20-0x80744460+i*8+2)[0] for i in range(113) if static[0x80755A20-0x80744460+i*8]==mid)
        used.update(struct.unpack_from('>H',static,0x80747D50-0x80744460+i*4+2)[0] for i in range(8) if struct.unpack_from('>H',static,0x80747D50-0x80744460+i*4)[0]==mid)
        free=iter(i for i in range(529,-1,-1) if i not in used)
        for pin in pins:
            if pin['map']==mid:
                row=dict(pin,object_id=next(free),type=TYPE)
                if row['reward_id']==1:row['xyz']=[1680,298,4245]
                # Draft sampling left these18 above the floor. Krusha's
                # native multiplayer contact points need a ground pickup;
                # walking tests (not teleported contact) establish this gap.
                row['xyz'][1]-=14
                result.append(row)
    return result

def props():
    """Private script identities, disjoint from native and all new pickups."""
    rom=(ROOT/'rom/dk64.z64').read_bytes();data=read_file(rom,9,7)
    used={struct.unpack_from('>H',data,4+i*48+42)[0] for i in range(struct.unpack_from('>I',data)[0])}
    script=read_file(rom,10,7);used.update(struct.unpack('>%dH'%(len(script)//2),script[:len(script)//2*2]))
    from m2_pickups import rows as m2_rows
    used.update(p['object_id'] for p in m2_rows());used.update(p['object_id'] for p in rows() if p['map']==7)
    free=iter(i for i in range(529,-1,-1) if i not in used)
    return dict(gate=next(free),switch=next(free))

def prepare(rom_path):
    rom=Path(rom_path).read_bytes();assert not read_file(rom,4,TYPE) and not read_file(rom,4,33)
    static=zlib.decompress(rom[0xC29D4:],47)
    assert static[0x80755F54-0x80744460:0x80755F58-0x80744460]==bytes.fromhex('01c40000')
    setup_count=struct.unpack_from('>I',rom,0x101C50+(32+9)*4)[0]
    for mid in range(setup_count):
        data=read_file(rom,9,mid)
        if not data:continue
        for i in range(struct.unpack_from('>I',data)[0]):assert struct.unpack_from('>H',data,4+i*48+40)[0] not in (TYPE,33)
        pos=4+struct.unpack_from('>I',data)[0]*48
        pos+=4+struct.unpack_from('>I',data,pos)[0]*36
        count=struct.unpack_from('>I',data,pos)[0];pos+=4
        for i in range(count):
            if struct.unpack_from('>H',data,pos+i*56+50)[0]+16==28:
                assert struct.unpack_from('>I',data,pos+i*56+24)[0]!=2,'Unused bonus entry has a native placement'
    h='/* Generated M4 stable reward slots; no native permanent flags added. */\n'
    h+='static const struct { u16 map,object_id; u8 reward; } m4Rewards[] = {\n'
    h+=''.join('    {%d,%d,%d},\n'%(p['map'],p['object_id'],p['reward_id']) for p in rows())+'};\n'
    h+='#define M4_GATE_ID %d\n#define M4_SWITCH_ID %d\n'%(props()['gate'],props()['switch'])
    (ROOT/'include/m4_rewards.generated.h').write_text(h)

def patch_setup(filename,mid):
    path=Path(filename);data=path.read_bytes();n=struct.unpack_from('>I',data)[0];extra=bytearray()
    template=next(data[4+i*48:4+(i+1)*48] for i in range(n) if struct.unpack_from('>H',data,4+i*48+40)[0]==0x74)
    for p in rows():
        if p['map']!=mid:continue
        rec=bytearray(template);struct.pack_into('>4f',rec,0,*p['xyz'],0.25);struct.pack_into('>HH',rec,40,TYPE,p['object_id']);extra+=rec
    if mid==7:
        factory=read_file((ROOT/'rom/dk64.z64').read_bytes(),9,26)
        factory_count=struct.unpack_from('>I',factory)[0]
        cage=next(factory[4+i*48:4+(i+1)*48] for i in range(factory_count) if struct.unpack_from('>HH',factory,4+i*48+40)==(0xD3,33))
        switch=next(data[4+i*48:4+(i+1)*48] for i in range(n) if struct.unpack_from('>H',data,4+i*48+42)[0]==291)
        for source,typ,ident,xyz,scale,rotation in [(cage,0xD3,props()['gate'],(1680,280,4245),.66,0),(switch,33,props()['switch'],(1545,280,4245),1.0,180)]:
            rec=bytearray(source)
            struct.pack_into('>4f',rec,0,*xyz,scale);struct.pack_into('>3f',rec,24,0,rotation,0);struct.pack_into('>HH',rec,40,typ,ident);extra+=rec
    tail=data[4+n*48:]
    if mid==7:
        offset=4+struct.unpack_from('>I',tail)[0]*36
        count=struct.unpack_from('>I',tail,offset)[0];actors=tail[offset+4:offset+4+count*56]
        barrel=bytearray(next(actors[i*56:(i+1)*56] for i in range(count) if struct.unpack_from('>H',actors,i*56+50)[0]+16==28))
        assert not any(struct.unpack_from('>H',actors,i*56+52)[0]==610 for i in range(count))
        struct.pack_into('>4f',barrel,0,1835,351,1490,1.0)
        struct.pack_into('>I',barrel,16,32);struct.pack_into('>I',barrel,24,2);struct.pack_into('>H',barrel,52,610)
        tail=tail[:offset]+struct.pack('>I',count+1)+actors+barrel+tail[offset+4+count*56:]
    path.write_bytes(struct.pack('>I',n+len(extra)//48)+data[4:4+n*48]+extra+tail)

def patch_japes(filename):patch_setup(filename,7)
def patch_cave(filename):patch_setup(filename,33)

def switch_texture(rom):
    from PIL import Image
    from character_colors import identity_color
    def decode(data):
        image=Image.new('RGBA',(32,32))
        image.putdata([((v>>11&31)*255//31,(v>>6&31)*255//31,(v>>1&31)*255//31,255*(v&1)) for (v,) in struct.iter_unpack('>H',data)])
        return image
    plate=decode(read_file(rom,25,0xB24));gray=identity_color()[0]
    for y in range(32):
        for x in range(32):
            r,g,b,a=plate.getpixel((x,y))
            light=round((.2126*r+.7152*g+.0722*b)*gray/255)
            if 4<=x<28 and 4<=y<28:light=30+round(12*(31-y)/31)
            plate.putpixel((x,y),(light,light,light,a))
    orange=decode(read_file(rom,25,0x14F6)).resize((22,22),Image.Resampling.LANCZOS)
    plate.alpha_composite(orange,(5,5))
    return b''.join(struct.pack('>H',(r>>3)<<11|(g>>3)<<6|(b>>3)<<1|(a>=128)) for r,g,b,a in plate.getdata())

def payloads(rom):
    switch=bytearray(read_file(rom,4,0x125))
    assert switch[0x228:0x230]==bytes.fromhex('fd10000000000b24') and not read_file(rom,25,7410)
    struct.pack_into('>I',switch,0x22C,7410)
    return [read_file(rom,4,0x74),bytes(switch),patched_scripts(read_file(rom,10,7)),switch_texture(rom)]

def patched_scripts(data):
    """Native switch contact/animation and metal cage animation; no flags."""
    ids=props()
    def script(ident,blocks):
        # Private condition only for these two scripts: preserve live records
        # for native cached-script restore, hide them through native controls.
        blocks=[([(-2,0x4D34,0,0)]+conditions,executions) for conditions,executions in blocks]
        blocks.append(([(0x7FFE,0x4D34,0,0)],[(69,1,0,255),(70,0,0,0),(71,0,0,0),(38,2,0,0)]))
        result=struct.pack('>3H',ident,len(blocks),0)
        for conditions,executions in blocks:
            result+=struct.pack('>H',len(conditions))+b''.join(struct.pack('>4h',*c) for c in conditions)
            result+=struct.pack('>H',len(executions))+b''.join(struct.pack('>4h',*e) for e in executions)
        return result
    gate=script(ids['gate'],[
        ([(1,0,0,0)],[(20,1,80,0),(17,1,-1,0),(38,2,0,0)]),
        ([(1,10,0,0)],[(18,1,0,0),(20,2,6,0),(17,2,1,0),(1,11,0,0)]),
        ([(1,11,0,0),(-32747,2,0,0)],[(69,1,0,255),(70,0,0,0),(71,0,0,0),(38,2,0,0)]),
    ])
    switch=script(ids['switch'],[
        ([(1,0,0,0)],[(20,1,10,0),(22,1,1,0),(1,1,0,0)]),
        ([(1,1,0,0),(24,171,1,0)],[(17,1,1,0),(5,ids['gate'],10,0),(84,ids['gate'],1,0),(1,2,0,0)]),
        ([(1,2,0,0)],[(15,140,0,0),(38,2,0,0),(1,3,0,0)]),
    ])
    offset=2
    for _ in range(struct.unpack_from('>H',data)[0]):
        _,count,_=struct.unpack_from('>3H',data,offset);offset+=6
        for _ in range(count):
            count=struct.unpack_from('>H',data,offset)[0];offset+=2+count*8
            count=struct.unpack_from('>H',data,offset)[0];offset+=2+count*8
    assert not any(data[offset:]),'Nonzero native script trailer'
    return struct.pack('>H',struct.unpack_from('>H',data)[0]+2)+data[2:offset]+gate+switch+data[offset:]

def patch_code(fh,symbols):
    for address,old,name in [(0x80680AFC,'0c1cc443','m4bonuscheckflag'),(0x80680DF0,'0c1a021b','m4bonuseligibility'),(0x806F78D8,'0c1cc504','m4bonusregisterflag')]:
        target=int(symbols[name],16)
        fh.seek(address-0x805FB300);assert fh.read(4)==bytes.fromhex(old)
        fh.seek(address-0x805FB300);fh.write((0x0C000000|((target&0xFFFFFFF)>>2)).to_bytes(4,'big'))
