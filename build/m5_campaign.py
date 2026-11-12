"""Campaign setup/spawner/script extension. Preserve original records verbatim."""
from pathlib import Path
import struct,zlib
from campaign_data import ROOT,worlds,ground,balloons,area,kasplat,aliases
from barrel_assets import read_file

def prepare(rom_path):
    rom=Path(rom_path).read_bytes();pins=ground()+balloons();slots=[p['pickup_slot'] for p in pins]
    # Removed Isles coins keep their old EEPROM bits reserved. Never compact
    # or reassign identities when retiring a placed object.
    from campaign_data import plan
    retired=plan().get('retired_pickup_slots',[])
    assert len(slots)==len(set(slots))==203 and max(slots)<384
    assert retired==list(range(322,330))+[340] and not set(slots)&set(retired)
    for w in worlds():
        ps=[p for p in pins if p['world']==w['world']]
        assert sum(p['kind']=='coin' for p in ps)==(9 if w['world']<7 else 0)
        assert sum({'single':1,'bunch':5,'balloon':10,'coin':0}[p['kind']] for p in ps)==(50 if w['world']<7 else 0)
    text='/* Generated campaign identities: original save/actor IDs are never reused. */\n'
    text+='static const M5Area m5Areas[8] = {\n'
    f=lambda xyz:'{'+','.join(f'{v:.3f}f' for v in xyz)+'}'
    for w in worlds():text+='    {%d,%d,%d,%d,%d,%d,%s,%s,%s},\n'%(w['map'],w['gate_id'],w['pad_id'],w['reward_id'],w['world'],w['trigger'],f(w['pad']),f(w['boss']),f(w['cage']))
    text+='};\nstatic const M5Kasplat m5Kasplats[8] = {\n'+''.join('    {%d,%d,%d},\n'%(w['kasplat_map'],w['world'],w['kasplat_id']) for w in worlds())+'};\n'
    text+='static const struct {u16 table,map,index;} m5Files[] = {\n'+''.join('    {%d,%d,%d},\n'%(v['table'],v['map'],v['index']) for v in aliases())+'};\n'
    (ROOT/'include/m5_campaign.generated.h').write_text(text)

def spawners(rom,mid):
    from m4_encounter import parse_spawners
    data=read_file(rom,16,mid);end,ids,records=parse_spawners(data);newfences=bytearray();newrecords=[]
    original=(ROOT/'rom/dk64.z64').read_bytes()
    def add(w,typ,ident,xyz,points,size=None):
        nonlocal newfences
        assert ident not in {v[19] for v in records+newrecords}
        template=None
        for source in range(216):
            raw=read_file(original,16,source)
            if not raw:continue
            template=next((v for v in parse_spawners(raw)[2] if v[0]==typ and len(v)==22 and (typ!=9 or v[15]==50)),None)
            if template is not None:break
        assert template is not None
        fid=max(ids+[0])+len(newrecords)+1;assert fid<256
        newfences+=struct.pack('>H',len(points))+b''.join(struct.pack('>3h',*(round(x) for x in p)) for p in points)+struct.pack('>3H',0,fid,1)
        rec=bytearray(template);struct.pack_into('>3h',rec,4,*(round(v) for v in xyz));rec[14]=fid;rec[19]=ident
        if size is not None:rec[15]=size;rec[18]=0;rec[20]=0
        newrecords.append(rec)
    w=kasplat(mid)
    if w:
        x,y,z=w['kasplat'];points=[(x+dx,y,z+dz) for dx,dz in [(-70,-70),(70,-70),(70,70),(-70,70),(-70,-70)]]
        add(w,61,w['kasplat_id'],w['kasplat'],points)
    w=area(mid)
    if w:add(w,9,w['trigger'],w['boss'],w['fence'],80)
    return struct.pack('>H',len(ids)+len(newrecords))+data[2:end]+newfences+struct.pack('>H',len(records)+len(newrecords))+b''.join(records+newrecords)

def payloads(rom):
    from m4_rewards import patched_scripts
    return [spawners(rom,a['map']) if a['table']==16 else patched_scripts(read_file(rom,10,a['map']),a['map']) for a in aliases()]

def patch_scripts(filename,mid):
    from m4_rewards import patched_scripts
    p=Path(filename);p.write_bytes(patched_scripts(p.read_bytes(),mid))

def patch_code(fh,symbols):
    address=0x80712548;fh.seek(address-0x805FB300)
    assert fh.read(8)==bytes.fromhex('27bdffe8afbf0014'),'Helm minute reader differs from verified USA'
    fh.seek(address-0x805FB300);fh.write((0x08000000|(int(symbols['m5helmminutes'],16)&0xFFFFFFF)>>2).to_bytes(4,'big')+bytes(4))
