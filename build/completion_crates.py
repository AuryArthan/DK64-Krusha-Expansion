"""Two native animal-crate setup records for the DK Isles completion reward."""
from pathlib import Path
import struct

from barrel_assets import read_file

# Donor map and ID, actor type minus 16, Isles ID, position and optional yaw.
CRATES = (
    (7, 27, 2, 620, (2538, 512, 1940), None),
    (30, 13, 113, 621, (2500, 441, 2764), 2960),
)


def actor_table(setup):
    offset = 4 + 48 * struct.unpack_from(">I", setup)[0]
    offset += 4 + 36 * struct.unpack_from(">I", setup, offset)[0]
    count = struct.unpack_from(">I", setup, offset)[0]
    end = offset + 4 + 56 * count
    assert end <= len(setup)
    return offset, end, [setup[i:i+56] for i in range(offset+4, end, 56)]


def patch_setup(path, mid):
    if mid != 34:
        return
    path = Path(path)
    rom = Path("rom/dk64.z64").read_bytes()
    setup = path.read_bytes()
    start, end, records = actor_table(setup)
    ids = {struct.unpack_from(">H", r, 52)[0] for r in records}
    for donor_map, donor_id, kind, new_id, position, yaw in CRATES:
        assert new_id not in ids
        _, _, source = actor_table(read_file(rom, 9, donor_map))
        donor, = [r for r in source if struct.unpack_from(">HH", r, 50) == (kind, donor_id)]
        crate = bytearray(donor)
        struct.pack_into(">3f", crate, 0, *position)
        if yaw is not None:
            struct.pack_into(">H", crate, 46, yaw)
        struct.pack_into(">H", crate, 52, new_id)
        records.append(crate)
    path.write_bytes(setup[:start] + struct.pack(">I", len(records)) + b"".join(records) + setup[end:])
