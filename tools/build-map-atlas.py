#!/usr/bin/env python3
"""Read the original USA ROM; build an offline map/placement study, never a ROM.

Collision block format follows DonkViewer (MIT, Ballaam, 2026), revision
57324aa2317a2baf814c67e8297f1b693ebd9c62, script/collision.js.
See tools/map-atlas/DonkViewer-LICENSE.txt. Other layouts use this repo's codecs.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import math
import shutil
import struct
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'build'))
from map_names import maps
from model2_names import model2_names
from actor_names import actor_names
from character_spawner_names import character_spawner_names
from native_pickup_adjustments import removed_ids

BASE = 0x101C50
KONGS = ['DK', 'Diddy', 'Lanky', 'Tiny', 'Chunky']
WORLDS = ['Jungle Japes', 'Angry Aztec', 'Frantic Factory', 'Gloomy Galleon',
          'Fungi Forest', 'Crystal Caves', 'Creepy Castle', 'DK Isles', 'Hideout Helm']
UI_FILES = ('index.html', 'atlas.js', 'planner.js', 'atlas.css', 'DonkViewer-LICENSE.txt', 'assistant-draft.html')


def unpack(fmt, data, offset=0):
    return struct.unpack_from('>' + fmt, data, offset)


class ROM:
    def __init__(self, path):
        self.data = path.read_bytes()
        self.sha1 = hashlib.sha1(self.data).hexdigest()
        if self.sha1 != 'cf806ff2603640a748fca5026ded28802f1f4a50':
            raise ValueError('Atlas requires the unchanged USA big-endian source ROM.')

    def file(self, table, index, seen=()):
        assert (table, index) not in seen, 'Pointer alias cycle'
        count = unpack('I', self.data, BASE + (32 + table) * 4)[0]
        assert 0 <= index < count, (table, index, count)
        pointer = BASE + unpack('I', self.data, BASE + table * 4)[0]
        raw, end = unpack('II', self.data, pointer + index * 4)
        start = BASE + (raw & 0x7FFFFFFF)
        end = BASE + (end & 0x7FFFFFFF)
        assert 0 <= start <= end <= len(self.data), (table, index)
        if raw & 0x80000000:
            target = unpack('H', self.data, start)[0]
            return self.file(table, target, seen + ((table, index),))
        data = self.data[start:end]
        return zlib.decompress(data, 15 + 32) if data[:2] == b'\x1f\x8b' else data


def collision(data, count, floor):
    """Grid cells repeat triangles; deduplicate by native coordinates/properties."""
    if not data:
        return []
    start = 8
    unique = {}
    for _ in range(count):
        assert start <= len(data), (start, len(data))
        end = unpack('I', data, start - 4)[0]
        assert start <= end <= len(data) and (end - start) % 24 == 0
        for pos in range(start, end, 24):
            values = unpack('9h', data, pos)
            if floor:
                points = [[values[j], values[j + 3], values[j + 6]] for j in range(3)]
                points = [[round(v / 6, 3) for v in p] for p in points]
                prop = unpack('H', data, pos + 18)[0]
            else:
                points = [list(values[j:j + 3]) for j in (0, 3, 6)]
                prop = unpack('H', data, pos + 22)[0]
            key = (tuple(sorted(tuple(p) for p in points)), prop)
            unique[key] = [*points[0], *points[1], *points[2], prop]
        start = end + 4
    assert start - 4 == len(data), ('Unparsed collision bytes', start, len(data))
    return list(unique.values())


def owner(name):
    return next((k for k in KONGS if '(' + k + ')' in name or '(' + k + ',' in name), None)


def classify(name, source):
    if name.startswith('CB Single ('): return 'single', 1
    if name.startswith('CB Bunch ('): return 'bunch', 5
    if name.startswith('Balloon (') and 'Unused' not in name: return 'balloon', 10
    if name.startswith('Banana Coin ('): return 'coin', 1
    if name == 'Golden Banana': return 'gb', 1
    if name.startswith('Blueprint (') or name.startswith('Kasplat ('): return 'blueprint', 1
    if name == 'Banana Medal': return 'medal', 1
    if name == 'Banana Fairy': return 'fairy', 1
    if name in ('Rainbow Coin Patch', 'Rainbow Coin'): return 'rainbow', 1
    if name in ('Battle Crown Pad', 'Battle Crown', 'Crown'): return 'crown', 1
    if name in ('Boss Key', 'Nintendo Coin', 'Rareware Coin', 'Bean', 'Pearl'): return 'quest', 1
    if name == 'Bonus Barrel': return 'bonus', 1
    if name in ('Crystal Coconut', 'Ammo Crate', 'Homing Ammo Crate', 'Orange',
                'Watermelon Slice', 'Film', 'Headphones'): return 'supply', 1
    if name.startswith(('Tag Barrel', 'Bananaport', 'Warp ', 'Cranky', 'Funky', 'Candy', "Snide", "Troff'n'Scoff Portal")):
        return 'landmark', 0
    return None, 0


def point_record(map_id, source, index, kind, name, xyz, object_id=None, quantity=1):
    assert all(math.isfinite(v) for v in xyz)
    return dict(id=f'{map_id:03d}-{source}-{index:03d}', source=source, index=index,
                kind=kind, name=name, owner=owner(name), xyz=[round(v, 3) for v in xyz],
                object_id=object_id, quantity=quantity)


def objects(rom, map_id, reward_owners):
    out = []
    omitted = removed_ids(map_id)
    b = rom.file(9, map_id)
    if b:
        n = unpack('I', b)[0]
        for i in range(n):
            p = 4 + i * 48
            xyz = unpack('3f', b, p)
            typ, obj = unpack('HH', b, p + 40)
            if obj in omitted:
                continue
            name = model2_names[typ] if typ < len(model2_names) else f'Model2 {typ}'
            kind, quantity = classify(name, 'model2')
            if kind:
                rec = point_record(map_id, 'model2', i, kind, name, xyz, obj, quantity)
                if (map_id, obj) in reward_owners and kind in ('gb', 'medal'):
                    rec['owner'], rec['flag'] = reward_owners[(map_id, obj)]
                out.append(rec)
        p = 4 + n * 48
        conveyors = unpack('I', b, p)[0]
        p += 4 + conveyors * 36
        n = unpack('I', b, p)[0]
        p += 4
        for i in range(n):
            q = p + i * 56
            typ = unpack('H', b, q + 50)[0] + 16
            name = actor_names[typ] if typ < len(actor_names) else f'Actor {typ}'
            kind, quantity = classify(name, 'actor')
            if kind:
                rec = point_record(map_id, 'actor', i, kind, name, unpack('3f', b, q),
                                   unpack('H', b, q + 52)[0], quantity)
                if kind in ('bonus', 'balloon'):
                    rec['position_note'] = 'Initial actor anchor; reward/path may differ.'
                out.append(rec)
        assert p + n * 56 == len(b), ('Setup trailing data', map_id)
    b = rom.file(16, map_id)
    if b:
        p = 2
        for _ in range(unpack('H', b)[0]):
            n = unpack('H', b, p)[0]; p += 2 + n * 6
            n = unpack('H', b, p)[0]; p += 2 + n * 10 + 4
        n = unpack('H', b, p)[0]; p += 2
        for i in range(n):
            typ = b[p]
            name = character_spawner_names[typ] if typ < len(character_spawner_names) else f'Spawner {typ}'
            kind, quantity = classify(name, 'enemy')
            if kind:
                out.append(point_record(map_id, 'enemy', i, kind, name, unpack('3h', b, p + 4),
                                        b[p + 19], quantity))
            p += 22 + 2 * b[p + 17]
        assert p == len(b), ('Spawner trailing data', map_id)
    b = rom.file(18, map_id)
    if b:
        n = unpack('H', b)[0]
        assert 2 + n * 56 == len(b)
        for i in range(n):
            p = 2 + i * 56
            typ, dest, exit_id = unpack('3H', b, p + 16)
            if typ in (9, 12, 13, 15, 16, 17, 20) and dest < 216:
                rec = point_record(map_id, 'exit', i, 'exit', 'To ' + maps[dest], unpack('3h', b, p))
                rec.update(destination=dest, destination_exit=exit_id, trigger_type=typ)
                if typ in (17, 20):
                    rec['position_note'] = 'Context-dependent parent/boss destination; raw trigger value.'
                out.append(rec)
    return out


def group(map_id):
    name = maps[map_id]
    if 'Lobby' in name or map_id in (34, 97, 171, 176, 189, 195):
        return 'DK Isles'
    for w in WORLDS:
        if name == w or name.startswith(w + ':'):
            return w
    if map_id == 17:
        return 'Hideout Helm'
    if map_id in (1, 5, 15, 25, 42):
        return 'Shared interiors'
    return 'Other maps / bonus games'


def write_placement_draft(out):
    campaign = ROOT / 'data/placements/campaign.json'
    data=json.loads(campaign.read_text())
    draft=dict(format='krusha-atlas-notes-v2',source_sha1=data['source_sha1'],
               draft_id=data['draft_id'],title=data['title'],scope='implemented-campaign',
               banana_target=50,coin_target=sum(p['kind'] == 'coin' for p in data['pins']),reward_target=3,pins=list(data['pins']))
    for w in data['worlds']:
        for name,kind,key,notes in [
            ('PAD','switch','pad','Shout here to summon the rare Klump. One paid shout; eight bazooka hits.'),
            ('KLUMP','gb','boss','Rare Klump drops one GB at its death location. About 1.47 times native size, eight hits, triple grenades.'),
            ('CAGE','gb','cage','Hit the compact cage with a bazooka projectile. Lime projectile hint on its roof.'),
            ('BP','blueprint','kasplat','Gray Kasplat: one blueprint, one GB from Snide. Collected-blueprint hair becomes black.')]:
            mid=w['kasplat_map'] if key=='kasplat' else w['map']
            draft['pins'].append(dict(id='m5-'+w['code']+'-'+name,map=mid,map_name=w['name'],
                label=w['code']+'-'+name,kind=kind,quantity=1,xyz=w[key],notes=w.get('placement_notes',{}).get(key,notes),status='campaign-draft'))
    (out / 'campaign.json').write_text(json.dumps(draft, indent=2) + '\n')
    seed = json.dumps(draft, separators=(',', ':'))
    (out / 'draft-seed.js').write_text('window.KRUSHA_DRAFTS=[' + seed + '];\nwindow.KRUSHA_DRAFT=' + seed + ';\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rom', type=Path, default=ROOT / 'rom/dk64.z64')
    ap.add_argument('--out', type=Path, default=ROOT / 'runtime/map-atlas/atlas')
    ap.add_argument('--refresh-ui', action='store_true',
                    help='Back up and refresh UI, seeds and implemented native pickup omissions; keep geometry and exported plans.')
    args = ap.parse_args()
    out = args.out.resolve()
    if args.refresh_ui:
        metadata = json.loads((out / 'coverage.json').read_text())
        if metadata.get('source_sha1') != 'cf806ff2603640a748fca5026ded28802f1f4a50' or metadata.get('map_count') != 216:
            raise SystemExit('Refresh requires an existing matching USA atlas.')
        backup = out / 'ui-history' / str(time.time_ns())
        backup.mkdir(parents=True)
        for name in UI_FILES + ('draft-seed.js', 'campaign.json'):
            if (out / name).exists():
                shutil.copyfile(out / name, backup / name)
        for name in UI_FILES:
            shutil.copyfile(ROOT / 'tools/map-atlas' / name, out / name)
        # Keep original collision/other reference points; omit only reviewed
        # native pickups that the ROM builder now removes. Preserve originals
        # beside the UI backup before touching generated reference metadata.
        for record in metadata['maps']:
            omitted = removed_ids(record['id'])
            if not omitted:
                continue
            path = out / 'data' / f'{record["id"]:03d}.js'
            text = path.read_text()
            detail = json.loads(text.split('=', 1)[1].strip().rstrip(';'))
            points = [p for p in detail['points'] if not
                      (p['source'] == 'model2' and p.get('object_id') in omitted)]
            if points == detail['points']:
                continue
            for original in (path, out / 'coverage.json', out / 'catalog.js'):
                saved = backup / original.name
                if not saved.exists():
                    shutil.copyfile(original, saved)
            record.update(points=len(points), counts=dict(collections.Counter(p['kind'] for p in points)))
            detail.update(meta=record, points=points)
            path.write_text('window.ATLAS_MAP=' + json.dumps(detail, separators=(',', ':')) + ';\n')
        (out / 'coverage.json').write_text(json.dumps(metadata, indent=2) + '\n')
        (out / 'catalog.js').write_text('window.ATLAS_CATALOG=' + json.dumps(metadata, separators=(',', ':')) + ';\n')
        write_placement_draft(out)
        print(f'Updated interface; previous UI preserved in {backup}')
        print(out / 'index.html')
        return
    rom = ROM(args.rom)
    # Do not overwrite an atlas that may contain browser/downloaded planning notes.
    if out.exists():
        raise SystemExit('Output already exists. Choose a new --out directory to preserve annotations.')
    (out / 'data').mkdir(parents=True)
    data = zlib.decompress(rom.data[0xC29D4:0xCBE70], 15 + 32)
    rewards = {}
    for p in range(0x80755A20 - 0x80744460, 0x80755DA8 - 0x80744460, 8):
        map_id, obj, flag, kong = data[p], unpack('H', data, p + 2)[0], unpack('H', data, p + 4)[0], data[p + 6]
        assert 2 <= kong <= 6
        rewards[(map_id, obj)] = (KONGS[kong - 2], flag)
    catalog = []
    coverage = {}
    for map_id in range(216):
        geo = rom.file(1, map_id)
        floors = walls = []
        if len(geo) >= 32:
            wall_count = math.prod(unpack('2H', geo, 16))
            floor_count = math.prod(unpack('2H', geo, 24))
            floors = collision(rom.file(3, map_id), floor_count, True)
            walls = collision(rom.file(2, map_id), wall_count, False)
        points = objects(rom, map_id, rewards)
        counts = dict(collections.Counter(p['kind'] for p in points))
        record = dict(id=map_id, name=maps[map_id], group=group(map_id), floors=len(floors),
                      walls=len(walls), points=len(points), counts=counts)
        catalog.append(record)
        detail = dict(meta=record, floors=floors, walls=walls, points=points)
        (out / 'data' / f'{map_id:03d}.js').write_text('window.ATLAS_MAP=' + json.dumps(detail, separators=(',', ':')) + ';\n')
        coverage[str(map_id)] = record
    metadata = dict(source_sha1=rom.sha1, source_sha256=hashlib.sha256(rom.data).hexdigest(),
                    map_count=len(catalog), maps=catalog,
                    coverage='Placed objects and enemy spawners; scripted rewards/drops are not a complete inventory.')
    (out / 'catalog.js').write_text('window.ATLAS_CATALOG=' + json.dumps(metadata, separators=(',', ':')) + ';\n')
    (out / 'coverage.json').write_text(json.dumps(metadata, indent=2) + '\n')
    for name in UI_FILES:
        shutil.copyfile(ROOT / 'tools/map-atlas' / name, out / name)
    write_placement_draft(out)
    print(f'Built {len(catalog)} maps, {sum(m["points"] for m in catalog):,} reference markers.')
    print(out / 'index.html')


if __name__ == '__main__':
    main()
