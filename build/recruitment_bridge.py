"""Reuse the original Isles prison's thin tether and two anchor plinths.

Only copy the small isolated connector; keep the vanilla connection intact.
End plinths scale uniformly .23; stretch the central tether to span the new gap.
"""
import math,struct
from barrel_assets import read_file
from recruitment_assets import POSITION
SHIP=(2900.,500.,3520.)
PRISON=(2954.,POSITION[1],3340.)
SOURCE_A=(2973.5,500.,3681.666666667)
SOURCE_B=(3106.,500.,3501.666666667)
SCALE=.23
TETHER_TINT=(.54,.57,.63)


def tint_vertex(raw):
    # The Model2 copy uses prelit vertex colors. Keep the texture and its
    # shading detail, soften the strongest warm accents and bias toward blue.
    red, green, blue = raw[12:15]
    gray = .21 * red + .72 * green + .07 * blue
    tinted = bytes(round((.9 * gray + .1 * channel) * factor)
                   for channel, factor in zip((red, green, blue), TETHER_TINT))
    return raw[:12] + tinted + raw[15:]


def triangles(rom):
    geo=read_file(rom,1,34);u=lambda p:struct.unpack_from('>I',geo,p)[0];ds,vs,cs=u(0x34),u(0x38),u(0x68);chunk=struct.unpack_from('>13I',geo,cs+52);out=[]
    dx,dz=SOURCE_B[0]-SOURCE_A[0],SOURCE_B[2]-SOURCE_A[2];length=math.hypot(dx,dz);ax,az=dx/length,dz/length
    dx,dz=PRISON[0]-SHIP[0],PRISON[2]-SHIP[2];span=math.hypot(dx,dz);nx,nz=dx/span,dz/span
    for start,size in[chunk[j:j+2]for j in(3,5,7,9)]:
        if not size:continue
        cursor=loaded=0;cache={};texture=None;history=[]
        for p in range(ds+start,ds+start+size,8):
            a,b=struct.unpack_from('>II',geo,p);op=a>>24
            if op==1:
                n=a>>12&255;first=(a>>1&127)-n;off=vs+chunk[11]+cursor+(b&0xffffff)
                for j in range(n):cache[first+j]=geo[off+j*16:off+(j+1)*16]
                loaded+=n*16
            elif op in(5,6):
                groups=[((a>>16)&255,(a>>8)&255,a&255)]
                if op==6:groups.append(((b>>16)&255,(b>>8)&255,b&255))
                for ids in groups:
                    raw=[cache[x//2]for x in ids];xyz=[tuple(x/3 for x in struct.unpack_from('>3h',v))for v in raw]
                    if texture not in(0x50f,0x24e,0x251)or not all(2900<x<3170 and 495<=y<=525 and 3440<z<3750 for x,y,z in xyz):continue
                    mapped=[]
                    for x,y,z in xyz:
                        t=((x-SOURCE_A[0])*ax+(z-SOURCE_A[2])*az)/length;side=-(x-SOURCE_A[0])*az+(z-SOURCE_A[2])*ax
                        if texture!=0x50f:
                            end=0 if t<.5 else 1;center=SOURCE_A if end==0 else SOURCE_B;anchor=SHIP if end==0 else PRISON
                            along=(x-center[0])*ax+(z-center[2])*az
                            mapped.append((anchor[0]+(along*nx-side*nz)*SCALE,anchor[1]+(y-500)*SCALE,anchor[2]+(along*nz+side*nx)*SCALE))
                        else:
                            # Bury both rope ends in the anchor bodies; do not
                            # stretch the native endpoint overhang past them.
                            t=max(0.,min(1.,t))
                            mapped.append((SHIP[0]+t*dx-side*SCALE*nz,SHIP[1]+t*(PRISON[1]-SHIP[1])+(y-500)*SCALE,SHIP[2]+t*dz+side*SCALE*nx))
                    # Same native pipeline, omit redundant previous texture loads.
                    material=history if texture==0x24e else history[:10]+history[20:] if texture==0x251 else history[:4]+history[-18:]
                    shaded = [tint_vertex(vertex) for vertex in raw]
                    out.append(dict(raw=shaded, world=mapped, material=material,
                                    texture=texture, source_command=p))
            elif op==0xdf:cursor+=loaded;loaded=0;cache={};texture=None;history=[]
            elif op not in(0,3):
                history.append((a,b))
                if op==0xfd:texture=b
    assert len(out)==36,len(out)
    return out
