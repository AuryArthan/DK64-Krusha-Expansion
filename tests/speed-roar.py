#!/usr/bin/env python3
"""Start a fresh Speed Mode file and use Krusha's roar with real controller inputs."""
import hashlib
import os
from pathlib import Path
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
rom = Path(os.environ.get('DK64_TEST_ROM', ROOT / 'rom/dk64-krusha-dev.z64')).resolve()
parent = ROOT / 'runtime/tests'
parent.mkdir(parents=True, exist_ok=True)
run = Path(tempfile.mkdtemp(prefix='speed-roar-', dir=parent))
print('Speed Mode test profile:', run, flush=True)
os.environ.update(DK64_RUNTIME=str(run), DK64_TEST_ROM=str(rom))
(run / 'saves').mkdir()
md5 = hashlib.md5(rom.read_bytes()).hexdigest()[:8].upper()
(run / 'saves' / f'Donkey Kong 64 (local build)-{md5}.eep').write_bytes(bytes([255]) * 2048)
(run / 'config').mkdir()
config = (ROOT / 'tools/config/mupen64plus.cfg').read_text()
(run / 'config/mupen64plus.cfg').write_text(config + '\n[Core]\nVersion = 1.010000\nGbCameraVideoCaptureBackend1 = "dummy"\n')

import driver as d
import menus
import options

d.REPORT_NAME = 'speed-roar.json'
d.results['fixtures'] = 'Erased EEPROM, native menus, D-pad tags and instrument inputs. No gameplay memory writes.'
symbols = {row[1]: int(row[0], 16) for line in rom.with_suffix('.sym').read_text().splitlines()
           if len(row := line.split()) >= 2}
moves = symbols['movesbase']

def energy():
    return d.cmd(read=[dict(address=moves + i*94 + 8, type='u16') for i in range(6)], wait=0)[0]['memory']

def play_instrument():
    d.cmd(down=['z'], wait=0)
    d.wait_frames(3)
    d.cmd(down=['i'], wait=0)
    try:
        d.wait_frames(3)
    finally:
        d.cmd(up=['z', 'i'], wait=0)
    d.wait_frames(3)
    return d.status()['player']['state']

def start_adventure(menu):
    menus.files(d, menu)
    menus.preview(d, menu, 0)
    d.press('Shift_L', .3, .6)
    deadline = time.monotonic() + 110
    while time.monotonic() < deadline:
        st = d.status()
        if st['map'] == 34 and st['frame'] > 150 and st.get('player', {}).get('state') == 12:
            return
        if st['map'] in (80, 34):
            d.cmd(wait=.25)
        else:
            d.press('Return', .15, .3)
    raise RuntimeError(('Speed Mode file did not reach DK Isles', d.status()))

def open_speed_menu():
    menu = menus.root(d)
    menus.select(d, menu, 4, 1)
    d.press('Shift_L', .3, .8)
    menus.ready(d, menu, 9)
    options.set_value(d, menu, 1, 2, symbols, None, lambda page: menus.ready(d, menu, page))
    d.press('Control_L', .3, .8)
    menus.ready(d, menu, 1)
    return menu

try:
    start_adventure(open_speed_menu())
    initial = energy()
    print('Fresh Speed Mode energy:', initial, flush=True)
    d.check('DK starts with his instrument and can spend one charge', play_instrument() == 103)
    d.wait_player_ready(60)
    d.press('a', .2, .8)
    d.check('D-pad selects Krusha', d.status()['character'] == 5, d.status())
    d.check('Krusha owns the upgraded shout', d.mem(moves + 5*94 + 4, 'u8') == 15)
    state = play_instrument()
    d.check('Fresh Speed Mode starts all six at 20 and permits an immediate roar',
            initial == [20]*6 and state == 103, dict(initial_energy=initial, roar_state=state))
    d.wait_player_ready(60)
    d.check('Each move spent one charge from its own counter', energy() == [19,20,20,20,20,19], energy())
    d.press('d', .2, .8)
    d.press('a', .2, .8)
    d.wait_frames(45)
    d.check('Tagging back and idle frames preserve the spent charge',
            d.status()['character'] == 5 and energy()[-1] == 19, energy())
    d.check('A second roar spends a second charge', play_instrument() == 103)
    d.wait_player_ready(60)
    d.check('Second charge remains spent', energy()[-1] == 18, energy())
    menus.stop(d)
    start_adventure(open_speed_menu())
    stock = energy()
    d.check('Reopening the native Speed Mode file gives all six the usual starting stock',
            stock == [20]*6, stock)
finally:
    menus.stop(d)
