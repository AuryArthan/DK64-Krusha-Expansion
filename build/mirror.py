"""Validate displaced USA instructions used by runtime mirror settings."""
import struct,zlib
PATCHES={0x806EA25C:0x256CFFD3,0x806EA2C8:0x256C002D,
0x80657F2C:0x0044082A,0x80657F7C:0x00C2082A,
0x8068BD0C:0x46068201,0x80706A54:0x03384023,
0x8065DFBC:0x35CE0602,0x8065DFC4:0x240F0406,0x8060AC60:0x0C001D15}
def validate_code(fh):
 for address,expected in PATCHES.items():
  fh.seek(address-0x805FB300)
  assert struct.unpack('>I',fh.read(4))[0]==expected,hex(address)

def validate_data(rom):
 data=zlib.decompress(rom[0xC29D4:],31)
 assert struct.unpack_from('>I',data,0x807599B0-0x80744460)[0]==0x3FB47AE1


def patch_map_texture_reload(fh, symbols):
    # USA map chunk teardown saves this index for the next G_SETTIMG load.
    offset = 0x80653F14 - 0x805FB300
    fh.seek(offset)
    assert fh.read(4) == bytes.fromhex('0c19adeb')
    address = int(symbols['mirrormaptextureidentity'], 16)
    fh.seek(offset)
    fh.write(struct.pack('>I', 0x0C000000 | ((address >> 2) & 0x03FFFFFF)))


def patch_race_map(filename):
    import os
    from pathlib import Path
    rom = Path(os.environ.get('DK64_BUILD_ROM', './rom/dk64-krusha-dev.z64'))
    symbols = dict(line.split()[:2][::-1] for line in rom.with_suffix('.sym').read_text().splitlines()
                   if len(line.split()) >= 2)
    hook = 0x0C000000 | ((int(symbols['mirrorracemapimage'], 16) >> 2) & 0x03FFFFFF)
    with open(filename, 'r+b') as f:
        # One native marker draw shared by all racers, then the four map tiles.
        for address in (0x8002BED0, 0x8002CDF4, 0x8002CE44, 0x8002CE94, 0x8002CEE4):
            f.seek(address - 0x80024000)
            assert f.read(4) == bytes.fromhex('0c1a316a')
            f.seek(-4, 1)
            f.write(struct.pack('>I', hook))

        # Camera-relative checkpoint bearing, calculated in race overlay code.
        # Keep the checkpoint and vehicle simulation in native world space.
        f.seek(0x8002F5D0 - 0x80024000)
        assert f.read(8) == bytes.fromhex('460081814600320d')
        address = int(symbols['mirrorcastlebearing'], 16)
        f.seek(-8, 1)
        f.write(struct.pack('>II', 0x08000000 | ((address >> 2) & 0x03FFFFFF), 0x46008181))
