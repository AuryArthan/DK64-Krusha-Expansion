"""Native menu controls for isolated recruitment QA. Does not modify game RAM."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def stop(d):
 if d.proc and d.proc.poll() is None:
  d.proc.stdin.write('{"quit":true}\n');d.proc.stdin.flush();d.proc.wait(timeout=25)
def ready(d,data,page):
 for _ in range(220):
  values=d.cmd(wait=0,read=[dict(address=a,type=t) for a,t in [(data+0x12,'u8'),(data,'f32'),(data+4,'f32'),(0x807467C4,'u8')]])[0]['memory']
  if values==[page,0.,0.,0]:return True
  d.cmd(wait=.2)
 raise RuntimeError(('Menu not ready',page,values))
def root(d):
 d.start();d.cmd(down=['f'])
 for _ in range(360):
  if d.status()['map']==80:break
  d.press('Return',.3,.3)
 d.cmd(up=['f'],wait=6);d.check('cold boot native menu',d.status()['map']==80)
 actor=next(a for a in d.scene('native-menu')['actors'] if a['type']==326);data=d.mem(int(actor['pointer'],16)+0x174)
 for _ in range(10):
  page=d.mem(data+0x12,'u8')
  if page==1:break
  d.press('Shift_L' if page==0 else 'Control_L',.3,.8)
 ready(d,data,1);return data
def select(d,data,index,page):
 ready(d,data,page)
 for _ in range(12):
  if d.mem(data+0x17,'u8')==index:return
  d.press('Right',.2,.5);ready(d,data,page)
 raise RuntimeError(('Menu selection failed',index))
def files(d,data):
 select(d,data,0,1);d.press('Shift_L',.3,.8);ready(d,data,2)
def preview(d,data,file):
 select(d,data,[0,1,3][file],2);d.press('Shift_L',.3,.8);ready(d,data,3)
 d.check('native preview selects file '+str(file),d.mem(0x807467C8,'u8')==file)
