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
