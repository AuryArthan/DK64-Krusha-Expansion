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
 check('approved baseline symbol map exact',hashlib.sha256(oldpath.read_bytes()).hexdigest()=='05bbf438a9b52521b1de4f92b28588c0019690ee34bf22b7557635f7efd5c4f7')
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
 check('horns another15 percent over approved1.10',abs(ENLARGEMENT-1.10*1.15)<1e-12)
 for h,tip in enumerate((368,306,243)):
  ys=[struct.unpack_from('>h',v,2)[0]for t in new[222+h*24:246+h*24]for v in t]
  check('horn planted root and new tip '+str(h),min(ys)==(211,190,135)[h]and max(ys)==tip,dict(root=min(ys),tip=max(ys)))
 # Verify all original exterior wall/floor records, except the physically
 # enlarged horns, remain exact. No world collision file or arch reshaping.
 def records(data):
  u=lambda p:struct.unpack_from('>I',data,p)[0];w,f=u(0x4c),u(0x50)
  return[data[w+4+i*22:w+4+(i+1)*22]for i in range(u(w))],[data[f+16+i*24:f+16+(i+1)*24]for i in range(u(f))]
 before,after=records(read_file(b,27,147)),records(read_file(r,27,147))
 for label,a,c in zip(('walls','floors'),before,after):
  delta=[(x,y)for x,y in zip(a,c)if x!=y]
  check('only horn collision changes '+label,len(a)==len(c)and all(min(struct.unpack_from('>9h',v)[1::3])>=135 for pair in delta for v in pair),dict(count=len(a),changed=len(delta)))
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
