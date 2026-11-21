"""Alternate triangle winding for a runtime-selectable mirror view.

The projection/winding approach and native addresses are documented by DK64
Randomizer, revision1fb1c75ae852bc5f7f0d9c37b81e0d9451c77f6e,
randomizer/Patching/{MirrorMode.py,ASM/Kaizo.py}. No collision or placement data
changes. Native resource loading/reference counting owns the alternate files.
"""
from pathlib import Path
import struct,hashlib,json
from barrel_assets import read_file as read_payload
from mirror_labels import correct_labels
from mirror_prints import mark_geometry
BASE=0x101C50
MIRROR_TABLE=28
MIRROR_ROM=0x02200000
# Native tables1/4/5 hold221/695/236 files. Preserve index arithmetic in C.
PRIVATE_ACTORS={0,3,58,69}
PRIVATE_MODELS={35,36,37,62,65,66,70,88,105,122}
def read_file(rom,table,index,seen=()):
    assert index not in seen
    pointer=BASE+struct.unpack_from('>I',rom,BASE+table*4)[0]
    raw=struct.unpack_from('>I',rom,pointer+index*4)[0]
    if raw&0x80000000:
        target=struct.unpack_from('>H',rom,BASE+(raw&0x7FFFFFFF))[0]
        return read_file(rom,table,target,seen+(index,))
    return read_payload(rom,table,index)
def flip(data,kind):
    if not data:return data,0
    b=bytearray(data);u=lambda p:struct.unpack_from('>I',b,p)[0]
    if kind==1:start,end=u(0x34),u(0x38)
    elif kind==4:start,end=u(0x40),u(0x48)
    else:
        base=u(0);end=0x28+u(4)-base
        assert 0<=end<=len(b)-4,(kind,len(b),end)
        start=0x28+u(end)-base
    assert 0<=start<=end<=len(b) and (end-start)%8==0,(kind,len(b),start,end)
    count=0
    for p in range(start,end,8):
        if b[p] in (5,6,7):
            for off in (2,6):b[p+off],b[p+off+1]=b[p+off+1],b[p+off]
            count+=1
    return bytes(b),count

def appendMirrorAssets(path):
    original=Path(path).read_bytes();payloads=[];entries=[]
    assert struct.unpack_from('>I', original, BASE+(32+MIRROR_TABLE)*4)[0] == 0, 'Mirror table must be unused'
    for table,expected in [(1,221),(4,695),(5,236),(27,131)]:
        n=struct.unpack_from('>I',original,BASE+(32+table)*4)[0]
        # Preserve all1283 historical mirror slots. R01's normal/mirrored
        # static models live directly in table27 at147/148; preview images
        # retain their reserved131..146 interval in either build preset.
        from recruitment_scene import COUNT as scene_count
        # Five pause-only RGBA icons and the private key jingle follow the scene; they need no mirrored
        # geometry and preserve every established scene/Mirror index.
        assert n==(scene_count+6 if table==27 else expected),(table,n)
        for index in range(expected):
            kind=table if table!=27 else 5 if index in PRIVATE_ACTORS else 4 if index in PRIVATE_MODELS else 0
            source=read_file(original,table,index) if kind else b''
            data,count=flip(source,kind) if kind else (b'',0)
            data=mark_geometry(correct_labels(data,table,index),table,index)
            payloads.append(data);entries.append(dict(table=table,index=index,kind=kind,bytes=len(data),triangle_commands=count,source_sha256=hashlib.sha256(source).hexdigest(),mirror_sha256=hashlib.sha256(data).hexdigest()))
    assert len(original)<=MIRROR_ROM
    pointer=MIRROR_ROM+(len(payloads)+1)*4;offsets=[]
    for data in payloads:offsets.append(pointer-BASE);pointer+=len(data)
    offsets.append(pointer-BASE);assert pointer<0x04000000
    with open(path,'r+b') as f:
        f.seek(0,2);f.write(bytes(MIRROR_ROM-f.tell()));f.write(struct.pack('>%dI'%len(offsets),*offsets))
        for data in payloads:f.write(data)
        f.seek(BASE+MIRROR_TABLE*4);f.write(struct.pack('>I',MIRROR_ROM-BASE))
        f.seek(BASE+(32+MIRROR_TABLE)*4);f.write(struct.pack('>I',len(payloads)))
    Path(str(path)+'.mirror-assets.json').write_text(json.dumps(dict(format=1,table=MIRROR_TABLE,rom_start=MIRROR_ROM,rom_end=pointer,entries=entries),indent=2)+'\n')
    print('Embedded1283 mirror geometry slots; end',hex(pointer))
