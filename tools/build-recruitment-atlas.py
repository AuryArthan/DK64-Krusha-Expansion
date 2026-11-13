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
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise SystemExit('Choose a new output directory; existing edits are preserved.')
    seed = json.loads((ROOT / 'docs/planning/krusha-adventure-expansion/placements/recruitment-keys-v1.json').read_text())
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
    (out / 'recruitment-keys-v1.json').write_text(json.dumps(seed, indent=2) + '\n')
    index = out / 'index.html'
    index.write_text(index.read_text().replace('Krusha’s collectibles', 'Recruitment keys').replace('assistant-draft-v1.json', 'recruitment-keys-v1.json').replace('Edit Krusha collectible', 'Edit recruitment key').replace('Room for one more.', 'Five keys. One new ally.').replace('Krusha • collectible placement atlas', 'Krusha • recruitment key atlas'))
    (out / 'keys.html').write_text('<!doctype html><meta charset="utf-8">'
        '<title>Krusha recruitment keys</title><meta http-equiv="refresh" '
        'content="0;url=index.html?map=34&amp;style=A&amp;draft=recruitment-keys-v1">'
        '<a href="index.html?map=34&amp;style=A&amp;draft=recruitment-keys-v1">'
        'Open five editable recruitment keys</a>')
    print(out / 'keys.html')


if __name__ == '__main__':
    main()
