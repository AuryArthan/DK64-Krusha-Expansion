"""Japes pilot enemy and isolated Kasplat palettes. Original tables stay intact."""
import struct
from character_colors import identity_color

GRAY_SPAWNER_ID=3
MAP=7

def spawners(native):
    pos=2; fences=struct.unpack_from('>H',native)[0]; fence_ids=[]
    for _ in range(fences):
        n=struct.unpack_from('>H',native,pos)[0];pos+=2+n*6
        n=struct.unpack_from('>H',native,pos)[0];pos+=2+n*10
        fence_ids.append(struct.unpack_from('>H',native,pos)[0]);pos+=4
    fence_end=pos
    count=struct.unpack_from('>H',native,pos)[0];pos+=2
    records=[]
    for _ in range(count):
        end=pos+22+native[pos+17]*2;records.append(native[pos:end]);pos=end
    assert pos==len(native)
    assert all(r[19]!=GRAY_SPAWNER_ID for r in records)
    template=next(r for r in records if r[0]==61)
    assert len(template)==22 and template[17]==0
    fence_id=max(fence_ids)+1
    assert fence_id<256
    from campaign_data import kasplat
    placement=kasplat(MAP)
    assert placement['kasplat_id']==GRAY_SPAWNER_ID
    xyz=tuple(round(n) for n in placement['kasplat'])
    points=[(xyz[0]+x,xyz[1],xyz[2]+z) for x,z in [(-70,-70),(70,-70),(70,70),(-70,70),(-70,-70)]]
    fence=struct.pack('>H',len(points))+b''.join(struct.pack('>3h',*p) for p in points)+struct.pack('>3H',0,fence_id,1)
    extra=bytearray(template)
    struct.pack_into('>3h',extra,4,*xyz)
    extra[14]=fence_id;extra[19]=GRAY_SPAWNER_ID
    return struct.pack('>H',fences+1)+native[2:fence_end]+fence+struct.pack('>H',count+1)+b''.join(records)+extra

def payloads(rom,read_file):
    assert not read_file(rom,4,7), 'Private blueprint type7 must be empty'
    for mid in range(221):
        setup=read_file(rom,9,mid)
        if setup:
            assert all(struct.unpack_from('>H',setup,4+i*48+40)[0]!=7 for i in range(struct.unpack_from('>I',setup)[0])), ('Private blueprint type in native setup',mid)
    native=read_file(rom,5,54)
    model=bytearray(native)
    start=struct.unpack_from('>I',model,16)[0]-struct.unpack_from('>I',model)[0]+40
    assert struct.unpack_from('>4H',model,start)==(1,6,12,1)
    assert tuple(struct.unpack_from('>6H',model,start+8))==tuple(range(0x1018,0x101E))
    assert start+20==len(model)
    # Native frame5 remains spent, now black in the ON-only model. New frame6
    # is silver. Geometry, skeleton, animations and original owner frames stay.
    # Third word is display-list segment12, NOT the byte length of the
    # texture-ID list. Preserve it when adding the seventh frame.
    model[start:]=struct.pack('>4H7H',1,7,12,1,*range(0x1018,0x101D),7400,7401)+bytes(2)
    white=read_file(rom,25,0x101D)
    def tint(target):
        out=bytearray()
        for (value,) in struct.iter_unpack('>H',white):
            lum=((value>>11)&31)*.2126+((value>>6)&31)*.7152+((value>>1)&31)*.0722
            gray=min(31,round(lum*target/255))
            out+=struct.pack('>H',(gray<<11)|(gray<<6)|(gray<<1)|(value&1))
        return bytes(out)
    # Same native48x42 billboard topology as the gray coin. The existing
    # approved gray blueprint frames26..33 are aliased into texture table7.
    pickup=bytearray(read_file(rom,4,29))
    assert len(pickup)==340 and struct.unpack_from('>I',pickup,0xA8)[0]==8
    old=struct.unpack_from('>I',pickup,0x9C)[0]
    struct.pack_into('>I',pickup,0x9C,7500);struct.pack_into('>H',pickup,0x124,7500)
    if struct.unpack_from('>H',pickup,0x2A)[0]==old:struct.pack_into('>H',pickup,0x2A,7500)
    for i in range(7):struct.pack_into('>I',pickup,0xAC+4*i,7501+i)
    return [bytes(model),tint(16),tint(identity_color()[0]),spawners(read_file(rom,16,MAP)),bytes(pickup)]
