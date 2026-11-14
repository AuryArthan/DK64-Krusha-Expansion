"""R03 dedicated map216: native-sized private scenery, no K. Lumsy actors/story.

All original map97 resources remain untouched. Native metadata arrays are221
entries (level mapping224);216 is an authored empty slot, not out-of-bounds.
"""
from pathlib import Path
import struct,zlib,json,hashlib,math
from barrel_assets import read_file
from recruitment_assets import POSITION,SCALE,SAFE_DEPTH,STONE_TINT
from recruitment_collision import DOOR_CENTER,DOOR_NORMAL
ROOT=Path(__file__).resolve().parents[1]
MAP=216
STONE_PALETTES=(0x5BD,0x5BF,0x5C1)
# Four neutral floor/metal palettes and the large warm-stone wall palette.
SECONDARY_PALETTES=(0x10,0x90D,0x262,0x251,0x514)
METAL_PALETTES=(0x90D,0x262,0x251)
METAL_BRIGHTNESS=.65
PALETTES=STONE_PALETTES+SECONDARY_PALETTES
TOKEN=7820
INDEX=158
ASSETS=ROOT/'runtime/recruitment/room-assets'

def palette(rom,ident,stone):
    source=read_file(rom,25,ident);assert len(source)==32
    out=bytearray()
    for (v,) in struct.iter_unpack('>H',source):
        rgb=(v>>11&31,v>>6&31,v>>1&31)
        light=.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
        if not stone:rgb=[round(light*(METAL_BRIGHTNESS if ident in METAL_PALETTES else 1))]*3
        elif max(rgb)-min(rgb)>3:rgb=[round(light*c) for c in STONE_TINT]
        out+=struct.pack('>H',rgb[0]<<11|rgb[1]<<6|rgb[2]<<1|v&1)
    return bytes(out)

def payloads(rom):
    # Preserve the established geometry/LZ/reference indices161..164.
    result=[palette(rom,i,True) for i in STONE_PALETTES]
    g=geometry(rom)
    from mirror_assets import flip
    result += [g,flip(g,1)[0],loading_zone(rom),struct.pack('>H',97)]
    # Native513/514 is the large warm-stone wall, not a metal plate.
    return result+[palette(rom,i,i==0x514) for i in SECONDARY_PALETTES]

def geometry(rom):
    g=bytearray(read_file(rom,1,97));start,end=struct.unpack_from('>II',g,0x34);changed=0
    for p in range(start,end,8):
        a,b=struct.unpack_from('>II',g,p)
        if a>>24==0xFD and b in PALETTES:
            struct.pack_into('>I',g,p+4,TOKEN+PALETTES.index(b));changed+=1
    assert changed>=len(PALETTES)
    # Neutralize warm baked vertex illumination in this private copy only.
    # Preserve luminance, shading variation, alpha, UVs and all native geometry.
    start,end=struct.unpack_from('>I',g,0x38)[0],struct.unpack_from('>I',g,0x40)[0]
    for p in range(start,end,16):
        rgb=g[p+12:p+15]
        if max(rgb)-min(rgb)>8:
            light=round(.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2])
            g[p+12:p+15]=bytes([light]*3)
    return bytes(g)

def return_exit(rom):
    original=read_file(rom,23,34);assert len(original)%10==0
    x=POSITION[0]+DOOR_CENTER[0]*SCALE+DOOR_NORMAL[0]*SAFE_DEPTH
    z=POSITION[2]+DOOR_CENTER[2]*SCALE+DOOR_NORMAL[1]*SAFE_DEPTH
    yaw=math.atan2(DOOR_NORMAL[0],DOOR_NORMAL[1])%(2*math.pi)
    angle=round(yaw*255/(2*math.pi))%256
    # Native exit.angle is the FIRST byte at+6, not a4096-unit ushort.
    record=struct.pack('>3h4B',round(x),round(POSITION[1]),round(z),angle,1,0,0)
    return original+record,len(original)//10

def prepare(rom_path):
    rom=Path(rom_path).read_bytes();assert not read_file(rom,1,MAP)
    assert read_file(rom,9,MAP)==bytes(12) and read_file(rom,16,MAP)==bytes(4)
    for ident in range(TOKEN,TOKEN+len(PALETTES)):assert not read_file(rom,25,ident)
    ASSETS.mkdir(parents=True,exist_ok=True)
    exits,outside=return_exit(rom);assert outside==13
    files={(23,34):exits,(23,MAP):struct.pack('>3h4B',1000,60,1000,128,1,0,0)}
    for (table,mid),data in files.items():(ASSETS/f'{table}-{mid}.bin').write_bytes(data)
    h=ROOT/'include/recruitment_room.generated.h'
    h.write_text('/* Generated isolated recruitment room identities. */\n'+''.join(f'#define {k} {v}\n' for k,v in dict(RECRUITMENT_ROOM_MAP=MAP,RECRUITMENT_ROOM_SOURCE=97,RECRUITMENT_ROOM_GEOMETRY=161,RECRUITMENT_ROOM_MIRROR=162,RECRUITMENT_ROOM_ZONE=163,RECRUITMENT_ROOM_TEXTURE_TOKEN=TOKEN,RECRUITMENT_ROOM_TEXTURE_INDEX=INDEX,RECRUITMENT_ROOM_EXTRA_TEXTURE_INDEX=165,RECRUITMENT_ROOM_TEXTURE_COUNT=len(PALETTES),RECRUITMENT_RETURN_EXIT=outside,RECRUITMENT_STAGE_TICKS=180).items()))
    data=zlib.decompress(rom[0xC29D4:],47);base=0x80744460
    report=dict(map=MAP,source=97,original_room_preserved=True,empty_setup=True,empty_spawners=True,empty_cutscenes=True,
                metadata=dict(level_mapping_capacity=224,map_properties_capacity=221,song_capacity=230,level=data[0x807445E0-base+MAP],properties=data[0x8074482C-base+12*MAP:0x8074482C-base+12*(MAP+1)].hex()),
                return_exit=outside,return_record=exits[-10:].hex(),source_palettes=PALETTES,private_texture_token=TOKEN,private_texture_index=INDEX,
                files={f'{t}:{m}':dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for (t,m),b in files.items()})
    (ASSETS/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')

def loading_zone(rom):
    # Payload packing sees the already-patched exit bank; do not append again
    # when calculating this index. prepare() verifies USA originally has13.
    outside=13
    zone=bytearray(read_file(rom,18,97)[2:58]);assert struct.unpack_from('>3H',zone,16)==(9,34,1)
    struct.pack_into('>H',zone,20,outside)
    return struct.pack('>H',1)+zone

def files():
    return [dict(name=f'Private R03 exits{mid}',pointer_table_index=23,file_index=mid,source_file=str((ASSETS/f'23-{mid}.bin').relative_to(ROOT)),do_not_extract=True,do_not_delete_source=True,do_not_compress=True) for mid in (34,MAP)]

def patch_data(filename):
    with open(filename,'r+b') as fh:patch_data_stream(fh)

def patch_data_stream(fh):
    # These are allocated native221-entry slots, not expansion into neighbors.
    for address,source,size,expected in [(0x807445E0+MAP,0x807445E0+97,1,b'\x0c'),(0x8074482C+12*MAP,0x8074482C+12*97,12,bytes(12)),(0x80745BDC+4*MAP,0x80745BDC+4*97,4,bytes.fromhex('58000001'))]:
        fh.seek(address-0x80744460);assert fh.read(size)==expected,hex(address)
        fh.seek(source-0x80744460);data=fh.read(size)
        fh.seek(address-0x80744460);fh.write(data)


def patch_native_aliases(path):
    # Native8066B4D4 resolves bit31 references BEFORE looking at the next
    # pointer. Reuse untouched97 collision from our empty216 entries. This
    # also covers raw streaming ROM-address queries that bypass the C loader.
    from barrel_assets import TABLE_BASE
    with open(path,'r+b') as f:
        def u(p):f.seek(p);return struct.unpack('>I',f.read(4))[0]
        private=TABLE_BASE+u(TABLE_BASE+27*4)
        ref=u(private+164*4)&0x7FFFFFFF
        f.seek(TABLE_BASE+ref);assert f.read(2)==struct.pack('>H',97)
        for table in (2,3):
            pointer=TABLE_BASE+u(TABLE_BASE+table*4)
            assert u(pointer+MAP*4)==u(pointer+(MAP+1)*4)
            f.seek(pointer+MAP*4);f.write(struct.pack('>I',0x80000000|ref))


def patch_code(fh,symbols):
    # Isolate the single Mini/Hunky upkeep debit, preserving its delay slot.
    start,end=0x806CB53C,0x806CBE44
    fh.seek(start-0x805FB300);body=fh.read(end-start)
    call=struct.pack('>I',0x0C000000|((0x806F91B4&0x0FFFFFFF)>>2))
    offsets=[i for i in range(0,len(body),4) if body[i:i+4]==call]
    assert len(offsets)==1,('Unexpected native crystal-drain call count',offsets)
    fh.seek(start-0x805FB300+offsets[0])
    fh.write(struct.pack('>I',0x0C000000|((int(symbols['krushaprisoncrystaldrain'],16)&0x0FFFFFFF)>>2)))
