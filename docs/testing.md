# Test a change

## Checks from a fresh clone

| What you changed | Run from the repository root |
| --- | --- |
| Ground pickup positions | Build the ROM and run `/usr/bin/python3 tools/check-build.py`. It reads the actual map setup tables. For balloons, also test the flight path and shoot one in game. |
| Save fields or compatibility | Run `/usr/bin/python3 tools/audit-save-layout.py` with your original USA ROM at `rom/dk64.z64`. This checks the allocation against the game’s 2 KiB EEPROM and the current header. |
| Key collection or turn-ins | Compile and run the host regression below. It links the same C state machine and turn-in controller as the ROM. |
| Exact release reproduction | After a clean build, run `/usr/bin/python3 tools/check-build.py --release`. This also checks the ROM and BPS against the approved SHA-256 values. |

```sh
mkdir -p runtime/tests
cc -Wall -Wextra -Werror -O2 tools/krusha-prison-turnin-test.c \
  src/krusha_recruitment.c src/krusha_prison_turnin.c -o runtime/tests/turnins
./runtime/tests/turnins
```

The host test covers key/lock ordering across files, interrupted turn-ins, duplicate visits and preservation of adjacent save bits. The emulator covers rendering, collision, music, transitions and EEPROM persistence on cold boot.

## Gameplay checks

Use Mupen64Plus with Glide64mk2 for the local launcher, or Mupen64Plus-Next with GLideN64 in RetroArch. Set 8 MB expansion memory, EEPROM 16K and CountPerOp 1. Enable framebuffer emulation for GLideN64. For widescreen, select 16:9 in the game and emulator display, and leave the emulator’s separate widescreen hack off.

`./tools/play-krusha.sh --info` prints the ROM hash, save directory and numbered slots. To run a disposable test, set `DK64_RUNTIME` to an absolute directory reserved for that test. Start a fresh file or copy a compatible native EEPROM you own into that profile. Load emulator save states only on the exact ROM that made them. The recruitment campaign uses save signature `K14.0`. The older pre-recruitment release uses a different format.

For recruitment changes, exercise a wrong-owner key touch, collect the same key after returning from far away, visit with fewer than five keys, and finish the fifth turn-in after a cold reload. Check that Krusha appears in the tag barrel and that his collectibles become available. Try Tag-Anywhere OFF, ON and Speed Mode on separate files because Speed Mode permanently grants rescue. For display changes, check standard and widescreen, with Mirror Mode active and inactive.

Two past bugs make good regression targets. A state that moved Chunky directly from underwater to dry land carried the underwater lighting into a key screenshot. Use a normal land approach for that check. Mini Tiny once came out of prison at the right size with the wrong music. Leave with crystals, listen for the Mini theme, and use up the last crystal to check that the local music returns.

Testing has concentrated on emulated Adventure mode. Physical N64 hardware, the full multiplayer mode and a complete start-to-111% playthrough remain unverified.
