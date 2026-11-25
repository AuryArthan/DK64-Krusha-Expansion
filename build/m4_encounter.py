"""Private native Klump/pad resources for the three-reward Japes pilot."""
from pathlib import Path
import struct
from barrel_assets import read_file

ROOT=Path(__file__).resolve().parents[1]
PAD_TYPE=42
TRIGGER=250
PAD_XYZ=(1835,286,1490)
BOSS_XYZ=(2110,286,1450)
TINT_IDS=(0x104D,0x104E,0x104F,0x1050,0x1051,0x1052,0x1053,0x1054,0x1058,0x1059)
PAD_TEXTURES=(0xBC4,0xBC5,0xBC6,0xBC7,0xBCE,0xBCF)

def parse_spawners(data):
    p=2;ids=[]
    for _ in range(struct.unpack_from('>H',data)[0]):
        n=struct.unpack_from('>H',data,p)[0];p+=2+n*6
        n=struct.unpack_from('>H',data,p)[0];p+=2+n*10
        ids.append(struct.unpack_from('>H',data,p)[0]);p+=4
    fence_end=p;n=struct.unpack_from('>H',data,p)[0];p+=2;records=[]
    for _ in range(n):
        end=p+22+data[p+17]*2;records.append(data[p:end]);p=end
    assert p==len(data)
    return fence_end,ids,records

def spawners(rom):
    from campaign_data import area
    placement=area(7)
    from m3_kasplat import spawners as m3_spawners
    data=m3_spawners(read_file(rom,16,7));end,ids,records=parse_spawners(data)
    assert not any(r[19]==TRIGGER for r in records)
    original=(ROOT/'rom/dk64.z64').read_bytes()
    template=None
    for mid in range(216):
        raw=read_file(original,16,mid)
        if not raw:continue
        template=next((r for r in parse_spawners(raw)[2] if r[0]==9 and len(r)==22 and r[15]==50),None)
        if template:break
    assert template is not None
    assert len(template)==22
    record=bytearray(template);struct.pack_into('>3h',record,4,*(round(v) for v in placement['boss']))
    # Ordinary world Klumps use size50 (24 of29 native instances);80 is1.6x (20% below the prior2x).
    fence_id=max(ids)+1;record[14]=fence_id;record[15]=80
    record[18]=0;record[19]=TRIGGER;record[20]=0
    # This is the fight area's boundary, independent of the spawn point.
    # Keep it fixed when moving Klump within the same clearing.
    points=placement['fence']
    fence=struct.pack('>H',len(points))+b''.join(struct.pack('>3h',*(round(x) for x in v)) for v in points)+struct.pack('>3H',0,fence_id,1)
    return struct.pack('>H',len(ids)+1)+data[2:end]+fence+struct.pack('>H',len(records)+1)+b''.join(records)+record

def remap_model(data,mapping):
    out=bytearray(data)
    for p in range(0,len(out)-8,4):
        a,b=struct.unpack_from('>II',out,p)
        if a==0xFD100000 and b in mapping:struct.pack_into('>I',out,p+4,mapping[b])
    return bytes(out)

def tint(data,kind):
    from klump_colors import skin_multiplier, gear_multiplier
    color=(.73,.87,1.0) if kind=='skin' else (.37,.56,1.0) if kind in ('armor','gear') else (.92,.48,.90)
    if kind in ('skin','torso'):
        color=skin_multiplier() or color
    elif kind=='gear':
        color=gear_multiplier() or color
    result=bytearray()
    for (v,) in struct.iter_unpack('>H',data):
        r,g,b=(v>>11&31),(v>>6&31),(v>>1&31)
        light=.2126*r+.7152*g+.0722*b
        a=[max(0,min(31,round(light*k))) for k in color]
        result+=struct.pack('>H',a[0]<<11|a[1]<<6|a[2]<<1|v&1)
    return bytes(result)

def pad_portrait():
    from PIL import Image
    face=Image.open(ROOT/'assets/krusha/hud/krusha-shout-source.png').convert('RGBA')
    face.thumbnail((58,58),Image.Resampling.LANCZOS)
    # The native metal/purple pad already supplies the circular base. Only
    # its floating instrument glyph is replaced; transparent corners matter.
    top=Image.new('RGBA',(64,64))
    top.alpha_composite(face,((64-face.width)//2,(64-face.height)//2))
    # Pad glyph uses two32x64 texture halves, upside-down like native art.
    top=top.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    def encode(im):return b''.join(struct.pack('>H',(r>>3)<<11|(g>>3)<<6|(b>>3)<<1|int(a>=128)) for r,g,b,a in im.getdata())
    return [encode(top.crop((0,0,32,64))),encode(top.crop((32,0,64,64)))]

def payloads(rom):
    original=(ROOT/'rom/dk64.z64').read_bytes()
    assert not read_file(original,4,PAD_TYPE)
    assert all(not read_file(original,25,i) for i in range(7420,7436))
    for mid in range(struct.unpack_from('>I',original,0x101C50+(32+9)*4)[0]):
        s=read_file(original,9,mid)
        if s:assert all(struct.unpack_from('>H',s,4+i*48+40)[0]!=PAD_TYPE for i in range(struct.unpack_from('>I',s)[0]))
    from klump_colors import recolor_model_skin
    model=recolor_model_skin(remap_model(read_file(rom,5,57),{i:7420+n for n,i in enumerate(TINT_IDS)}))
    from klump_helmet import HORN_TEXTURE, add_helmet_spike, horn_reflection
    model=add_helmet_spike(model, read_file(original,5,0xCC))
    # Reuse the native base files directly; only the two portrait halves are
    # private. Model2 texture streaming must restore their external IDs on
    # unload (see z_texture_identity.c), rather than table27's storage IDs.
    pad=remap_model(read_file(rom,4,171),{i:7430+n for n,i in enumerate(PAD_TEXTURES) if n>=4})
    from klump_colors import skin_choice, armored_belly
    # 1051 and 1052 wrap the pouch walls. 1053 closes the same six pouches.
    materials={0x104D:'skin', 0x104E:'gear', 0x104F:'gear', 0x1050:'gear',
               0x1051:'gear', 0x1052:'gear', 0x1053:'gear', 0x1054:'gear', 0x1058:'skin',
               0x1059:'torso'}
    textures=[]
    for i in TINT_IDS:
        raw=read_file(rom,25,i)
        if i in (0x104D,0x1058,0x1059) and skin_choice()=='red-orange':
            textures.append(armored_belly(raw,front_panel=i!=0x1059))
        else:
            textures.append(tint(raw,materials.get(i,'armor')))
    # The first four private pad slots formerly duplicated its native base.
    # Reuse the first for the horn and keep existing texture IDs in place.
    assert 7420+len(textures)==HORN_TEXTURE
    textures.append(horn_reflection(read_file(rom,25,0xBAB)))
    textures.extend(read_file(rom,25,i) for i in PAD_TEXTURES[1:4])
    result=[model,pad]+textures+pad_portrait()+[spawners(rom)]
    assert len(result)==19
    return result

def patch_code(fh,symbols):
    # observeMelee reuses the six original player attack tests. The private
    # table then runs the native active belly hitbox and neutral fallback.
    import zlib
    data=zlib.decompress((ROOT/'rom/dk64.z64').read_bytes()[0xC29D4:],47)
    base=0x80744460
    assert struct.unpack_from('>I',data,0x8074C604+187*8-base)==(0x8074B5C8,)
    assert struct.unpack_from('>h2xI',data,0x8074B5C8-base)==(-1,0x8074B568)
    assert data[0x8074B568-base:0x8074B5C8-base]==bytes.fromhex(
        'ffff0004 80676540 05030200 ffff0020 00000000 04020200 '
        'ffff0400 00000000 09020200 ffff0a00 8067641c 04020200 '
        'ffff0080 806764d8 04020200 ffff0148 8067641c 05020200 '
        '0002ffff 80676730 010c0200 ffffffff 00000000 02020000')
    def patch(address,old,name,call=False):
        fh.seek(address-0x805FB300);assert fh.read(len(bytes.fromhex(old)))==bytes.fromhex(old),hex(address)
        target=int(symbols[name],16);fh.seek(address-0x805FB300)
        fh.write(((0x0C000000 if call else 0x08000000)|((target&0xFFFFFFF)>>2)).to_bytes(4,'big'))
        if not call:fh.write(bytes(4))
    patch(0x8072AEAC,'0c19947f','m4enemywalk',True)
    patch(0x806758A4,'0c19d78f8646005c','m4klumpcontactlookup',True)
    patch(0x80675DD0,'848e013484af0136','m4encounterdamage')
    patch(0x806AF384,'0c1a4213','m4encounterthrow',True)
    from klump_colors import grenade_choice
    if grenade_choice()!='original':
        patch(0x80694014,'0c1c5272','m4grenadecolor',True)
        patch(0x8069403C,'0c1c5302','m4grenadesprite',True)
        # Native idle snack particle: same scoped sprite as the thrown round.
        patch(0x806193EC,'0c1c5272','m4grenadecolor',True)
        patch(0x806194B8,'0c1c5302','m4grenadesprite',True)
