#!/usr/bin/env python3
"""R14 genuinely erased native EEPROM, native opening story and locked roster.
No native progress/moves/rescues, quest bits, identity, action or code fixtures.
The ordinary Treehouse doorway position is a logged navigation shortcut.
This proves the START of a natural chain, not all five original-Kong rescues.
"""
from pathlib import Path
import hashlib
import json
import os
import struct
import tempfile
import traceback
import types

ROOT = Path(__file__).resolve().parents[1]
rom = Path(os.environ.get('DK64_TEST_ROM', ROOT / 'rom/dk64-krusha-dev.z64')).resolve()
parent = ROOT / 'runtime/tests'
parent.mkdir(parents=True, exist_ok=True)
run = Path(tempfile.mkdtemp(prefix='fresh-adventure-', dir=parent))
print(f'Fresh Adventure profile: {run}', flush=True)
os.environ.update(DK64_TEST_ROM=str(rom), DK64_RUNTIME=str(run))
(run / 'saves').mkdir()
empty = bytes([255]) * 2048
rom_bytes = rom.read_bytes()
name = hashlib.md5(rom_bytes).hexdigest()[:8].upper()
(run / 'saves' / f'Donkey Kong 64 (local build)-{name}.eep').write_bytes(empty)
(run / 'config').mkdir()
config = (ROOT / 'tools/config/mupen64plus.cfg').read_text()
(run / 'config/mupen64plus.cfg').write_text(config + '\n[Core]\nVersion = 1.010000\nGbCameraVideoCaptureBackend1 = "dummy"\n')

import driver as d
import menus as ui
import options as opt

symbols = {row[1]:int(row[0], 16) for line in rom.with_suffix('.sym').read_text().splitlines()
           if len(row := line.split()) >= 2}
offset = 0x1FED020 + symbols['krushaenabled'] - 0x805DAE00
lui, jr, lw = struct.unpack_from('>III', rom_bytes, offset)
assert lui >> 16 == 0x3C02 and jr == 0x03E00008 and lw >> 16 == 0x8C42
enabled_address = ((lui & 65535) << 16) + struct.unpack('>h', struct.pack('>H', lw & 65535))[0]
m = types.SimpleNamespace(symbols=symbols, ENABLED=enabled_address)
d.REPORT_NAME = 'fresh-adventure.json'
d.results.update(fixtures=__doc__, initial_eeprom_sha256=hashlib.sha256(empty).hexdigest())
def reads(req):return d.cmd(read=[dict(address=a,type=t)for a,t in req],wait=0)[0]['memory']
def private():
 mapping=reads([(0x807EDEA8+i,'u8')for i in range(4)]);file=d.mem(0x807467C8,'u8');base=mapping.index(file)*3936+2500;words=reads([(0x807ECEA8+j*4,'u32')for j in range(base//32,(base+511)//32+1)])
 return[(words[(base+i)//32-base//32]>>((base+i)%32))&1 for i in range(512)]
try:
 data=ui.root(d)
 d.check('genuinely erased EEPROM boots native menu',d.status()['map']==80)
 d.check('fresh defaults Krusha ON TagOFF WideOFF MirrorOFF',[opt.value(d,i,m.ENABLED)for i in(4,1,0,5)]==[1,0,0,0])
 # Select ordinary Tag ON through the real options menu for locked roster probes.
 ui.select(d,data,4,1);d.press('Shift_L',.3,.8);ui.ready(d,data,9);opt.set_value(d,data,1,1,m.symbols,m.ENABLED,lambda p:ui.ready(d,data,p));d.press('Control_L',.3,.8);ui.ready(d,data,1)
 ui.files(d,data);ui.preview(d,data,0);d.press('Shift_L',.3,1);d.cmd(down=['f'])
 for i in range(800):
  st=d.status()
  if st['map']in(171,176) and st.get('player',{}).get('state')==12 and d.mem(0x807444EC,'u8')==0:break
  if i%50==0:print('NATIVE_STORY',i,st,flush=True)
  d.press('Return',.15,.4)
 else:raise RuntimeError('Opening story did not give control')
 d.cmd(up=['f'],wait=1)
 if d.mem(0x807FBB63,'u8')&2:d.press('Return',.15,.5)
 if d.status()['map']==171:d.place(d.zone_position(171,176),0,wait=4)
 for i in range(180):
  st=d.status()
  if st['map']==176 and st['player']['state']==12 and not d.mem(0x807444EC,'u8') and not d.mem(0x807463B8,'u8'):break
  d.press('Shift_L',.15,.3)
 d.check('native story reaches Training Grounds with DK control',d.status()['map']==176 and d.status()['character']==0 and d.status()['player']['state']==12,d.status())
 d.check('fresh quest and personal Krusha moves remain unowned',private()[496:510]==[0]*14,private()[496:510])
 mapping=reads([(0x807EDEA8+i,'u8')for i in range(4)]);active_flags=0x807ECEA8+mapping.index(d.mem(0x807467C8,'u8'))*492
 d.check('unrescued original Kongs have no native rescue flags',not any(d.mem(active_flags+flag//8,'u8')&(1<<(flag%8))for flag in(6,70,66,117)))
 seen=[]
 for key in('a','d','a','d'):
  d.press(key,.2,.6);seen.append(d.status()['character'])
 d.check('normal fresh D-pad roster contains only DK',seen==[0,0,0,0],seen)
 d.check('fresh file has no crystals or free Krusha abilities',d.status()['inventory'][3]==0)
 d.cmd(shot='r14-genuine-fresh-training');d.checkpoint(0,'r14-genuine-fresh-training')
 d.check('fresh native engine and SI healthy',d.mem(0x800100F4)==0 and d.mem(0x807FF01C,'u8')==0)
 d.results['complete']=True;d.results['scope']='Fresh file through the Training Grounds'
except Exception as e:
 d.results.update(error=repr(e),traceback=traceback.format_exc());print(traceback.format_exc(),flush=True)
 try:d.cmd(shot='r14-fresh-failure')
 except Exception:pass
finally:
 ui.stop(d);(run/'logs'/d.REPORT_NAME).write_text(json.dumps(d.results,indent=2)+'\n')
 if not d.results.get('complete'):raise SystemExit(1)
