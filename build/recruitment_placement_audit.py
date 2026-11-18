"""Read-only geometry/code checks for the illustrated attachment/key revision."""
import struct,zlib,math,importlib.util
from pathlib import Path
from barrel_assets import read_file

def height(x,z,row):
 a,b,c=[row[i:i+3]for i in(0,3,6)];den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
 if not den:return None
 u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/den;v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/den
 return u*a[1]+v*b[1]+(1-u-v)*c[1]if min(u,v,1-u-v)>=-1e-5 else None

def faces(data):
 u=lambda o:struct.unpack_from('>I',data,o)[0];cache={};out=[]
 for a,b in struct.iter_unpack('>II',data[u(0x40):u(0x44)]):
  op=a>>24
  if op==1:
   n=a>>12&255;first=(a>>1&127)-n;off=u(0x48)+(b&0xffffff)
   for i in range(n):cache[first+i]=data[off+i*16:off+(i+1)*16]
  if op in(5,6):
   groups=[[(a>>16)&255,(a>>8)&255,a&255]]
   if op==6:groups.append([(b>>16)&255,(b>>8)&255,b&255])
   out.extend([[cache[i//2]for i in ids]for ids in groups])
 return out

def extra(r,b,clean,path,check,report,sym):
 from recruitment_assets import POSITION,SCALE,WALKWAY_TEXTURES
 from recruitment_bridge import SHIP,PRISON
 from recruitment_spikes import ENLARGEMENT
 from recruitment_keys import rows
 root=Path(__file__).resolve().parents[1]
 check('resident gameplay code and data byte-exact',r[0x1fed020:0x2007020]==b[0x1fed020:0x2007020])
 check('native global overlay byte-exact',zlib.decompressobj(-15).decompress(r[0x113fa:])==zlib.decompressobj(-15).decompress(b[0x113fa:]))
 check('pickup cue and palettes byte-exact',all(read_file(r,27,i)==read_file(b,27,i)for i in(*range(187,192),229)))
 old,new=faces(read_file(b,27,147)),faces(read_file(r,27,147));check('same330 triangles and unchanged shell tunnel and walkway',len(old)==len(new)==330 and old[:222]==new[:222])
 check('horn colors and UVs unchanged',all(x[6:]==y[6:]for x,y in zip((v for t in old[222:294]for v in t),(v for t in new[222:294]for v in t))))
 check('horn enlargement exactly10 percent',ENLARGEMENT==1.10)
 for h,tip in enumerate((347,291,228)):
  vertices=[v for t in new[222+h*24:246+h*24]for v in t];ys=[struct.unpack_from('>h',v,2)[0]for v in vertices]
  check('enlarged horn tip and planted root '+str(h),max(ys)==tip and min(ys)==(211,190,135)[h],dict(min=min(ys),max=max(ys)))
 atlas_spec=importlib.util.spec_from_file_location('native_floor_audit',root/'tools/build-map-atlas.py');atlas=importlib.util.module_from_spec(atlas_spec);atlas_spec.loader.exec_module(atlas)
 geo=read_file(clean,1,34);cells=math.prod(struct.unpack_from('>2H',geo,24));floors=atlas.collision(read_file(clean,3,34),cells,True)
 walk=[]
 for t in report['source_triangles']:
  if t['texture']in WALKWAY_TEXTURES:walk.append(sum([[POSITION[i]+v[i]*SCALE for i in range(3)]for v in t['local_vertices']],[])+[0])
 check('anchors follow illustration rear and original-tether side',SHIP==(2900.,500.,3520.)and PRISON==(2954.,498.,3340.))
 for name,anchor,ground in(('ship',SHIP,floors),('prison',PRISON,walk)):
  base=sorted({tuple(v)for t in report['source_triangles']if t.get('bridge')and t['texture']==0x24e for v in t['vertices']if abs(v[1]-anchor[1])<.001 and math.hypot(v[0]-anchor[0],v[2]-anchor[2])<20})
  check('four planted anchor corners '+name,len(base)==4,base)
  center=(sum(p[0]for p in base)/4,sum(p[2]for p in base)/4);base.sort(key=lambda p:math.atan2(p[2]-center[1],p[0]-center[0]));samples=[(p[0],p[2])for p in base]+[center]+[((base[i][0]+base[(i+1)%4][0])/2,(base[i][2]+base[(i+1)%4][2])/2)for i in range(4)]
  check('entire anchor base supported by its island '+name,all(any((h:=height(x,z,row))is not None and abs(h-anchor[1])<.01 for row in ground)for x,z in samples))
 dx,dz=PRISON[0]-SHIP[0],PRISON[2]-SHIP[2];span=math.hypot(dx,dz)
 shaft=[v for t in report['source_triangles']if t.get('bridge')and t['texture']==0x50f for v in t['vertices']]
 along=[((v[0]-SHIP[0])*dx+(v[2]-SHIP[2])*dz)/span for v in shaft]
 check('rope cannot protrude behind either anchor',min(along)>-.0001 and max(along)<span+.0001,dict(min=min(along),max=max(along),span=span))
 for key,clearance in((rows()[0],12),(rows()[3],4)):
  x,y,z=key['xyz'];supports=[h for row in floors if(h:=height(x,z,row))is not None]
  check('key supported at requested clearance '+key['id'],any(abs(h+clearance-y)<.01 for h in supports),dict(xyz=key['xyz'],supports=supports,clearance=clearance))
