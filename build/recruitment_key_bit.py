"""Complete the private inserted key's truncated native shank on bone3.

The original lock is untouched. The small two-tooth bit extends into the lock
past its existing shaft anchor, and turns with the same skeleton matrix.
"""
import math
import struct

# Clockwise viewed from positiveX. Local negativeZ is the insertion end.
OUTLINE = ((8,18),(-112,18),(-112,-74),(-84,-74),(-84,-20),
           (-62,-20),(-62,-86),(-30,-86),(-30,-18),(8,-18))


def triangles():
    # Ear clipping in the (Z,Y) plane, preserving the concave teeth/notches.
    poly = list(range(len(OUTLINE)))
    cross = lambda a,b,c: (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    orientation = 1 if sum(OUTLINE[i][0]*OUTLINE[(i+1)%len(poly)][1]-OUTLINE[(i+1)%len(poly)][0]*OUTLINE[i][1] for i in poly)>0 else -1
    faces = []
    while len(poly)>3:
        for n,b in enumerate(poly):
            a,c=poly[n-1],poly[(n+1)%len(poly)]
            A,B,C=(OUTLINE[i] for i in (a,b,c))
            if cross(A,B,C)*orientation <= 0: continue
            if any(all(cross(p,q,OUTLINE[i])*orientation>=0 for p,q in ((A,B),(B,C),(C,A))) for i in poly if i not in (a,b,c)): continue
            faces.append((a,b,c));poly.pop(n);break
        else: raise AssertionError('Non-simple key outline')
    faces.append(tuple(poly))
    points=lambda x,i: (x,OUTLINE[i][1],OUTLINE[i][0])
    result=[]
    # Fix orientation by comparing triangle normal against desired face side.
    for x in (-12,12):
        for face in faces:
            tri=[points(x,i) for i in face]
            a,b,c=tri
            normal=(b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1])
            if normal*x<0:tri.reverse()
            result.append(tri)
    for i in range(len(OUTLINE)):
        j=(i+1)%len(OUTLINE)
        a,b,c,d=points(-12,i),points(12,i),points(12,j),points(-12,j)
        pair=[[a,b,c],[a,c,d]]
        # For a CCW Z/Y polygon, cross of the X extrusion points outwards.
        if orientation<0:pair=[list(reversed(t)) for t in pair]
        result.extend(pair)
    assert len(result)==36
    return result


def complete_key(source):
    u=lambda off:struct.unpack_from('>I',source,off)[0]
    base=u(0);end=u(4)-base+40;start=u(end)-base+40
    assert (start,end)==(0xD08,0x12D0) and source[end-8:end]==bytes.fromhex('df00000000000000')
    vertices=bytearray()
    for a,b,c in triangles():
        v=[b[i]-a[i] for i in range(3)];w=[c[i]-a[i] for i in range(3)]
        n=(v[1]*w[2]-v[2]*w[1],v[2]*w[0]-v[0]*w[2],v[0]*w[1]-v[1]*w[0])
        length=math.sqrt(sum(x*x for x in n));assert length
        normals=[round(x*127/length) for x in n]
        for p in (a,b,c):vertices+=struct.pack('>3hH2h3bB',*p,0,0,0,*normals,255)
    commands=bytearray()
    # Join the EXISTING key draw block while its material/lighting is active.
    # A second G_DL_NOPUSH segment7 header replaces the native segment binding
    # (8061324C/80614C38), skipping the original bow/shank. Put all teeth before
    # its original lighting reset and segment7 alternate-branch marker.
    insert=0x1050
    assert source[insert:insert+16]==bytes.fromhex('d9f9ffff000000000000000000000007')
    count=len(vertices)//16
    for first in range(0,count,24):
        batch=min(24,count-first)
        commands+=struct.pack('>II',0x01000000|batch<<12|batch<<1,0x03000000+start-40+first*16)
        for i in range(0,batch,6):
            commands+=struct.pack('>II',0x06000000|i*2<<16|(i+1)*2<<8|(i+2)*2,(i+3)*2<<16|(i+4)*2<<8|(i+5)*2)
    delta=len(vertices)+len(commands)
    out=bytearray(source[:start]+vertices+source[start:insert]+commands+source[insert:])
    for off in (4,8,12,16):
        assert u(off)>=base+end-40
        struct.pack_into('>I',out,off,u(off)+delta)
    struct.pack_into('>I',out,end+delta,u(end)+len(vertices))
    assert out[40:start]==source[40:start] and out[end+delta+4:]==source[end+4:]
    new_start=u(end)+len(vertices)-base+40
    new_end=end+delta
    matrices=[w&0xFFFFFF for a,w in struct.iter_unpack('>II',out[new_start:new_end]) if a>>24==0xDA]
    assert matrices==[0x40,0xC0,0x80,0], matrices
    branches=[w for a,w in struct.iter_unpack('>II',out[new_start:new_end]) if a==0xDE010000]
    assert branches==[0x07000000], branches
    return bytes(out)
