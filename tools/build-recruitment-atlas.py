#!/usr/bin/env python3
"""Build a separate, move-only five-key study; never edit the ROM or old atlas."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rom', type=Path, default=ROOT / 'rom/dk64.z64')
    parser.add_argument('--runtime-plan', type=Path, help='Seed a separate atlas from implemented R10 positions')
    parser.add_argument('--draft-id', default='recruitment-keys-r10-v1', choices=('recruitment-keys-r10-v1','recruitment-keys-v15-v1'))
    parser.add_argument('--title', default='Implemented keys — placements for review')
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise SystemExit('Choose a new output directory; existing edits are preserved.')
    seed = json.loads((ROOT / 'docs/planning/krusha-adventure-expansion/placements/recruitment-keys-v1.json').read_text())
    if args.runtime_plan:
        runtime = json.loads(args.runtime_plan.read_text())
        assert {p['id'] for p in runtime['keys']} == {p['id'] for p in seed['pins']}
        by_id = {p['id']: p for p in runtime['keys']}
        for pin in seed['pins']:
            row = by_id[pin['id']]
            pin.update(xyz=row['xyz'], notes=row['notes'], status=row['status'])
        seed.update(implemented=True, draft_id=args.draft_id, title=args.title)
    draft_id = seed['draft_id']
    seed_name = draft_id + '.json'
    subprocess.run([sys.executable, str(ROOT / 'tools/build-map-atlas.py'),
                    '--rom', str(args.rom), '--out', str(out)], check=True)
    # The ordinary builder supplies the current campaign. Append its Isles pins
    # as immutable references, never as entries in the five-key editing list.
    line = (out / 'draft-seed.js').read_text().splitlines()[1]
    campaign = json.loads(line.split('=', 1)[1].rstrip(';'))
    map_path = out / 'data/034.js'
    data = json.loads(map_path.read_text().split('=', 1)[1].rstrip(';\n'))
    for pin in campaign['pins']:
        if pin['map'] == 34:
            data['points'].append(dict(pin, id='reference-' + pin['id'],
                name=pin['label'], owner='Krusha',
                kind='landmark' if pin['kind'] in ('note', 'switch') else pin['kind'],
                source='implemented-campaign-reference'))
    data['meta']['points'] = len(data['points'])
    map_path.write_text('window.ATLAS_MAP=' + json.dumps(data, separators=(',', ':')) + ';\n')
    (out / 'draft-seed.js').write_text('window.KRUSHA_DRAFTS=' + json.dumps([seed]) +
        ';\nwindow.KRUSHA_DRAFT=' + json.dumps(seed) + ';\n')
    (out / seed_name).write_text(json.dumps(seed, indent=2) + '\n')
    index = out / 'index.html'
    index.write_text(index.read_text().replace('Krusha’s collectibles', 'Recruitment keys').replace('assistant-draft-v1.json', seed_name).replace('Edit Krusha collectible', 'Edit recruitment key').replace('Room for one more.', 'Five keys. One new ally.').replace('Krusha • collectible placement atlas', 'Krusha • recruitment key atlas'))
    (out / 'keys.html').write_text('<!doctype html><meta charset="utf-8">'
        '<title>Krusha recruitment keys</title><meta http-equiv="refresh" '
        f'content="0;url=index.html?map=34&amp;style=A&amp;draft={draft_id}">'
        f'<a href="index.html?map=34&amp;style=A&amp;draft={draft_id}">'
        'Open five editable recruitment keys</a>')
    print(out / 'keys.html')


if __name__ == '__main__':
    main()
