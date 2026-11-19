"""Japes M4 private Golden Bananas. Original setup order/flag pools stay intact."""
from pathlib import Path
import json, struct, zlib
from barrel_assets import read_file

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'data/placements/japes-base.json'
TYPE=9
CAGE_TYPE=46
CAGE_XYZ=(1680,286.27,4245)
# Rotated button back reaches +10X; cage's left rim is -52*.33X.
# 1653+10=1663 meets 1680-52*.33=1662.84 without a visible gap.
SWITCH_XYZ=(1653,280,4245)

def legacy_rows():
    from m2_pickups import registry_rows as m2_rows
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

def rows(mid=7):
    # Keep the reserved five-bit stride. Only gate1, encounter0 and Snide4
    # belong to the new three-reward design; retired2/3 remain stored only.
    if mid==7:
        from campaign_data import area
        cage=area(7)['cage']
        return [dict(r,xyz=[cage[0],round(cage[1]-2.27,3),cage[2]])
                for r in legacy_rows() if r['reward_id']==1]
    from campaign_data import worlds
    extra=[dict(map=w['map'],world=w['world'],object_id=w['reward_id'],reward_id=w['world']*5+1,type=TYPE,xyz=[w['cage'][0],round(w['cage'][1]-2.27,3),w['cage'][2]]) for w in worlds() if w['map']!=7 and (mid is None or w['map']==mid)]
    return rows(7)+extra if mid is None else extra

def props(mid=7):
    """Private script identities, disjoint from native and all new pickups."""
    if mid!=7:
        from campaign_data import area
        w=area(mid);assert w
        return dict(gate=w['gate_id'],switch=w['switch_id'],pad=w['pad_id'])
    rom=(ROOT/'rom/dk64.z64').read_bytes();data=read_file(rom,9,7)
    used={struct.unpack_from('>H',data,4+i*48+42)[0] for i in range(struct.unpack_from('>I',data)[0])}
    script=read_file(rom,10,7);used.update(struct.unpack('>%dH'%(len(script)//2),script[:len(script)//2*2]))
    from m2_pickups import registry_rows as m2_rows
    used.update(p['object_id'] for p in m2_rows());used.update(p['object_id'] for p in legacy_rows() if p['map']==7)
    free=iter(i for i in range(529,-1,-1) if i not in used)
    return dict(gate=next(free),switch=next(free),pad=next(free))

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
    h+=''.join('    {%d,%d,%d},\n'%(p['map'],p['object_id'],p['reward_id']) for p in rows(None))+'};\n'
    h+='#define M4_GATE_ID %d\n#define M4_SWITCH_ID %d\n#define M4_PAD_ID %d\n'%(props()['gate'],props()['switch'],props()['pad'])
    (ROOT/'include/m4_rewards.generated.h').write_text(h)

def patch_setup(filename,mid):
    path=Path(filename);data=path.read_bytes();n=struct.unpack_from('>I',data)[0];extra=bytearray()
    native=read_file((ROOT/'rom/dk64.z64').read_bytes(),9,7)
    template=next(native[4+i*48:4+(i+1)*48] for i in range(struct.unpack_from('>I',native)[0]) if struct.unpack_from('>H',native,4+i*48+40)[0]==0x74)
    from campaign_data import area
    w=area(mid)
    for p in rows(mid):
        if p['map']!=mid:continue
        rec=bytearray(template);struct.pack_into('>4f',rec,0,*p['xyz'],0.25);struct.pack_into('>HH',rec,40,TYPE,p['object_id']);extra+=rec
    if w:
        factory=read_file((ROOT/'rom/dk64.z64').read_bytes(),9,26)
        factory_count=struct.unpack_from('>I',factory)[0]
        cage=next(factory[4+i*48:4+(i+1)*48] for i in range(factory_count) if struct.unpack_from('>HH',factory,4+i*48+40)==(0xD3,33))
        for source,typ,ident,xyz,scale,rotation in [(cage,CAGE_TYPE,props(mid)['gate'],w['cage'],.33,0)]:
            rec=bytearray(source)
            struct.pack_into('>4f',rec,0,*xyz,scale);struct.pack_into('>3f',rec,24,0,rotation,0);struct.pack_into('>HH',rec,40,typ,ident);extra+=rec
    tail=data[4+n*48:]
    if w:
        from m4_encounter import PAD_TYPE,PAD_XYZ
        original=(ROOT/'rom/dk64.z64').read_bytes()
        pad=None
        for map_id in range(216):
            native=read_file(original,9,map_id)
            if not native:continue
            for i in range(struct.unpack_from('>I',native)[0]):
                if struct.unpack_from('>H',native,4+i*48+40)[0]==171:
                    pad=bytearray(native[4+i*48:4+(i+1)*48]);break
            if pad:break
        assert pad is not None
        struct.pack_into('>4f',pad,0,*w['pad'],.25)
        struct.pack_into('>3f',pad,24,0,0,0)
        struct.pack_into('>HH',pad,40,PAD_TYPE,props(mid)['pad'])
        extra+=pad
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

def cage_model(rom):
    """Private static cage, retaining native body geometry/materials.

    Five hanging chain links and the top eyelet occupy DL B0..388. Omit
    only their triangles. Native skeleton, bounds, vertex and animation data
    remain valid; Factory's original hanging cages are never changed.
    """
    assert not read_file(rom,4,CAGE_TYPE)
    model=bytearray(read_file(rom,4,0xD3))
    original=(ROOT/'rom/dk64.z64').read_bytes()
    for mid in range(216):
        setup=read_file(original,9,mid)
        if setup:assert all(struct.unpack_from('>H',setup,4+i*48+40)[0]!=CAGE_TYPE for i in range(struct.unpack_from('>I',setup)[0]))
    assert len(model)==9664 and struct.unpack_from('>I',model,0x48)[0]==0x740
    removed=0
    for offset in range(0xB0,0x390,8):
        if model[offset] in (5,6):
            model[offset:offset+8]=bytes(8);removed+=1
    assert removed==24,removed
    return bytes(model)

def patched_scripts(data,mid=7):
    """Native projectile button and static disappearing cage; no native flags."""
    ids=props(mid)
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
        ([(1,0,0,0)],[(1,1,0,0)]),
        ([(1,1,0,0),(0x7FFE,0x4D35,0,0)],[(1,10,0,0)]),
        ([(1,10,0,0)],[(69,1,0,255),(70,0,0,0),(71,0,0,0),(1,11,0,0),(38,2,0,0)]),
    ])
    # Retired switch bytecode is retained only as source history.
    switch=script(0 if ids['switch']==65535 else ids['switch'],[
        ([(1,0,0,0)],[(1,1,0,0)]),
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
    return struct.pack('>H',struct.unpack_from('>H',data)[0]+1)+data[2:offset]+gate+data[offset:]

def patch_code(fh,symbols):
    from m4_encounter import patch_code as encounter_patch
    encounter_patch(fh,symbols)
    from krusha_ammo import patch_code as ammo_patch
    ammo_patch(fh,symbols)
    # These two Model2 unload paths turn a live texture pointer back into a
    # file ID for a later table25 reload. Preserve the external alias; the
    # native reference/free path must continue to see its real table27 key.
    for address in (0x806368A0,0x80636BAC):
        fh.seek(address-0x805FB300)
        assert fh.read(4)==bytes.fromhex('0c19adeb'),hex(address)
        target=int(symbols['krushamodel2textureidentity'],16)
        fh.seek(address-0x805FB300)
        fh.write((0x0C000000|((target&0xFFFFFFF)>>2)).to_bytes(4,'big'))
