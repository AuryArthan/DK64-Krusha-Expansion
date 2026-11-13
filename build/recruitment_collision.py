"""R02 native Model2 wall/floor sections for the private prison only.

Native layouts verified against USA loaders8066C2D0/80633A1C and the supplied
DK64 decompilation. Records are local model units, transformed by native .25
setup scale. Original world collision files are never patched.
"""
import struct,math

# Local rear arch, derived from the accepted render mesh. X/Z tangent runs
# left-to-right; outward points from the sphere toward the rear landing.
DOOR_CENTER=(-60.5,0.0,125.0)
DOOR_TANGENT=(.898490440,.438993779)
DOOR_NORMAL=(-.438993779,.898490440)

def normal(verts):
    a,b,c=verts;u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
    return n,math.sqrt(sum(x*x for x in n))

def with_collision(model,report):
    u=lambda p:struct.unpack_from('>I',model,p)[0]
    walls=[];floors=[];seen_w=set();seen_f=set()
    def add(target,seen,verts):
        verts=tuple(tuple(round(x) for x in v) for v in verts)
        key=tuple(sorted(verts))
        if key not in seen:target.append(verts);seen.add(key)
    for t in report['source_triangles']:
        verts=t['local_vertices'];n,length=normal(verts)
        if length<1:continue
        if abs(n[1])<.90*length:add(walls,seen_w,verts)
        if n[1]>.55*length:add(floors,seen_f,verts)
    # A small supported staging area inside the aperture; no R03 interior yet.
    # The invisible backstop is twelve world units behind the visible arch. Mini
    # Tiny can occupy the entrance volume, but cannot wander into an unbuilt room.
    cx,cy,cz=DOOR_CENTER;tx,tz=DOOR_TANGENT;nx,nz=DOOR_NORMAL
    def point(side,depth,y):return (cx+tx*side+nx*depth,y,cz+tz*side+nz*depth)
    a,b,c,d=[point(s,-48,y) for s,y in [(-27,0),(27,0),(27,54),(-27,54)]]
    for tri in [(a,b,c),(a,c,d),(c,b,a),(d,c,a)]:
        # Keep opposing faces of the readiness backstop explicitly.
        walls.append(tuple(tuple(round(x) for x in p) for p in tri))
    a,b,c,d=[point(s,depth,0) for s,depth in [(-28,20),(-28,-56),(28,-56),(28,20)]]
    for tri in [(a,b,c),(a,c,d)]:
        if normal(tri)[0][1]<0:tri=tri[::-1]
        add(floors,seen_f,tri)
    wall_bytes=struct.pack('>I',len(walls))+b''.join(struct.pack('>9h4B',*(x for v in t for x in v),0,0,255,0) for t in walls)
    points=[v for t in floors for v in t];bounds=[min(p[i] for p in points) for i in range(3)]+[max(p[i] for p in points) for i in range(3)]
    floor_bytes=struct.pack('>I6h',len(floors),*bounds)+b''.join(struct.pack('>9hBbBBH',*(x for v in t for x in v),15,-1,3,0,0) for t in floors)
    start=u(0x4C);old_tail=u(0x54);new_tail=start+len(wall_bytes)+len(floor_bytes);delta=new_tail-old_tail
    out=bytearray(model[:start]+wall_bytes+floor_bytes+model[old_tail:])
    struct.pack_into('>II',out,0x4C,start,start+len(wall_bytes))
    for p in range(0x54,0x74,4):struct.pack_into('>I',out,p,u(p)+delta)
    report.update(collision=dict(walls=len(walls),floors=len(floors),wall_stride=22,floor_stride=24,floor_bounds=bounds,door_center=DOOR_CENTER,door_tangent=DOOR_TANGENT,door_normal=DOOR_NORMAL,readiness_backstop_world_depth=12,wall_vertices=walls,floor_vertices=floors),model_bytes=len(out))
    return bytes(out),report
