#!/usr/bin/env python3
"""Validate a reviewed five-key atlas export into a NEW runtime-plan file.

Does not build/promote a ROM or overwrite the maintained plan. Review the JSON
and route/ground checks before copying its content into the maintained manifest.
Protected identities and scale come from the existing runtime manifest.
"""
from pathlib import Path
import argparse,json,math
ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'data/placements/recruitment-keys.json'
SOURCE='cf806ff2603640a748fca5026ded28802f1f4a50'
OWNERS=('DK','Diddy','Lanky','Tiny','Chunky')

def convert(data,baseline):
 if data.get('format')!='krusha-atlas-notes-v2' or data.get('source_sha1')!=SOURCE:raise ValueError('Expected an original-USA v2 atlas export')
 if data.get('draft_id')not in('recruitment-keys-v1','recruitment-keys-r10-v1','recruitment-keys-v15-v1','recruitment-keys-v15-refined-v1','recruitment-keys-v15-pipes-v1','recruitment-keys-v15-ridge-v1'):raise ValueError('Expected a recruitment-key draft, not campaign placements')
 if data.get('mode','move-only')!='move-only':raise ValueError('Expected move-only editing')
 pins=data.get('pins');canonical={p['id']:p for p in baseline['keys']}
 if not isinstance(pins,list)or len(pins)!=5 or len({p.get('id')for p in pins})!=5 or {p.get('id')for p in pins}!=set(canonical):raise ValueError('Keep exactly the five stable key IDs')
 out=json.loads(json.dumps(baseline));by_id={p['id']:p for p in out['keys']}
 for p in pins:
  c=by_id[p['id']]
  if p.get('map')!=34 or p.get('kind')!='key' or p.get('quantity')!=1 or p.get('owner')!=OWNERS[c['owner']]:raise ValueError('Cannot change a key owner, map, kind or quantity')
  xyz=p.get('xyz')
  if not isinstance(xyz,list)or len(xyz)!=3 or any(isinstance(x,bool)or not isinstance(x,(float,int))or not math.isfinite(x)for x in xyz):raise ValueError('Expected three finite coordinates')
  if not(0<=xyz[0]<=7000 and -500<=xyz[1]<=5000 and 0<=xyz[2]<=7000):raise ValueError('Coordinates outside DK Isles study bounds')
  notes=p.get('notes','')
  if not isinstance(notes,str)or len(notes)>16000:raise ValueError('Invalid challenge/access notes')
  c.update(xyz=xyz,notes=notes,status='user-reviewed; ground and route validation pending')
 out.update(source='Explicit reviewed atlas export',placement_status='user-reviewed; ground and route validation pending')
 return out

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 out=convert(json.loads(a.input.read_text()),json.loads(PLAN.read_text()));a.out.parent.mkdir(parents=True,exist_ok=True)
 with a.out.open('x')as f:f.write(json.dumps(out,indent=2)+'\n')
 print(a.out)
if __name__=='__main__':main()
