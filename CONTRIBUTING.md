# Build and modify Krusha Expansion

## Build v1.0.0

The supported developer setup is Linux x86-64 on an Ubuntu-compatible distribution. You’ll need Git, curl, tar, make, host C and C++ compilers, apt/dpkg, and Pillow available to `/usr/bin/python3`. Setup installs its compiler, assembler and compression tools into a local cache.

1. From the repository root, create `rom/` and put your clean USA big-endian ROM at `rom/dk64.z64`. Its SHA-1 is `cf806ff2603640a748fca5026ded28802f1f4a50`.
2. Run the following commands in order.

```sh
./tools/setup-build-tools.sh
./tools/build-krusha.sh
/usr/bin/python3 tools/check-build.py --release
```

The playable file is `rom/dk64-krusha-dev.z64`. The builder also writes the BPS to `runtime/krusha/dk64-krusha-adventure.bps`. You can reuse an existing compatible tool cache by exporting `DK64_TOOL_ROOT` as its absolute path. [Release fingerprints](docs/releases/v1.0.0.json)

## First edit · move one banana

In Jungle Japes a silver trail leads to the marked banana cage. The single nearest the cage is **JP-S01**, object **515** on map **7**. It’s a useful first edit because you can identify it both in the ROM and in the world.

1. Open the campaign placement file below and search for `"label": "JP-S01"`. Its `xyz` is `[845.295, 292, 2050.156]`. Try changing the first coordinate to `865.295`. This moves the banana 20 units along X at the same height. Keep its object ID, pickup slot and other fields. The slot is how a save remembers that this particular banana was collected. [Campaign placements](data/placements/campaign.json)
2. Run `./tools/build-krusha.sh`, then `/usr/bin/python3 tools/check-build.py`. The check reads the rebuilt level records and compares each ground pickup’s type, object ID and coordinates with your source data.
3. For the bundled emulator, run `./tools/setup-emulator.sh` once and launch with `./tools/play-krusha.sh`. Select Speed Mode on a disposable Adventure file to make Krusha immediately available. Enter Jungle Japes, follow the silver trail to the cage, and collect the moved banana. Pause to check his banana count. The launcher gives each ROM hash its own save and state directory. [Emulator and testing notes](docs/testing.md)

For a map view, run `/usr/bin/python3 tools/build-map-atlas.py` and open `runtime/map-atlas/atlas/index.html`. Select a silver marker and choose **Move on map A**, or adjust X/Y/Z and its access notes. Export the plan to keep your edits. Transfer the reviewed coordinates to the matching marker in the campaign file and rebuild. [Placement atlas](tools/map-atlas/README.md)

## Find the feature you want to change

| Feature | Start here |
| --- | --- |
| Bananas, coins, Kasplats, pads, cages and patrols | [Campaign placements](data/placements/campaign.json) and [world object builder](build/m5_campaign.py) |
| Key locations and rescue eligibility | [Five keys](data/placements/recruitment-keys.json) and [recruitment state machine](src/krusha_recruitment.c) |
| Prison exterior, interior, locks and dialogue | [Exterior geometry](build/recruitment_assets.py), [interior geometry](build/recruitment_room.py), [dialogue and scene](src/krusha_prison_scene.c) |
| Gear, prices and voice | [Shop logic](src/m3_progress.c), [Candy’s text](build/candy_dialogue.py), [bazooka](src/krusha_ammo.c), [Primitive Roar](src/krusha_roar.c) |
| Progress, save compatibility and pause totals | [Save layout](include/krusha_progress.h), [progress](src/krusha_progress.c), [colored-key display](src/krusha_recruitment_pause.c) |
| Portraits, title artwork and shout audio | [Media sources and conversion commands](assets/README.md) |
| Tag barrel, options and widescreen | [Tag barrel](src/krusha_barrel.c), [Options](src/krusha_options.c), [widescreen](src/widescreen.c), [mirror mode](src/mirror.c) |

The assembly entry points and symbol map are under `asm/` and `include/`. The Python modules under `build/` read the original ROM, compile the C hooks and assemble game resources. Generated objects, headers, emulator profiles and atlas output stay local. [AI handoff](codex_handoff/README.md) · [License and scope](LICENSE.md)
