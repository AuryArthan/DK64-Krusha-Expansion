"""Canonical M5 content identities and reviewed coordinates; no ROM mutations."""
from pathlib import Path
import json
from functools import lru_cache
ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'docs/planning/krusha-adventure-expansion/placements/campaign-m5-v1.json'
@lru_cache(None)
def plan():return json.loads(PLAN.read_text())
def worlds():return plan()['worlds']
def area(mid):return next((w for w in worlds() if w['map']==mid),None)
def kasplat(mid):return next((w for w in worlds() if w['kasplat_map']==mid),None)
def ground(mid=None):return [p for p in plan()['pins'] if p['kind']!='balloon' and (mid is None or p['map']==mid)]
def balloons(mid=None):return [p for p in plan()['pins'] if p['kind']=='balloon' and (mid is None or p['map']==mid)]
def maps():return sorted({p['map'] for p in plan()['pins']}|{w['map'] for w in worlds()})
def verify_ground_in_rom(path):
    """Reject QA against a ROM whose locations differ from the loaded plan."""
    import struct,hashlib
    from barrel_assets import read_file
    data=Path(path).read_bytes()
    for mid in {p['map'] for p in ground()}:
        raw=read_file(data,9,mid)
        rows={struct.unpack_from('>H',raw,4+i*48+42)[0]:raw[4+i*48:4+(i+1)*48] for i in range(struct.unpack_from('>I',raw)[0])}
        for pin in ground(mid):
            row=rows.get(pin['object_id'])
            assert row and struct.unpack_from('>H',row,40)[0]==pin['type'] and all(abs(x-y)<.002 for x,y in zip(struct.unpack_from('>3f',row),pin['xyz'])), f'ROM/placement-plan mismatch at {pin["label"]}; use its matching plan/build'
    return hashlib.sha256(PLAN.read_bytes()).hexdigest()
def aliases():
    # Keep all123 M4 resources and aliases stable. Japes retains its legacy Kasplat61/encounter87 aliases.
    result=[];index=123
    for mid in sorted({w['map'] for w in worlds()}|{w['kasplat_map'] for w in worlds()}):
        if mid!=7:result.append(dict(table=16,map=mid,index=index));index+=1
    return result
