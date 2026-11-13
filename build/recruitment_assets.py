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
SCALE=1/4
WALKWAY_TEXTURES=(0x10,0x24F)
WALKWAY_BRIGHTNESS=0.60
STONE_TEXTURES=(0x518,0x51A,0x51B,0x51C)

def metal_pixel(r,g,b):
    # The mixed51A image includes gray plates surrounded by green stone.
    # Preserve the low-chroma metal, including its native mip levels.
    return b*4>=g*3 and r*4>=g*3
# Two large mouths of the native entrance tunnel, ordered along each arch.
SEALED_ARCHES=(
 ((10054,1500,9938),(10066,1650,9944),(10099,1738,9973),(10190,1800,10001),(10262,1739,10051),(10309,1650,10057),(10326,1500,10065)),
 ((10193,1500,9640),(10205,1650,9646),(10243,1738,9679),(10340,1800,9711),(10407,1739,9758),(10447,1650,9762),(10463,1500,9769)),
)

def u(b,p):return struct.unpack_from('>I',b,p)[0]
def selected(vertices,texture):
    return texture in SOURCE_TEXTURES+WALKWAY_TEXTURES and all(3050<=x/3<=3700 and 3000<=z/3<=3750 for x,y,z in vertices)

def model(rom):
    geo=read_file(rom,1,34);ds,vs=u(geo,0x34),u(geo,0x38);cs,ce=u(geo,0x68),u(geo,0x6C)
    vertices=bytearray();commands=[];materials=[];triangles=[];used_textures=set();cap_material=None;source_points=set()
    def command(a,b=0):commands.append(struct.pack('>II',a,b))
    def material(values):
        for ma,mb in values:
            if ma>>24==0xFD and mb in SOURCE_TEXTURES:
                used_textures.add(mb);mb=TEXTURE_TOKEN+SOURCE_TEXTURES.index(mb)
            command(ma,mb)
    def emit(raw,xyz,texture,source_command=None):
        command(0xD9FDFFFF,0) # map vertices are prelit RGBA, not normals
        command(0x01003006,0x08000000+len(vertices))
        local_vertices=[]
        for data,pos in zip(raw,xyz):
            v=bytearray(data);local=[round(pos[i]/3-ORIGIN[i]) for i in range(3)]
            if texture in WALKWAY_TEXTURES:
                local[0]=-local[0];local[2]=-local[2] # turn only the annulus180 degrees
                for channel in range(12,15):v[channel]=round(v[channel]*WALKWAY_BRIGHTNESS)
            local_vertices.append(local)
            struct.pack_into('>3h',v,0,*local);vertices.extend(v)
        command(0x05000204);triangles.append(dict(source_command=source_command,texture=texture,vertices=xyz,local_vertices=local_vertices))
    # Only map chunk1 contains this spatially isolated prison shell. Keep all
    # material changes pending until the next selected triangle; never emit
    # another part of the map's vertices, triangles, matrix or culling commands.
    for q in range(cs,ce,52):
        chunk=struct.unpack_from('>13I',geo,q)
        for start,size in [chunk[j:j+2] for j in (3,5,7,9)]:
            if not size:continue
            cursor=loaded=0;cache={};texture=None;materials=[];state_history=[]
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
                        source_points.update(xyz)
                        if texture==0x51B and cap_material is None:cap_material=list(state_history)
                        material(materials);materials=[]
                        emit(raw,xyz,texture,p)
                elif op==0xDF:cursor+=loaded;loaded=0;cache={};materials=[];texture=None;state_history=[]
                elif op in (0,3):pass
                elif op in (0xDA,0xDE,2):
                    # These do not occur in the prison source ranges.
                    raise AssertionError(('unsupported map geometry command',hex(p),hex(op)))
                else:
                    materials.append((a,b));state_history.append((a,b))
                    if op==0xFD:texture=b
    assert len(triangles)==202,len(triangles)
    assert sum(t['texture'] in WALKWAY_TEXTURES for t in triangles)==66
    assert cap_material
    material(cap_material)
    # A double-sided stone infill follows the existing arches exactly. Seal
    # both ends of the large tunnel; leave the five-vertex rear opening alone.
    command(0xD9FFF9FF,0) # clear both cull flags for the infill
    import math
    for arch in SEALED_ARCHES:
        assert set(arch)<=source_points, 'Entrance boundary moved in source ROM'
        dx,dz=arch[-1][0]-arch[0][0],arch[-1][2]-arch[0][2];length=math.hypot(dx,dz)
        raw=[]
        for x,y,z in arch:
            uvx=round(((x-arch[0][0])*dx+(z-arch[0][2])*dz)/length/3*20)
            uvy=round((y-1500)/3*20)
            raw.append(struct.pack('>hhhHhh4B',x,y,z,0,uvx,uvy,170,170,170,255))
        for j in range(1,len(arch)-1):emit([raw[0],raw[j],raw[j+1]],[arch[0],arch[j],arch[j+1]],0x51B)
    assert len(triangles)==212
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
    report=dict(triangles=len(triangles),vertices=len(vertices)//16,model_bytes=len(new),used_private_source_textures=sorted(used_textures),source_triangles=triangles,position=POSITION,scale=SCALE,origin=ORIGIN,walkway_triangles=66,sealed_arches=SEALED_ARCHES,infill_triangles=10,walkway_rotation_degrees=180,walkway_brightness=WALKWAY_BRIGHTNESS)
    return bytes(new),report

def payloads(rom):
    normal,report=model(rom)
    from mirror_assets import flip
    mirrored,n=flip(normal,4);assert n==report['triangles']
    textures=[]
    for i in SOURCE_TEXTURES:
        data=read_file(rom,25,i)
        if i in STONE_TEXTURES:
            # Preserve native gray519, mixed51A metal and underwater CI maps.
            # Tint only green stone, retaining mip levels and alpha.
            out=bytearray()
            for (v,) in struct.iter_unpack('>H',data):
                r,g,b=(v>>11&31),(v>>6&31),(v>>1&31)
                if i==0x51A and metal_pixel(r,g,b):
                    out+=struct.pack('>H',v);continue
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
