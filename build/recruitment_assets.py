"""R01 private static prison exterior; geometry derives from the original USA ROM.

Render layout follows DonkViewer (Ballaam, MIT), license in tools/map-atlas/.
R02 adds native private-model collision; original world resources stay intact.
"""
from pathlib import Path
import struct,json,hashlib,zlib,math
from barrel_assets import read_file
ROOT=Path(__file__).resolve().parents[1]
MODEL_TYPE=59
OBJECT_ID=400
MODEL_INDEX=147
MIRROR_INDEX=148
TEXTURE_BASE=149
TEXTURE_TOKEN=7800
SOURCE_TEXTURES=tuple(range(0x514,0x51D))
# The ring extends 20 model units below the deck, crossing the sea at Y 490.
POSITION=(2977.0,493.0,3288.0)
FACING_TARGET=(2800.0,2200.0) # central DK island; rear aperture faces the island
ROTATION_Y=math.atan2(FACING_TARGET[0]-POSITION[0],FACING_TARGET[1]-POSITION[2])-math.atan2(-.438993779,.898490440)

def rotate(point):
    x,y,z=point;c,s=math.cos(ROTATION_Y),math.sin(ROTATION_Y)
    return (c*x+s*z,y,-s*x+c*z)
ORIGIN=(3359.333333333,500.0,3409.5)
SCALE=.23 # user requested8% less than the reviewed quarter scale
SAFE_DEPTH=24.0
TUNNEL_EXTENSION=190.0 # local units;43.7 world units inward, mouth unchanged
INNER_ARCH=((-83,0,114),(-79,33,116),(-61,50,125),(-43,33,133),(-38,0,136))
WALKWAY_TEXTURES=(0x10,0x24F)
WALKWAY_BRIGHTNESS=0.60
STONE_TINT=(0.24,0.30,0.60)
METAL_BRIGHTNESS=0.45
STONE_TEXTURES=(0x518,0x51A,0x51B,0x51C)

def metal_pixel(r,g,b):
    # The mixed51A image includes gray plates surrounded by green stone.
    # Identify the low-chroma metal consistently at all native mip levels.
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
    lighting=True
    vertices=bytearray();commands=[];materials=[];triangles=[];used_textures=set();cap_material=None;tunnel_material=None;source_points=set();tunnel_caps=0
    def command(a,b=0):
        nonlocal lighting
        if a>>24==0xD9:lighting=(lighting and bool(a&0x20000))or bool(b&0x20000)
        commands.append(struct.pack('>II',a,b))
    def material(values):
        for ma,mb in values:
            if ma>>24==0xFD and mb in SOURCE_TEXTURES:
                used_textures.add(mb);mb=TEXTURE_TOKEN+SOURCE_TEXTURES.index(mb)
            command(ma,mb)
    def emit(raw,xyz,texture,source_command=None,local_coords=False,tunnel=False):
        if lighting:command(0xD9FDFFFF,0) # map vertices are prelit RGBA, not normals
        command(0x01003006,0x08000000+len(vertices))
        local_vertices=[]
        for data,pos in zip(raw,xyz):
            v=bytearray(data);local=[round(pos[i]) if local_coords else round(pos[i]/3-ORIGIN[i]) for i in range(3)]
            if texture in WALKWAY_TEXTURES and not local_coords:
                local[0]=-local[0];local[2]=-local[2] # turn only the annulus180 degrees
                for channel in range(12,15):v[channel]=round(v[channel]*WALKWAY_BRIGHTNESS)
            if tunnel:
                for channel in range(12,15):v[channel]=round(v[channel]*.035)
            local=[round(c) for c in rotate(local)]
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
                        if texture==0x514 and tunnel_material is None:tunnel_material=list(state_history)
                        material(materials);materials=[]
                        local=[tuple(round(pos[i]/3-ORIGIN[i]) for i in range(3)) for pos in xyz]
                        is_cap=texture==0x51A and all(v in INNER_ARCH for v in local)
                        if is_cap:
                            # Move only the three original back-cap triangles.
                            # Keep the mouth/arch/sphere outline and all eight
                            # existing outer tunnel wall triangles unchanged.
                            from recruitment_collision import LOCAL_DOOR_NORMAL
                            xyz=[(pos[0]-LOCAL_DOOR_NORMAL[0]*TUNNEL_EXTENSION*3,pos[1],pos[2]-LOCAL_DOOR_NORMAL[1]*TUNNEL_EXTENSION*3) for pos in xyz]
                            tunnel_caps+=1
                        from recruitment_collision import LOCAL_DOOR_CENTER,LOCAL_DOOR_TANGENT,LOCAL_DOOR_NORMAL
                        is_wall=texture==0x514 and all(abs((v[0]-LOCAL_DOOR_CENTER[0])*LOCAL_DOOR_TANGENT[0]+(v[2]-LOCAL_DOOR_CENTER[2])*LOCAL_DOOR_TANGENT[1])<38 and 0<=v[1]<=65 and -70<(v[0]-LOCAL_DOOR_CENTER[0])*LOCAL_DOOR_NORMAL[0]+(v[2]-LOCAL_DOOR_CENTER[2])*LOCAL_DOOR_NORMAL[1]<12 for v in local)
                        emit(raw,xyz,texture,p,tunnel=is_cap or is_wall)
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
    for arch in SEALED_ARCHES:
        assert set(arch)<=source_points, 'Entrance boundary moved in source ROM'
        dx,dz=arch[-1][0]-arch[0][0],arch[-1][2]-arch[0][2];length=math.hypot(dx,dz)
        raw=[]
        for x,y,z in arch:
            uvx=round(((x-arch[0][0])*dx+(z-arch[0][2])*dz)/length/3*20)
            uvy=round((y-1500)/3*20)
            raw.append(struct.pack('>hhhHhh4B',x,y,z,0,uvx,uvy,170,170,170,255))
        for j in range(1,len(arch)-1):emit([raw[0],raw[j],raw[j+1]],[arch[0],arch[j],arch[j+1]],0x51B)
    assert len(triangles)==212 and tunnel_caps==3 and tunnel_material
    from recruitment_collision import LOCAL_DOOR_NORMAL,LOCAL_DOOR_TANGENT
    inner=INNER_ARCH
    deep=[(v[0]-LOCAL_DOOR_NORMAL[0]*TUNNEL_EXTENSION,v[1],v[2]-LOCAL_DOOR_NORMAL[1]*TUNNEL_EXTENSION) for v in inner]
    material(tunnel_material);command(0xD9FFF9FF,0)
    def tunnel_triangle(points):
        raw=[struct.pack('>3hH2h4B',0,0,0,0,round(v[0]*12),round(v[2]*12),145,145,145,255)for v in points]
        emit(raw,points,0x514,local_coords=True,tunnel=True)
    for i in range(4):
        tunnel_triangle([inner[i],deep[i],deep[i+1]])
        tunnel_triangle([inner[i],deep[i+1],inner[i+1]])
    tunnel_triangle([inner[0],inner[-1],deep[-1]])
    tunnel_triangle([inner[0],deep[-1],deep[0]])
    assert len(triangles)==222
    # Solid low-poly crown, with baked vertex shading and native primitive
    # alpha for distance fading. No textures, extra actors or particle effects.
    from recruitment_spikes import triangles as spike_triangles
    command(0xE7000000);command(0xD7000000,0)
    command(0xFCFFFFFF,0xFFFE773B) # RGB=SHADE, alpha=PRIMITIVE, both cycles
    crown=spike_triangles(LOCAL_DOOR_TANGENT,LOCAL_DOOR_NORMAL)
    for first in range(0,72,24):
        # Share each horn's two8-vertex rings and tip. This fits17 vertices
        # in one native cache load instead of duplicating216 vertices, and
        # keeps table27 inside its existing reserved ROM bank.
        cache={};nodes=[];faces=[]
        for points,colors in crown[first:first+24]:
            local=[tuple(round(c) for c in rotate(p)) for p in points];indices=[]
            for point,color in zip(local,colors):
                key=point+color
                if key not in cache:cache[key]=len(nodes);nodes.append((point,color))
                indices.append(cache[key])
            faces.append(indices)
            triangles.append(dict(source_command=None,texture=None,vertices=points,local_vertices=local,spike=True))
        assert len(nodes)==17
        command(0x01000000|len(nodes)<<12|len(nodes)<<1,0x08000000+len(vertices))
        for point,color in nodes:vertices+=struct.pack('>3hH2h4B',*point,0,0,0,*color,255)
        for a,b in zip(faces[::2],faces[1::2]):
            command(0x06000000|a[0]*2<<16|a[1]*2<<8|a[2]*2,b[0]*2<<16|b[1]*2<<8|b[2]*2)
    assert len(triangles)==294
    # Reuse vanilla tether/anchors, with shared vertices and TRI2 batches.
    from recruitment_bridge import triangles as bridge_triangles
    bridge=bridge_triangles(rom)
    for texture in (0x24e,0x251,0x50f):
        group=[v for v in bridge if v['texture']==texture]
        material(group[0]['material']);command(0xD9FDFFFF,0)
        nodes=[];cache={};faces=[]
        def flush():
            if not faces:return
            command(0x01000000|len(nodes)<<12|len(nodes)<<1,0x08000000+len(vertices))
            for raw in nodes:vertices.extend(raw)
            for i in range(0,len(faces),2):
                a=faces[i]
                if i+1<len(faces):
                    b=faces[i+1];command(0x06000000|a[0]*2<<16|a[1]*2<<8|a[2]*2,b[0]*2<<16|b[1]*2<<8|b[2]*2)
                else:command(0x05000000|a[0]*2<<16|a[1]*2<<8|a[2]*2)
        for t in group:
            local=[];raws=[]
            for raw,point in zip(t['raw'],t['world']):
                point=tuple(round((point[i]-POSITION[i])/SCALE)for i in range(3));v=bytearray(raw);struct.pack_into('>3h',v,0,*point);raws.append(bytes(v));local.append(point)
            if len(set(raws)-cache.keys())+len(nodes)>32:flush();nodes=[];cache={};faces=[]
            indices=[]
            for v in raws:
                if v not in cache:cache[v]=len(nodes);nodes.append(v)
                indices.append(cache[v])
            faces.append(indices);triangles.append(dict(source_command=t['source_command'],texture=texture,vertices=t['world'],local_vertices=local,bridge=True))
        flush()
    material(tunnel_material) # restore the native textured material state
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
    triangle_commands=sum(1 for c in commands if c[0]in(5,6))
    report=dict(triangle_commands=triangle_commands,bridge_triangles=36,triangles=len(triangles),vertices=len(vertices)//16,model_bytes=len(new),used_private_source_textures=sorted(used_textures),source_triangles=triangles,position=POSITION,scale=SCALE,origin=ORIGIN,rotation_y_degrees=math.degrees(ROTATION_Y),facing_target=FACING_TARGET,spikes=3,spike_triangles=72,walkway_triangles=66,sealed_arches=SEALED_ARCHES,infill_triangles=10,tunnel_extension_local=TUNNEL_EXTENSION,tunnel_extension_world=TUNNEL_EXTENSION*SCALE,tunnel_added_triangles=10,tunnel_moved_cap_triangles=tunnel_caps,walkway_rotation_degrees=180,walkway_brightness=WALKWAY_BRIGHTNESS)
    from recruitment_collision import with_collision
    return with_collision(bytes(new),report)

def payloads(rom):
    normal,report=model(rom)
    from mirror_assets import flip
    mirrored,n=flip(normal,4);assert n==report['triangle_commands']
    textures=[]
    for i in SOURCE_TEXTURES:
        data=read_file(rom,25,i)
        if i in STONE_TEXTURES or i==0x519:
            # Darken gray519 and mixed51A metal independently of the stone.
            # Retain native detail, mip layouts and alpha; CI base stays native.
            out=bytearray()
            for (v,) in struct.iter_unpack('>H',data):
                r,g,b=(v>>11&31),(v>>6&31),(v>>1&31)
                if i==0x519 or (i==0x51A and metal_pixel(r,g,b)):
                    rgb=[round(channel*METAL_BRIGHTNESS) for channel in (r,g,b)]
                else:
                    light=round(.2126*r+.7152*g+.0722*b)
                    rgb=[round(light*x) for x in STONE_TINT]
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
    # Native80603450's Isles cylinders are14-byte records. The radius alone
    # is updated at runtime; verify the USA prison row before exposing it.
    music_row=0x8074626E
    assert struct.unpack_from('>5h4B',static,music_row-0x80744460)==(3610,477,3302,-1,630,0,112,0,0)
    assert struct.unpack_from('>5h4B',static,0x80746244-0x80744460)==(2076,477,3750,-1,980,0,110,0,0)
    used.update(struct.unpack_from('>H',static,0x80755A20-0x80744460+i*8+2)[0] for i in range(113) if static[0x80755A20-0x80744460+i*8]==34)
    used.update(struct.unpack_from('>H',static,0x80747D50-0x80744460+i*4+2)[0] for i in range(8) if struct.unpack_from('>H',static,0x80747D50-0x80744460+i*4)[0]==34)
    assert OBJECT_ID not in used
    for i in range(len(SOURCE_TEXTURES)):assert not read_file(rom,25,TEXTURE_TOKEN+i)
    _,report=model(rom)
    target=ROOT/'include/recruitment_assets.generated.h'
    target.write_text('/* Generated private recruitment exterior identities/collision. */\n'+''.join(f'#define {k} {v}\n' for k,v in [('RECRUITMENT_MODEL_TYPE',MODEL_TYPE),('RECRUITMENT_OBJECT_ID',OBJECT_ID),('RECRUITMENT_MODEL_INDEX',MODEL_INDEX),('RECRUITMENT_MIRROR_INDEX',MIRROR_INDEX),('RECRUITMENT_TEXTURE_BASE',TEXTURE_BASE),('RECRUITMENT_TEXTURE_TOKEN',TEXTURE_TOKEN),('RECRUITMENT_TEXTURE_COUNT',len(SOURCE_TEXTURES))]))
    from recruitment_collision import DOOR_CENTER,DOOR_TANGENT,DOOR_NORMAL
    door=[POSITION[i]+DOOR_CENTER[i]*SCALE for i in range(3)]
    with target.open('a') as header:
        header.write(f'#define RECRUITMENT_MODEL_X {POSITION[0]:.9f}f\n#define RECRUITMENT_MODEL_Z {POSITION[2]:.9f}f\n#define RECRUITMENT_COLLISION_WALLS {report["collision"]["walls"]}\n')
    with target.open('a') as header:
        header.write('#define RECRUITMENT_MUSIC_RADIUS_ADDRESS 0x80746276\n#define RECRUITMENT_MUSIC_RADIUS_ORIGINAL 630\n#define RECRUITMENT_MUSIC_RADIUS_EXPANDED 900\n#define RECRUITMENT_SHIP_MUSIC_RADIUS_ADDRESS 0x8074624C\n#define RECRUITMENT_SHIP_MUSIC_RADIUS_ORIGINAL 980\n')
    values=dict(X=door[0],Y=door[1],Z=door[2],TX=DOOR_TANGENT[0],TZ=DOOR_TANGENT[1],NX=DOOR_NORMAL[0],NZ=DOOR_NORMAL[1],SAFE_X=door[0]+SAFE_DEPTH*DOOR_NORMAL[0],SAFE_Z=door[2]+SAFE_DEPTH*DOOR_NORMAL[1])
    with target.open('a') as header:
        for name,value in values.items():header.write(f'#define RECRUITMENT_DOOR_{name} {value:.9f}f\n')
    (ROOT/'runtime/recruitment/r01').mkdir(parents=True,exist_ok=True)
    (ROOT/'runtime/recruitment/r01/extraction-latest.json').write_text(json.dumps(report,indent=2)+'\n')

def patch_setup(path,mid):
    if mid!=34:return
    path=Path(path);b=path.read_bytes();n=u(b,0)
    assert OBJECT_ID not in [struct.unpack_from('>H',b,4+i*48+42)[0] for i in range(n)]
    original=read_file((ROOT/'rom/dk64.z64').read_bytes(),9,34)
    # Source the inert Rock placement record; only its explicit visual fields
    # are copied; our private model supplies its own native wall/floor sections.
    donor=next(original[4+i*48:4+(i+1)*48] for i in range(u(original,0)) if struct.unpack_from('>H',original,4+i*48+42)[0]==52)
    rec=bytearray(donor);struct.pack_into('>4f',rec,0,*POSITION,SCALE);struct.pack_into('>3f',rec,24,0,0,0);struct.pack_into('>HH',rec,40,MODEL_TYPE,OBJECT_ID)
    path.write_bytes(struct.pack('>I',n+1)+b[4:4+n*48]+rec+b[4+n*48:])
