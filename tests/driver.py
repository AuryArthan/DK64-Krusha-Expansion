"""Helpers for native emulator regressions in an isolated test profile."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
ROM = Path(os.environ.get('DK64_TEST_ROM', ROOT / 'rom/dk64-krusha-dev.z64'))
DIGEST = hashlib.sha256(ROM.read_bytes()).hexdigest()
RUN = Path(os.environ['DK64_RUNTIME']).resolve()
RUN.mkdir(parents=True, exist_ok=True)
(RUN / 'saves').mkdir(exist_ok=True)
results = {'rom_sha256': DIGEST, 'cold_boot': True,
           'fixtures': 'RAM positions / loading-zone redirects only; no character or move-code writes',
           'checks': []}
REPORT_NAME = 'krusha-tests.json'
proc = None

def start():
    global proc
    proc = subprocess.Popen(['/usr/bin/python3', str(ROOT / 'tools/control.py')], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, text=True, bufsize=1,
                            env={**os.environ, 'DK64_ROM': str(ROM)})
    print(proc.stdout.readline().strip(), flush=True)

def cmd(**command):
    proc.stdin.write(json.dumps(command) + '\n'); proc.stdin.flush()
    output = []
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError('Controller stopped')
        row = json.loads(line)
        if 'error' in row:
            raise RuntimeError(row['error'])
        output.append(row)
        if 'ok' in row:
            return output

def status():
    return cmd(status=True)[0]

def wait_frames(count, timeout=30):
    """Wait for native game time in a stable map, including slow renderers."""
    first = status()['frame']
    deadline = time.monotonic() + timeout
    while ((status()['frame'] - first) & 0xFFFFFFFF) < count:
        if time.monotonic() >= deadline:
            raise RuntimeError('Native frame wait timed out')
        cmd(wait=.2)

def wait_player_ready(timeout=30):
    deadline = time.monotonic() + timeout
    while status()['player']['state'] not in (12, 13, 0x4E, 0x4F):
        if time.monotonic() >= deadline:
            raise RuntimeError('Player did not return to ordinary movement')
        cmd(wait=.25)

def mem(address, kind='u32'):
    return cmd(read=[{'address': address, 'type': kind}])[0]['memory'][0]

def press(key, seconds=.25, wait=.5, shot=None):
    args = dict(keys=[key], seconds=seconds, wait=wait)
    if shot: args['shot'] = shot
    return cmd(**args)

def combo(key, wait=1, shot=None):
    cmd(down=['z'], wait=.25)
    press(key, .25, wait, shot)
    cmd(up=['z'])

def check(name, condition, detail=None):
    row = {'name': name, 'passed': bool(condition), 'detail': detail}
    results['checks'].append(row)
    (RUN / 'logs' / REPORT_NAME).write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(row), flush=True)
    if not condition:
        raise AssertionError(name)

def checkpoint(slot, name):
    press(str(slot), .1, .1); press('F5', .1, .4)
    files = list((RUN / 'states').glob(f'Donkey*.st{slot}'))
    if files:
        (RUN / 'states' / (name + f'.st{slot}')).write_bytes(files[0].read_bytes())

def place(xyz, facing=0, wait=1.5):
    cmd(tap='p', wait=.05)
    cmd(position=xyz, facing=facing, wait=.05)
    cmd(tap='p', wait=wait)

def scene(name):
    return cmd(scene=name)[0]

def go(map_id):
    cmd(tap='p', wait=.05)
    cmd(fixture_map=map_id, wait=.05)
    cmd(tap='p', wait=5)
    check('fixture loaded map ' + str(map_id), status()['map'] == map_id, status())

def zone_position(map_id, destination=None):
    rom = (ROOT / 'rom/dk64.z64').read_bytes()
    base = 0x101C50
    table = base + struct.unpack_from('>I', rom, base + 18*4)[0]
    start, end = struct.unpack_from('>II', rom, table + map_id*4)
    data = rom[base+(start & 0x7FFFFFFF):base+(end & 0x7FFFFFFF)]
    if data[:2] == b'\x1f\x8b': data = zlib.decompress(data, 15+32)
    for i in range(struct.unpack_from('>H', data)[0]):
        off = 2 + i*0x38
        kind, dest = struct.unpack_from('>HH', data, off+0x10)
        if (destination is None and kind == 17) or (kind in (9,16) and dest == destination):
            return list(struct.unpack_from('>hhh', data, off))
    raise RuntimeError(f'No normal door to {destination} in {map_id}')
