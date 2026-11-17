"""R11 independent colored padlock displays. No native story/collision scripts."""
from pathlib import Path
import struct
from barrel_assets import read_file
ROOT=Path(__file__).resolve().parents[1]
MODEL=192
TEXTURE=202
MODEL_TOKEN=0xF0
TEXTURE_TOKEN=7850
KEY_MODEL=212
KEY_MODEL_TOKEN=245
from recruitment_cage import MODEL as CAGE_MODEL, MODEL_TOKEN as CAGE_MODEL_TOKEN, COUNT

def prepare(path):
 r=Path(path).read_bytes()
 from recruitment_barrel import MODEL_TOKEN as previous_model_token
 assert MODEL_TOKEN==previous_model_token+1
 assert MODEL_TOKEN-1>=struct.unpack_from('>I',r,0x101C50+(32+5)*4)[0]
 assert TEXTURE==MODEL+10 and KEY_MODEL==TEXTURE+10 and CAGE_MODEL==KEY_MODEL+10 and COUNT==CAGE_MODEL+2
 for i in range(TEXTURE_TOKEN,TEXTURE_TOKEN+10):assert not read_file(r,25,i)
 assert KEY_MODEL_TOKEN==MODEL_TOKEN+5
 assert CAGE_MODEL_TOKEN==KEY_MODEL_TOKEN+5 and CAGE_MODEL_TOKEN<256
 (ROOT/'include/recruitment_scene.generated.h').write_text('/* Generated R11/R12 private display resources. */\n'+''.join(f'#define {k} {v}\n'for k,v in dict(RECRUITMENT_LOCK_MODEL=MODEL,RECRUITMENT_LOCK_TEXTURE=TEXTURE,RECRUITMENT_LOCK_MODEL_TOKEN=MODEL_TOKEN,RECRUITMENT_LOCK_TEXTURE_TOKEN=TEXTURE_TOKEN,RECRUITMENT_TURN_KEY_MODEL=KEY_MODEL,RECRUITMENT_TURN_KEY_MODEL_TOKEN=KEY_MODEL_TOKEN,RECRUITMENT_CAGE_MODEL=CAGE_MODEL,RECRUITMENT_CAGE_MODEL_TOKEN=CAGE_MODEL_TOKEN,RECRUITMENT_SCENE_ASSET_COUNT=COUNT).items()))

def without_inserted_key(source):
    """Keep native lock/shackle; omit only separate inserted-key bone3."""
    out=bytearray(source);base=struct.unpack_from('>I',out)[0]
    end=struct.unpack_from('>I',out,4)[0]-base+40
    start=struct.unpack_from('>I',out,end)[0]-base+40
    bone=None;removed=0
    for pos in range(start,end,8):
        a,b=struct.unpack_from('>II',out,pos)
        if a>>24==0xDA:bone=(b&0xFFFFFF)//64
        if a>>24 in (5,6,7) and bone==3:
            struct.pack_into('>II',out,pos,0,0);removed+=1
    assert removed>0
    return bytes(out)

def payloads(r):
 from mirror_assets import flip
 from recruitment_keys import COLORS
 from recruitment_materials import metal_rgb
 source=without_inserted_key(read_file(r,5,0xCC));result=[]
 assert struct.unpack_from('>II',source,0xD88)==(0xFD100000,0xBAB)
 for owner in range(5):
  b=bytearray(source)
  for offset,token in((0xD88,TEXTURE_TOKEN+owner*2),(0x1090,TEXTURE_TOKEN+owner*2),(0x11E0,TEXTURE_TOKEN+owner*2+1)):
   assert b[offset]==0xFD;struct.pack_into('>I',b,offset+4,token)
  result.extend([bytes(b),flip(bytes(b),5)[0]])
 for color in COLORS:
  for index,size in((0xBAB,2048),(0x130F,2744)):
   texture=read_file(r,25,index);assert len(texture)==size;out=bytearray()
   for(v,)in struct.iter_unpack('>H',texture):
    rgb=(v>>11&31,v>>6&31,v>>1&31)
    c=metal_rgb(rgb,color);out+=struct.pack('>H',c[0]<<11|c[1]<<6|c[2]<<1|v&1)
   result.append(bytes(out))
 assert len(result)==20
 # Independent key components, keeping the original skeleton/bind pose.
 # Reuse the existing owner-colored textures. No new texture aliases and
 # no native boss-key actor/controller or global story side effects.
 for owner in range(5):
  b=bytearray(read_file(r,5,0xCC));base=struct.unpack_from('>I',b)[0]
  end=struct.unpack_from('>I',b,4)[0]-base+40
  start=struct.unpack_from('>I',b,end)[0]-base+40
  bone=None;kept=0
  for pos in range(start,end,8):
   a,w=struct.unpack_from('>II',b,pos)
   if a>>24==0xDA:bone=(w&0xFFFFFF)//64
   if a>>24 in(5,6,7):
    if bone!=3:struct.pack_into('>II',b,pos,0,0)
    else:kept+=1
  assert kept>0
  for offset,token in((0xD88,TEXTURE_TOKEN+owner*2),(0x1090,TEXTURE_TOKEN+owner*2),(0x11E0,TEXTURE_TOKEN+owner*2+1)):
   assert b[offset]==0xFD;struct.pack_into('>I',b,offset+4,token)
  from recruitment_key_bit import complete_key
  b=complete_key(bytes(b))
  result.extend([b,flip(b,5)[0]])
 assert len(result)==CAGE_MODEL-MODEL
 from recruitment_cage import extended_cage
 cage=extended_cage(read_file(r,5,0xC3))
 result.extend([cage,flip(cage,5)[0]])
 assert len(result)==COUNT-MODEL
 return result
