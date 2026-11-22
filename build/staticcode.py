def patchStaticCode(filename):
	with open(filename, "r+b") as fh:
		from mirror import validate_code, patch_map_texture_reload
		validate_code(fh)
		# Experimental M1 save foundation. Install before native EEPROM startup.
		# All original layout users derive sizes from 807ECEA0; adding a reserved
		# 512-bit region retains native records, CRCs, spare-slot rotation and globals.
		import os
		from pathlib import Path
		rom = os.environ.get('DK64_BUILD_ROM', './rom/dk64-krusha-dev.z64')
		symbols = dict(line.split()[:2][::-1] for line in
			Path(rom.replace('.z64', '.sym')).read_text().splitlines() if len(line.split()) >= 2)
		patch_map_texture_reload(fh, symbols)
		# Preserve the startup video argument and both original delay slots.
		# The wrapper calls the controller initializer once, before drawing.
		fh.seek(0x805FBD40 - 0x805FB300)
		assert fh.read(8) == bytes.fromhex('0c17ee51ac2ca0a8')
		fh.seek(-8, 1)
		fh.write((0x0C000000 | ((int(symbols['widescreenbootvideosetup'], 16) & 0x0FFFFFFF) >> 2)).to_bytes(4, 'big'))
		fh.seek(0x805FBD58 - 0x805FB300)
		assert fh.read(8) == bytes.fromhex('0c182a4000000000')
		fh.seek(-8, 1)
		fh.write(bytes(4))
		for address, name, prologue in [
			(0x80713764, 'krushaintrotitle', '3c0e807485ce4490'),
			(0x8060B7F0, 'krushasavelayoutinit', '27bdffd8afb1001c'),
			(0x8060C648, 'krushasavepackedwrite', '27bdffd8afbf001c'),
			(0x8060C6B8, 'krushasavepackedread', '27bdffd8afbf001c'),
			(0x8060DC3C, 'krushasaveloadgame', '27bdffb8afb00018'),
			(0x806C850C, 'krusharecruitmentplayerspawn', '27bdffd0afb00014'),
			(0x806ABE3C, 'krushacollecttotals', '27bdffd83c028080'),
			(0x806AA304, 'krushapausebuild', '27bdff703c0e8075'),
			(0x806AC07C, 'krushapausesprite', '27bdffa8afbf001c'),
			(0x806FB418, 'krushatotalgbs', '3c0480803c078080'),
			(0x806F8278, 'krushahudgbs', '308e00ff000e7880'),
			(0x806B1DD4, 'm3kasplatinit', '3c0280808c42bb40'),
			(0x806A5C60, 'm3enemydrop', '27bdffc03c0e8080'),
			(0x806A610C, 'm3blueprint', '27bdffe8afbf0014'),
			(0x806C9974, 'm4encounterplayerdamage', '308e00ff000ec080'),
		]:
			fh.seek(address - 0x805FB300)
			assert fh.read(8) == bytes.fromhex(prologue), f'Unexpected save prologue at {address:X}'
			target = int(symbols[name], 16)
			fh.seek(address - 0x805FB300)
			fh.write((0x08000000 | ((target & 0x0FFFFFFF) >> 2)).to_bytes(4, 'big'))
			fh.write(bytes(4))
		# The size initializer is replaced completely, without a native trampoline.
		# Clear only its unreachable body, retaining offsets and overlay slot size.
		fh.seek(0x8060B7F8 - 0x805FB300)
		fh.write(bytes(0x8060B84C - 0x8060B7F8))
		# Title renderer is also replaced completely. Retain its entry hook and
		# all overlay offsets, freeing compression headroom only in dead code.
		fh.seek(0x8071376C - 0x805FB300)
		fh.write(bytes(0x807138A4 - 0x8071376C))

		# Native EEPROM writer: desired data was already snapshotted by the
		# preceding memcpy. Replace ONLY its local old-device comparison copy.
		fh.seek(0x8060D38C - 0x805FB300)
		assert fh.read(24) == bytes.fromhex('27be00603c05807f24a5d6a803c020250c000c0024060800'), 'EEPROM comparison copy differs from USA'
		fh.seek(0x8060D39C - 0x805FB300)
		fh.write((0x0C000000 | ((int(symbols['krushasavecomparesnapshot'],16) & 0x0FFFFFFF) >> 2)).to_bytes(4,'big'))

		# Map setup's native actor-list constructor. Only the two new Isles
		# crate spawners receive a completion-aware activation predicate.
		fh.seek(0x806887F0 - 0x805FB300)
		assert fh.read(4) == (0x0C000000 | ((0x80688FC0 & 0x0FFFFFFF) >> 2)).to_bytes(4, 'big')
		fh.seek(-4, 1)
		fh.write((0x0C000000 | ((int(symbols['completioncratesetup'],16) & 0x0FFFFFFF) >> 2)).to_bytes(4,'big'))

		# Original bne v1,at followed by li a2,129. Keep its delay slot.
		fh.seek(0x8067ED28 - 0x805FB300)
		assert fh.read(8) == bytes.fromhex('1461000224060081')
		fh.seek(-8, 1)
		fh.write((0x08000000 | ((int(symbols['islesrambiowner'],16) & 0x0FFFFFFF) >> 2)).to_bytes(4,'big'))

		# The only animal first-use dialogue call. Leave the native dialogue
		# and its flags intact in the original levels.
		fh.seek(0x806EDD0C - 0x805FB300)
		assert fh.read(4) == bytes.fromhex('0c1bb542')
		fh.seek(-4, 1)
		fh.write((0x0C000000 | ((int(symbols['islesanimalfirstusetext'], 16) & 0x0FFFFFFF) >> 2)).to_bytes(4, 'big'))

		# Keep the native manual reversion input immediately after this branch.
		fh.seek(0x806CB580 - 0x805FB300)
		assert fh.read(12) == bytes.fromhex('331908001320000900000000')
		fh.seek(-12, 1)
		fh.write((0x08000000 | ((int(symbols['islesanimalzone'], 16) & 0x0FFFFFFF) >> 2)).to_bytes(4, 'big'))
		fh.write(bytes(4))

		# Adjust the native depth local after either movement profile loads
		# it. Both the dive test and the surface clamp use that same value.
		fh.seek(0x806D85B0 - 0x805FB300)
		assert fh.read(8) == bytes.fromhex('8e0e00002401004e')
		fh.seek(-8, 1)
		fh.write((0x08000000 | ((int(symbols['islesrambiswimdepthhook'], 16) & 0x0FFFFFFF) >> 2)).to_bytes(4, 'big'))
		fh.write(bytes(4))

		# Only the rainbow award's FTT call, after the original five-wallet loop.
		# The wrapper credits the sixth adventure wallet even when Krusha is OFF.
		fh.seek(0x806F54E0 - 0x805FB300)
		rainbow_body = fh.read(0x806F58A0 - 0x806F54E0)
		native_call = (0x0C000000 | ((0x806F5498 & 0x0FFFFFFF) >> 2)).to_bytes(4, 'big')
		matches = [i for i in range(0, len(rainbow_body), 4) if rainbow_body[i:i+4] == native_call]
		assert len(matches) == 1, 'Rainbow tutorial call differs from USA'
		fh.seek(0x806F54E0 - 0x805FB300 + matches[0])
		fh.write((0x0C000000 | ((int(symbols['krusharainbowcredit'], 16) & 0x0FFFFFFF) >> 2)).to_bytes(4, 'big'))

		from recruitment_room import patch_code as patchRoom
		patchRoom(fh,symbols)
		# Gameplay's controller read, after which a native fade zeroes the stick.
		# Give only a committed Mini prison entry its original approach stick.
		fh.seek(0x805FC3F4 - 0x805FB300)
		assert fh.read(8) == bytes.fromhex('0c182b1fac39a048')
		fh.seek(-8, 1)
		fh.write((0x0C000000 | ((int(symbols['krushaprisonreadadventurepad'], 16) & 0x0FFFFFFF) >> 2)).to_bytes(4, 'big'))
		# Only the barrel confirmation's native busy check. Keep native layout,
		# rotation and cleanup; reject an unavailable sixth choice before swap.
		fh.seek(0x806838A8 - 0x805FB300)
		assert fh.read(8)==bytes.fromhex('0c18a46700000000')
		fh.seek(0x806838A8 - 0x805FB300)
		fh.write((0x0C000000|((int(symbols['krushabarrelselectionbusy'],16)&0x0FFFFFFF)>>2)).to_bytes(4,'big'))
		from progress_pause import patchPause
		patchPause(fh, symbols)
		from m2_pickups import patch_code
		patch_code(fh,symbols)
		# T&S's native five-character sum is unrolled. Keep its ownership,
		# decrement, animation, quota and boss-selection logic; add sixth fed
		# stock only to the quota-stop comparison. Delay-slot LUI stays native.
		fh.seek(0x806BE49C - 0x805FB300)
		assert fh.read(12) == bytes.fromhex('0069082a142000063c0a8080'), 'T&S quota differs from USA'
		fh.seek(0x806BE49C - 0x805FB300)
		fh.write((0x08000000 | ((int(symbols['m3tnsquota'],16) & 0x0FFFFFFF) >> 2)).to_bytes(4,'big'))
		fh.write(bytes(4))
		from m3_progress import patch_pickups
		patch_pickups(fh,symbols)
		# Runtime script adapter's displaced native instructions (see trampoline).
		fh.seek(0x80614EBC - 0x805FB300)
		assert fh.read(8) == bytes.fromhex('8c82000444802000'), 'Animation script prologue differs from USA'
		fh.seek(0x806F79E0 - 0x805FB300)
		assert fh.read(8) == bytes.fromhex('00047400000e7c03'), 'Pickup effect prologue differs from USA'
		fh.seek(0x806F9B64 - 0x805FB300)
		assert fh.read(8) == bytes.fromhex('27bdff883c0e8075'), 'GB portrait constructor prologue differs from USA'
		from m4_rewards import patch_code as patchM4
		patchM4(fh,symbols)
		from m5_campaign import patch_code as patchM5
		patchM5(fh,symbols)

		# RDRAM Address - 0x5FB300 = ROM address
		# Only the fairy-camera entry check: allow character 5, still exclude
		# Rambi/Enguarde. No change to collectible or character identities.
		fh.seek(0x806E98A0 - 0x805FB300)
		assert fh.read(4) == bytes.fromhex("2b210005"), "Camera guard differs from USA 1.0"
		fh.seek(0x806E98A0 - 0x805FB300)
		fh.write(bytes.fromhex("2b210006"))

		# Replace just the CPU pixel-copy loop between decompression and the
		# native clear/writeback. s2 points to the two framebuffer pointers.
		from PIL import Image
		with Image.open("bin/Nintendo_Krusha.png") as logo:
			width, height = logo.size
		assert height == 48 and width % 4 == 0 and width <= 320
		fh.seek(0x805FB8A0 - 0x805FB300)
		assert fh.read(12) == bytes.fromhex('8e4300003c0700023401f080')
		fh.seek(0x805FB900 - 0x805FB300)
		assert fh.read(8) == bytes.fromhex('246301008e430004')
		fh.seek(0x805FB8A0 - 0x805FB300)
		words = (0x8E440000, 0x8FA5004C,  # lw a0,0(s2); lw a1,0x4c(sp)
		         0x0C000000 | ((int(symbols['krushabootlogocopy'], 16) & 0x0FFFFFFF) >> 2),
		         0x24060000 | width,       # copy width in the call delay slot
		         0x3C070002, 0x08000000 | ((0x805FB904 & 0x0FFFFFFF) >> 2),
		         0x34E75800)               # restore framebuffer byte count
		for word in words:
			fh.write(word.to_bytes(4, 'big'))

		# Heap Shrink
		fh.seek(0x15212)
		fh.write(bytearray([0x80,0x5D])) # Heap Shrink: lui t5, 0x805d

		# Starting Map & Exit
		# fh.seek(0x119247)
		# fh.write(bytearray([0x22])) # File Start Map
		# fh.seek(0x11925B)
		# fh.write(bytearray([0x0])) # File Start Exit

		# Load race overlay when no overlay specified
		# fh.seek(0x15108) # RDRAM 80631048
		# fh.write(bytearray([0x24, 0x09, 0x00, 0x05])) # ADDIU $t1 $zero 0x0005

		# Increase Object Model 2 Per Map Count
		fh.seek(0x36D24)
		fh.write(bytearray([0x24, 0x0a, 0x02, 0x12])) # li $t2, 465 (original, Jungle Japes)
		fh.seek(0x36D34)
		fh.write(bytearray([0x24, 0x0b, 0x02, 0x12])) # li $t3, 450 (original, All Other Maps)
		fh.seek(0x36CF4)
		fh.write(bytearray([0x24, 0x19, 0x02, 0x12])) # li $t9, 500 (original, Frantic Factory)
		fh.seek(0x36D14)
		fh.write(bytearray([0x24, 0x09, 0x02, 0x12])) # li $t1, 485 (original, Gloomy Galleon)
		fh.seek(0x36D04)
		fh.write(bytearray([0x24, 0x08, 0x02, 0x12])) # li $t0, 500 (original, Angry Aztec)
		fh.seek(0x36CE4)
		fh.write(bytearray([0x24, 0x18, 0x02, 0x12])) # li $t8, 530 (original, Fungi Forest)
