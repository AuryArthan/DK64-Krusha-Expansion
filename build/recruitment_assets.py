"""R01 private static prison exterior; geometry derives from the original USA ROM.

Render layout follows DonkViewer (Ballaam, MIT), license in tools/map-atlas/.
No collision, entrance trigger, recruitment state or native resource replacement.
"""
from pathlib import Path
import struct,json,hashlib,zlib
from barrel_assets import read_file
ROOT=Path(__file__).resolve().parents[1]
MODEL_TYPE=59
OBJECT_ID=400
MODEL_INDEX=147
MIRROR_INDEX=148
TEXTURE_BASE=149
TEXTURE_TOKEN=7800
SOURCE_TEXTURES=tuple(range(0x514,0x51D))
POSITION=(3630.0,500.0,3409.5)
ORIGIN=(3359.333333333,500.0,3409.5)
SCALE=1/3

def u(b,p):return struct.unpack_from('>I',b,p)[0]
def selected(vertices,texture):
    return texture in SOURCE_TEXTURES and all(3050<=x/3<=3700 and 3000<=z/3<=3750 for x,y,z in vertices)

def model(rom):
    geo=read_file(rom,1,34);ds,vs=u(geo,0x34),u(geo,0x38);cs,ce=u(geo,0x68),u(geo,0x6C)
    vertices=bytearray();commands=[];materials=[];triangles=[];used_textures=set()
    def command(a,b=0):commands.append(struct.pack('>II',a,b))
    # Only map chunk1 contains this spatially isolated prison shell. Keep all
    # material changes pending until the next selected triangle; never emit
    # another part of the map's vertices, triangles, matrix or culling commands.
    for q in range(cs,ce,52):
        chunk=struct.unpack_from('>13I',geo,q)
        for start,size in [chunk[j:j+2] for j in (3,5,7,9)]:
            if not size:continue
            cursor=loaded=0;cache={};texture=None;materials=[]
            for p in range(ds+start,ds+start+size,8):
                a,b=struct.unpack_from('>II',geo,p);op=a>>24
                if op==1:
                    n=(a>>12)&255;first=((a>>1)&127)-n;off=vs+chunk[11]+cursor+(b&0xffffff)
                    assert off+n*16<=vs+chunk[11]+chunk[12]
                    for j in range(n):cache[first+j]=geo[off+j*16:off+(j+1)*16]
                    loaded+=n*16
                elif op in (5,6):
                    groups=[((a>>16)&255,(a>>8)&255,a&255)]
                    if op==6:groups.append(((b>>16)&255,(b>>8)&255,b&255))
                    for ids in groups:
                        raw=[cache[x//2] for x in ids];xyz=[struct.unpack_from('>3h',v) for v in raw]
                        if not selected(xyz,texture):continue
                        for ma,mb in materials:
                            if ma>>24==0xFD and mb in SOURCE_TEXTURES:
                                used_textures.add(mb);mb=TEXTURE_TOKEN+SOURCE_TEXTURES.index(mb)
                            command(ma,mb)
                        materials=[]
                        # Map vertices are prelit RGBA, not model-space normals.
                        command(0xD9FDFFFF,0) # clear G_LIGHTING
                        command(0x01003006,0x08000000+len(vertices))
                        for data,pos in zip(raw,xyz):
                            v=bytearray(data);local=[round(pos[i]/3-ORIGIN[i]) for i in range(3)]
                            struct.pack_into('>3h',v,0,*local);vertices+=v
                        command(0x05000204);triangles.append(dict(source_command=p,texture=texture,vertices=xyz))
                elif op==0xDF:cursor+=loaded;loaded=0;cache={};materials=[];texture=None
                elif op in (0,3):pass
                elif op in (0xDA,0xDE,2):
                    # These do not occur in the prison source ranges.
                    raise AssertionError(('unsupported map geometry command',hex(p),hex(op)))
                else:
                    materials.append((a,b))
                    if op==0xFD:texture=b
    assert len(triangles)==136,len(triangles)
    command(0xDF000000)
    donor=read_file(rom,4,0x267);old_v_end=u(donor,0x4C)
    dl=b''.join(commands);trans=struct.pack('>II',0xDF000000,0)
    # Static donor metadata and native object ownership remain native. Two
    # collision section counts are zero: R01 is a visual prototype only.
    new=bytearray(donor[:0x78]+dl+trans+vertices+donor[old_v_end:])
    new_vs=0x78+len(dl)+len(trans);new_end=new_vs+len(vertices);delta=new_end-old_v_end
    struct.pack_into('>3I',new,0x40,0x78,0x78+len(dl),new_vs)
    for p in range(0x4C,0x74,4):struct.pack_into('>I',new,p,u(donor,p)+delta)
    for p in (0x4C,0x50):struct.pack_into('>I',new,u(new,p),0)
    report=dict(triangles=len(triangles),vertices=len(vertices)//16,model_bytes=len(new),used_private_source_textures=sorted(used_textures),source_triangles=triangles,position=POSITION,scale=SCALE,origin=ORIGIN)
    return bytes(new),report

def payloads(rom):
    normal,report=model(rom)
    from mirror_assets import flip
    mirrored,n=flip(normal,4);assert n==136
    textures=[]
    for i in SOURCE_TEXTURES:
        data=read_file(rom,25,i)
        if i not in (0x515,0x517):
            # CI palette entries and RGBA16 mip levels only; indexed image
            # bytes515/517 stay exact. Preserve per-texel luminance and alpha.
            out=bytearray()
            for (v,) in struct.iter_unpack('>H',data):
                r,g,b=(v>>11&31),(v>>6&31),(v>>1&31)
                light=round(.2126*r+.7152*g+.0722*b)
                rgb=[round(light*x) for x in (.18,.32,.95)]
                out+=struct.pack('>H',rgb[0]<<11|rgb[1]<<6|rgb[2]<<1|v&1)
            data=bytes(out)
        textures.append(data)
    return [normal,mirrored]+textures

def prepare(rom_path):
    rom=Path(rom_path).read_bytes();assert not read_file(rom,4,MODEL_TYPE)
    used=set()
    for mid in range(221):
        b=read_file(rom,9,mid)
        if not b:continue
        for i in range(u(b,0)):
            typ,ident=struct.unpack_from('>HH',b,4+i*48+40);assert typ!=MODEL_TYPE
            if mid==34:used.add(ident)
    script=read_file(rom,10,34);used.update(struct.unpack('>%dH'%(len(script)//2),script))
    from m4_rewards import props,rows
    used.update(props(34).values());used.update(p['object_id'] for p in rows(34))
    static=zlib.decompress(rom[0xC29D4:],47)
    used.update(struct.unpack_from('>H',static,0x80755A20-0x80744460+i*8+2)[0] for i in range(113) if static[0x80755A20-0x80744460+i*8]==34)
    used.update(struct.unpack_from('>H',static,0x80747D50-0x80744460+i*4+2)[0] for i in range(8) if struct.unpack_from('>H',static,0x80747D50-0x80744460+i*4)[0]==34)
    assert OBJECT_ID not in used
    for i in range(len(SOURCE_TEXTURES)):assert not read_file(rom,25,TEXTURE_TOKEN+i)
    _,report=model(rom)
    target=ROOT/'include/recruitment_assets.generated.h'
    target.write_text('/* Generated R01 visual-only exterior identities. */\n'+''.join(f'#define {k} {v}\n' for k,v in [('RECRUITMENT_MODEL_TYPE',MODEL_TYPE),('RECRUITMENT_OBJECT_ID',OBJECT_ID),('RECRUITMENT_MODEL_INDEX',MODEL_INDEX),('RECRUITMENT_MIRROR_INDEX',MIRROR_INDEX),('RECRUITMENT_TEXTURE_BASE',TEXTURE_BASE),('RECRUITMENT_TEXTURE_TOKEN',TEXTURE_TOKEN),('RECRUITMENT_TEXTURE_COUNT',len(SOURCE_TEXTURES))]))
    (ROOT/'runtime/recruitment/r01').mkdir(parents=True,exist_ok=True)
    (ROOT/'runtime/recruitment/r01/extraction-latest.json').write_text(json.dumps(report,indent=2)+'\n')

def patch_setup(path,mid):
    if mid!=34:return
    path=Path(path);b=path.read_bytes();n=u(b,0)
    assert OBJECT_ID not in [struct.unpack_from('>H',b,4+i*48+42)[0] for i in range(n)]
    original=read_file((ROOT/'rom/dk64.z64').read_bytes(),9,34)
    # Source the inert Rock placement record; only its explicit visual fields
    # are copied, with native shell collisions absent from our private model.
    donor=next(original[4+i*48:4+(i+1)*48] for i in range(u(original,0)) if struct.unpack_from('>H',original,4+i*48+42)[0]==52)
    rec=bytearray(donor);struct.pack_into('>4f',rec,0,*POSITION,SCALE);struct.pack_into('>3f',rec,24,0,0,0);struct.pack_into('>HH',rec,40,MODEL_TYPE,OBJECT_ID)
    path.write_bytes(struct.pack('>I',n+1)+b[4:4+n*48]+rec+b[4+n*48:])
