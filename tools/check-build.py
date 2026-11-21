#!/usr/bin/env python3
"""Check ground pickups against the actual ROM setup records, optionally verify the stable release."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build'))
from campaign_data import ground, verify_ground_in_rom


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=ROOT / 'rom/dk64-krusha-dev.z64')
    parser.add_argument('--release', action='store_true', help='Also compare ROM and BPS to the v1.0.1 release fingerprints')
    args = parser.parse_args()
    verify_ground_in_rom(args.rom)
    print(f'All {len(ground())} ground pickups match the placement data.')
    if args.release:
        manifest = json.loads((ROOT / 'docs/releases/v1.0.1.json').read_text())
        files = [(args.rom, 'rom_sha256'), (ROOT / 'runtime/krusha/dk64-krusha-adventure.bps', 'bps_sha256')]
        for path, key in files:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != manifest[key]:
                raise SystemExit(f'{path.name} differs from {manifest["version"]}: {digest}')
            print(f'{path.name}  {digest}')


if __name__ == '__main__':
    main()
