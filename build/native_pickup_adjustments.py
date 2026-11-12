"""Reviewed native pickup removals; keep every retained record/ID and tail exact."""
from pathlib import Path
import json
import struct

PLAN = Path(__file__).resolve().parents[1] / 'docs/planning/krusha-adventure-expansion/placements/native-pickup-adjustments.json'

def removals(mid):
    return [p for p in json.loads(PLAN.read_text())['remove_model2'] if p['map'] == mid]

def removed_ids(mid):
    return {p['object_id'] for p in removals(mid)}

def patch_setup(filename, mid):
    requested = {p['object_id']: p for p in removals(mid)}
    if not requested:
        return
    path = Path(filename)
    data = path.read_bytes()
    count = struct.unpack_from('>I', data)[0]
    kept, seen = [], set()
    for i in range(count):
        record = data[4 + i * 48:4 + (i + 1) * 48]
        typ, ident = struct.unpack_from('>HH', record, 40)
        if ident in requested:
            expected = requested[ident]
            assert ident not in seen and typ == expected['type']
            assert all(abs(a - b) < .002 for a, b in zip(struct.unpack_from('>3f', record), expected['xyz']))
            seen.add(ident)
        else:
            kept.append(record)
    assert seen == set(requested), 'Native pickup removal did not match the expected USA objects'
    path.write_bytes(struct.pack('>I', len(kept)) + b''.join(kept) + data[4 + count * 48:])
