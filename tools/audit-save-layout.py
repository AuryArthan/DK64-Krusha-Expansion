#!/usr/bin/env python3
"""Read-only USA EEPROM allocation audit. No emulator, ROM or save writes."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent


def audit(path):
    rom = path.read_bytes()
    assert hashlib.sha1(rom).hexdigest() == 'cf806ff2603640a748fca5026ded28802f1f4a50'
    data = zlib.decompress(rom[0xC29D4:0xCBE70], 15 + 32)
    code = zlib.decompress(rom[0x113F0:0xC29D4], 15 + 32)
    base = 0x101C50
    u32 = lambda p: struct.unpack_from('>I', rom, p)[0]
    levels = data[0x807445E0 - 0x80744460:0x807445E0 - 0x80744460 + 221]
    lobbies = struct.unpack_from('>9H', data, 0x80744734 - 0x80744460)
    persisted = {10, 13, 22, 28, 29, 30, 31, 35, 36, 39, 43, 517, 518, 519, 520}

    def file(table, index, seen=()):
        assert index not in seen
        pointer = base + u32(base + table * 4)
        start, end = (u32(pointer + i * 4) for i in (index, index + 1))
        if start & 0x80000000:
            return file(table, struct.unpack_from('>H', rom, base + (start & 0x7FFFFFFF))[0], seen + (index,))
        b = rom[base + start:base + (end & 0x7FFFFFFF)]
        return zlib.decompress(b, 15 + 32) if b[:2] == b'\x1f\x8b' else b

    counts = [0] * 8
    per_map = []
    for mid in range(221):
        setup = file(9, mid)
        if not setup:
            continue
        n = struct.unpack_from('>I', setup)[0]
        assert 4 + n * 48 <= len(setup)
        count = sum(struct.unpack_from('>H', setup, 4 + i * 48 + 40)[0] in persisted for i in range(n))
        if count:
            level = 7 if mid in lobbies else levels[mid]
            assert level < 8, ('Parent-map resolution needed', mid, level)
            counts[level] += count
            per_map.append(dict(map=mid, level=level, collected_object_bits=count))
    total = sum(counts)
    assert total == 1700, total

    def layout(extra, signature):
        bits = (((total + extra + 0x6B7) & ~63) + 0x27) & ~7
        globals_start = ((bits * 4 + 63) & ~63) // 8
        signature_start = (((globals_start * 8) + 0x207) & ~7) // 8
        assert signature_start + len(signature) + 1 <= 2048
        return dict(per_record_bits=bits, per_record_bytes=bits // 8,
                    record_count=4, player_files=3, recovery_records=1,
                    globals_start=globals_start, globals_bytes=64,
                    signature_start=signature_start, signature=signature,
                    signature_end_including_nul=signature_start + len(signature) + 1,
                    unused_tail_bytes=2048 - signature_start - len(signature) - 1,
                    record_crc_offset_bytes=bits // 8 - 4)

    native = layout(0, '7.2')
    expanded = layout(512, 'K07.1')
    for address, expected in [(0x8060B7F0, '27bdffd8afb1001c'),
                              (0x8060C648, '27bdffd8afbf001c'),
                              (0x8060C6B8, '27bdffd8afbf001c'),
                              (0x8060DC3C, '27bdffb8afb00018')]:
        assert code[address - 0x805FB300:address - 0x805FB300 + 8].hex() == expected
    fields = [
        ('colored_pickup_flags', 0, 384), ('fed_bananas', 384, 49),
        ('golden_bananas', 433, 40), ('blueprints_collected', 473, 8),
        ('medals', 481, 7), ('wallet', 488, 8), ('keys_collected', 496, 5),
        ('locks_open', 501, 5), ('recruited', 506, 1),
        ('bazooka_owned', 507, 1), ('shout_learned', 508, 1), ('reserved', 509, 3),
    ]
    header = (ROOT / 'include/krusha_progress.h').read_text()
    assert int(re.search(r'#define KRUSHA_SAVE_BITS (\d+)', header)[1]) == 512
    assert int(re.search(r'#define KRUSHA_PICKUP_SLOTS (\d+)', header)[1]) == fields[0][2]
    assert sum(width for _, _, width in fields) == 512
    assert all(a[1] + a[2] == b[1] for a, b in zip(fields, fields[1:]))
    assert native['per_record_bytes'] == 428 and expanded['per_record_bytes'] == 492
    assert 0x320 + 5 * 0xA1 == 0x645
    return dict(source_sha256=hashlib.sha256(rom).hexdigest(), eeprom_bytes=2048,
                native_prop_flag_counts_by_level=counts, native_prop_flags=total,
                native=native, experimental=expanded,
                extension_start_bit_within_record=800 + total,
                native_character_region_start_expanded=800 + total + 512,
                character_record_stride_bits=161,
                schema=[dict(name=n, bit=b, width=w) for n, b, w in fields],
                constraints=['384 separately tracked new colored pickups across the campaign, not 700 single-banana objects',
                             'Banana totals/GB counts/blueprint turn-ins derive from flags and a ROM-side item registry',
                             'Registry is provisional; no world placements; final weights/IDs need approved annotations',
                             'No old-format save import; native signature K07.1 distinguishes experimental saves',
                             'Only 10 bytes remain after the new signature; future schema growth requires redesign'],
                per_map=per_map)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', type=Path, default=ROOT / 'rom/dk64.z64')
    p.add_argument('--report', type=Path)
    args = p.parse_args()
    result = audit(args.rom)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open('x') as f:
            json.dump(result, f, indent=2)
            f.write('\n')
    print(json.dumps({k: result[k] for k in ('native_prop_flags', 'native', 'experimental', 'constraints')}, indent=2))


if __name__ == '__main__':
    main()
