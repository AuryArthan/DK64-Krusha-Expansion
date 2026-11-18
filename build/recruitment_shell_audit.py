"""Independent resource, relocation, native ridge and small-prison safety audits."""
import struct,zlib,math,hashlib
from pathlib import Path
from barrel_assets import read_file
from recruitment_placement_audit import faces,height

def symbols(p):return{v[1]:int(v[0],16)for v in(l.split()for l in p.read_text().splitlines())if len(v)>1}
def overlay(data,start):
 dec=zlib.decompressobj(-15);code=dec.decompress(data[start+10:]);off=len(data)-len(dec.unused_data)+8
 dec=zlib.decompressobj(-15);meta=dec.decompress(data[off+10:]);return code,meta

def relocations(old,new,olds,news):
 targets={};low={}
 for name,value in olds.items():
  if 0x805dae00<=value<0x805f4e00 and name in news:
   targets.setdefault(value,set()).add(news[name]);low.setdefault(value&65535,set()).add(news[name]&65535)
 # Three native M2 accesses address fields/interior records in the exact
 # unchanged0x410-byte collect-def array, rather than the array's first byte.
 for offset in(2,12,840):low.setdefault((olds['m2collectdefs']+offset)&65535,set()).add((news['m2collectdefs']+offset)&65535)
 counts={'resident jump':0,'resident low16':0,'resident pointer':0};bad=[]
 if len(old)!=len(new):return counts,['size']
 for pos in range(0,len(old),4):
  a,b=struct.unpack_from('>I',old,pos)[0],struct.unpack_from('>I',new,pos)[0]
  if a==b:continue
  op=a>>26;kind=None
  if b in targets.get(a,set()):kind='resident pointer'
  elif op in(2,3)and b>>26==op and (0x80000000|((b&0x3ffffff)<<2))in targets.get(0x80000000|((a&0x3ffffff)<<2),set()):kind='resident jump'
  elif op in(9,13,32,33,35,36,37,40,41,43,49,57)and b>>16==a>>16 and b&65535 in low.get(a&65535,set()):kind='resident low16'
  if kind:counts[kind]+=1
  else:bad.append(dict(offset=pos,old=hex(a),new=hex(b)))
 return counts,bad

def extra(r,b,clean,path,check,report,sym,baseline):
 root=Path(__file__).resolve().parents[1];oldpath=baseline.with_suffix('.sym')
 # Explicit --baseline is already digest-checked by the caller; its symbols
 # are the approved matching file, retained here for native relocation proof.
 olds=symbols(oldpath)
 check('approved baseline symbol map exact',hashlib.sha256(oldpath.read_bytes()).hexdigest()=='bee2e4425e435021355bf8a9278baa938d734b5436edfc6ddaafa9c22016eec7')
 def resident(data,address,size):return data[0x1fed020+address-0x805dae00:0x1fed020+address-0x805dae00+size]
 check('native collect-def data exactly retained',resident(b,olds['m2collectdefs'],0x410)==resident(r,sym['m2collectdefs'],0x410))
 from recompute_overlays import overlays
 for item in overlays:
  old,new=overlay(b,item['codeROMAddress']),overlay(r,item['codeROMAddress'])
  for i,label in enumerate(('code','data')):
   if item['name']in('global_asm','menu')and i==0:
    counts,bad=relocations(old[i],new[i],olds,sym);check('native overlay changes only resolved resident references '+item['name'],not bad,dict(counts=counts,unmatched=bad))
   else:check('unrelated native overlay exact '+item['name']+'/'+label,old[i]==new[i])
 old,new=faces(read_file(b,27,147)),faces(read_file(r,27,147))
 check('render topology unchanged330 triangles',len(old)==len(new)==330)
 check('shell tunnel and annulus rendering exact',old[:222]==new[:222])
 check('approved tether rendering exact',old[294:]==new[294:])
 check('horn colors and UVs unchanged',all(x[6:]==y[6:]for x,y in zip((v for t in old[222:294]for v in t),(v for t in new[222:294]for v in t))))
 from recruitment_spikes import ENLARGEMENT
 check('horns another5 percent over approved1.265',abs(ENLARGEMENT-1.10*1.15*1.05)<1e-12)
 for h,tip in enumerate((363,299,235)):
  ys=[struct.unpack_from('>h',v,2)[0]for t in new[222+h*24:246+h*24]for v in t]
  check('horn planted root and new tip '+str(h),min(ys)==(198,177,122)[h]and max(ys)==tip,dict(root=min(ys),tip=max(ys)))
 # Verify all original exterior wall/floor records, except the physically
 # enlarged horns, remain exact. No world collision file or arch reshaping.
 def records(data):
  u=lambda p:struct.unpack_from('>I',data,p)[0];w,f=u(0x4c),u(0x50)
  return[data[w+4+i*22:w+4+(i+1)*22]for i in range(u(w))],[data[f+16+i*24:f+16+(i+1)*24]for i in range(u(f))]
 before,after=records(read_file(b,27,147)),records(read_file(r,27,147))
 for label,a,c in zip(('walls','floors'),before,after):
  delta=[(x,y)for x,y in zip(a,c)if x!=y]
  check('only horn collision changes '+label,len(a)==len(c)and all(min(struct.unpack_from('>9h',v)[1::3])>=122 for pair in delta for v in pair),dict(count=len(a),changed=len(delta)))
 from fractions import Fraction as F
 p=(F(8359,3),F(2756,3),F(13133,6));q=(F(16655,6),F(760),F(2248));t=F(67,355)
 expected=[float(p[i]+t*(q[i]-p[i])+(12 if i==1 else 0))for i in range(3)]
 from recruitment_keys import rows
 actual=rows()[0]['xyz'];check('DK key exactly on the central native ridge',all(abs(a-c)<.00001 for a,c in zip(actual,expected)),dict(actual=actual,expected=expected,support=expected[1]-12))
 # Independent native collision extraction to verify that this edge is shared
 # by both nose sides. Atlas coordinates are rounded for visualization only.
 import importlib.util
 spec=importlib.util.spec_from_file_location('safety_native_atlas',root/'tools/build-map-atlas.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
 geo=read_file(clean,1,34);floors=a.collision(read_file(clean,3,34),math.prod(struct.unpack_from('>2H',geo,24)),True)
 p,q=[tuple(round(float(v),3)for v in point)for point in(p,q)]
 adjacent=[row for row in floors if p in[tuple(row[i:i+3])for i in(0,3,6)]and q in[tuple(row[i:i+3])for i in(0,3,6)]]
 check('two actual native triangles share the centered ridge',len(adjacent)==2,adjacent)
 check('unchanged native prison music row at boot',all(struct.unpack_from('>5h4B',meta,0x8074626e-0x80744460)==(3610,477,3302,-1,630,0,112,0,0)for meta in(overlay(b,0x113f0)[1],overlay(r,0x113f0)[1])))
 check('all private pickup cue and palette assets exact',all(read_file(r,27,i)==read_file(b,27,i)for i in(*range(187,192),229)))
 check('native doorway wall cache capacity retained',report['collision']['walls']==266 and report['collision']['floors']==61)

 # Independent emitted roof/ring intersections, after integer quantization.
 from recruitment_spikes import LOWERING
 check('horns lowered13local units /2.99world',LOWERING==13)
 roof=[sum([list(struct.unpack_from('>3h',v))for v in t],[])for t in new[:202]]
 clearances=[]
 for horn,root_y in enumerate((198,177,122)):
  ring={struct.unpack_from('>3h',v)for t in new[222+horn*24:246+horn*24]for v in t if struct.unpack_from('>h',v,2)[0]==root_y}
  check('exact8 planted root vertices '+str(horn),len(ring)==8)
  gaps=[]
  for x,y,z in ring:
   ys=[h for face in roof if(h:=height(x,z,face))is not None]
   check('enlarged root vertex intersects actual roof '+str(horn)+' '+str((x,z)),bool(ys)and max(ys)-y>=3,dict(root_y=y,roof_y=max(ys)if ys else None))
   gaps.append(max(ys)-y)
  clearances.append(dict(horn=horn,min_local=min(gaps),max_local=max(gaps)))
 report['horn_root_embedding']=clearances
 source=(root/'src/krusha_prison.c').read_text()
 check('steep-wall correction remains object-local and bounds checked', 'solidPrisonWalls((u8*)&objects[i])'in source and 'size>RECRUITMENT_COLLISION_WALLS*88'in source and 'wall[0x4B]!=2'in source and 'wall[0x4B]=1'in source)
 # Cross-section convex envelope at every native mesh Y breakpoint in the
 # guarded band. The private tunnel is intentionally an interior exception;
 # genuine native Mini entry remains exempt in C. All external body panels
 # form the original convex sphere; use emitted, quantized vertices here.
 from recruitment_assets import SCALE
 body=[[[c*SCALE for c in struct.unpack_from('>3h',v)]for v in t]for t in new[:212]]
 levels=sorted({-8.,20.,*[v[1]for face in body for v in face if -8<v[1]<20]})
 def hull(points):
  pts=sorted(set(points))
  def cross(a,b,c):return(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
  sides=[]
  for seq in(pts,list(reversed(pts))):
   row=[]
   for p in seq:
    while len(row)>1 and cross(row[-2],row[-1],p)<=0:row.pop()
    row.append(p)
   sides.append(row[:-1])
  return sides[0]+sides[1]
 clear=[]
 for level in levels:
  points=[]
  for face in body:
   for a,b in zip(face,face[1:]+face[:1]):
    if a[1]==level:points.append((a[0],a[2]))
    if min(a[1],b[1])<level<max(a[1],b[1]):
     f=(level-a[1])/(b[1]-a[1]);points.append((a[0]+f*(b[0]-a[0]),a[2]+f*(b[2]-a[2])))
  ring=hull(points);distances=[(a[0]*b[1]-a[1]*b[0])/math.hypot(b[0]-a[0],b[1]-a[1])for a,b in zip(ring,ring[1:]+ring[:1])]
  check('inner28-unit core remains behind outer shell at Y '+str(level),len(ring)>=3 and min(distances)>31,dict(inradius=min(distances),clearance=min(distances)-28))
  clear.append(min(distances)-28)
 check('inner guard retains native Mini entry exemption', '!(eligible && absolute(side)<3.5f && depth>-4 && depth<25)'in source)
 report['core_min_envelope_margin_world']=min(clear)
