import os
import shutil
import gzip
import zlib
import subprocess
import hashlib
import sys

# Keep Windows support; use native tools on Linux. Build from the repository root.
GCC = os.environ.get("N64_GCC", "mips64-elf-gcc")
ARMIPS = os.environ.get("ARMIPS", "build/armips.exe" if os.name == "nt" else "armips")
GZIP = os.environ.get("N64_GZIP", "./build/gzip.exe" if os.name == "nt" else "gzip")
# Explicit QA-only build; ordinary candidates never contain the test mailbox.
RECRUITMENT_QA = os.environ.get("DK64_RECRUITMENT_QA") == "1"
ROMName = "./rom/dk64.z64"
with open(ROMName, "rb") as base:
	base_bytes = base.read()
	if hashlib.sha1(base_bytes).hexdigest() != "cf806ff2603640a748fca5026ded28802f1f4a50":
		raise SystemExit("Expected the original USA DK64 ROM (SHA-1 CF806FF2603640A748FCA5026DED28802F1F4A50)")
from mirror import validate_data
validate_data(base_bytes)

# Measure how long this takes
import time
start_time = time.time()

print("Cranky's Lab Build System")
print()

print("[1 / 8] - Compiling C Code")
from candy_dialogue import patch_candy_dialogue
from character_colors import write_identity_header
write_identity_header()
from klump_colors import prepare as prepareKlumpColors
prepareKlumpColors()
from intro_assets import prepare as prepareIntro
prepareIntro(ROMName)
from m2_pickups import prepare as prepareM2, patch_setup as patchM2Setup, patch_paths as patchM2Paths
prepareM2(ROMName)
from m5_campaign import prepare as prepareM5, patch_scripts as patchM5Scripts
prepareM5(ROMName)
from recruitment_assets import prepare as prepareRecruitment, patch_setup as patchRecruitmentSetup
prepareRecruitment(ROMName)
from recruitment_keys import prepare as prepareRecruitmentKeys, patch_setup as patchRecruitmentKeys
prepareRecruitmentKeys(ROMName)
from recruitment_scene import prepare as prepareRecruitmentScene
prepareRecruitmentScene(ROMName)
from recruitment_room import prepare as prepareRecruitmentRoom, files as recruitmentRoomFiles, patch_data as patchRecruitmentData
prepareRecruitmentRoom(ROMName)
from recruitment_barrel import prepare as prepareRecruitmentBarrel
prepareRecruitmentBarrel()
from krusha_victory import prepare as prepareVictory
prepareVictory(ROMName)
from m4_rewards import prepare as prepareM4, patch_japes as patchM4Japes, patch_cave as patchM4Cave, patch_setup as patchM4Setup
prepareM4(ROMName)
if os.path.exists("obj"):
	shutil.rmtree('obj')
os.mkdir("obj")
with open('./asm/objects.asm', 'w') as obj_asm:
	for root, dirs, files in os.walk(r'src'):
		dirs.sort()
		files.sort()
		for file in files:
			if file.endswith('.c'):
				_o = os.path.join(root, file).replace("/", "_").replace("\\", "_").replace(".c", ".o")
				print(os.path.join(root, file))
				obj_asm.write(".importobj \"obj/" + _o + "\"\n")
				subprocess.run([GCC, "-Wall", "-O1", "-fno-common", "-mtune=vr4300", "-march=vr4300", "-mabi=32", "-fomit-frame-pointer", "-G0", "-c", os.path.join(root, file)], check=True)
				shutil.move("./" + file.replace(".c", ".o"), "obj/" + _o)
	if RECRUITMENT_QA:
		subprocess.run([GCC, "-Wall", "-O1", "-fno-common", "-mtune=vr4300", "-march=vr4300", "-mabi=32", "-fomit-frame-pointer", "-G0", "-c", "tools/recruitment-qa-driver.c", "-o", "obj/recruitment_qa.o"], check=True)
		obj_asm.write('.importobj "obj/recruitment_qa.o"\n')
print()

# Infrastructure for recomputing DK64 global pointer tables
from recompute_pointer_table import pointer_tables, dumpPointerTableDetails, replaceROMFile, writeModifiedPointerTablesToROM, parsePointerTables, getFileInfo, make_safe_filename
from recompute_overlays import isROMAddressOverlay, readOverlayOriginalData, replaceOverlayData, writeModifiedOverlaysToROM

# Patcher functions for the extracted files
from mirror import patch_race_map
from staticcode import patchStaticCode
from mainmenu import patchMainMenu, patchDolbyText
from krusha import patchKrushaShop
from barrel_assets import prepareBarrelAssets, appendBarrelAssets

prepareBarrelAssets(ROMName)

ROMName = "./rom/dk64.z64"
newROMName = os.environ.get("DK64_BUILD_ROM", "./rom/dk64-krusha-dev.z64")

if os.path.exists(newROMName):
	os.remove(newROMName)
shutil.copyfile(ROMName, newROMName)

# Resolve resident hook addresses before patching the compressed shop overlay.
subprocess.run([ARMIPS, "asm/main.asm", "-definelabel", "RECRUITMENT_QA", str(int(RECRUITMENT_QA)), "-strequ", "OUTPUT_ROM", newROMName,
                "-sym", newROMName.replace(".z64", ".sym")], check=True)

from campaign_data import maps as campaignMaps, balloons as campaignBalloons, area as campaignArea
from completion_crates import patch_setup as patchCompletionCrates
from native_pickup_adjustments import patch_setup as patchNativePickups
file_dict = []
for mid in campaignMaps():
    if mid==7:continue
    file_dict.append({"name":f"M5 map{mid} pickups/rewards","pointer_table_index":9,"file_index":mid,"source_file":f"bin/M5Setup{mid}.bin","patcher":lambda name,mid=mid:(patchM2Setup(name,mid),patchM4Setup(name,mid),patchNativePickups(name,mid),patchRecruitmentSetup(name,mid),patchRecruitmentKeys(name,mid),patchCompletionCrates(name,mid))})
    if campaignArea(mid):
        file_dict.append({"name":f"M5 map{mid} cage script","pointer_table_index":10,"file_index":mid,"source_file":f"bin/M5Scripts{mid}.bin","patcher":lambda name,mid=mid:patchM5Scripts(name,mid)})
    if campaignBalloons(mid):
        file_dict.append({"name":f"M5 map{mid} balloon paths","pointer_table_index":15,"file_index":mid,"source_file":f"bin/M5Paths{mid}.bin","patcher":lambda name,mid=mid:patchM2Paths(name,mid),"do_not_compress":True})
file_dict += [
	{"name":"M4 cave reward", "pointer_table_index":9, "file_index":33,
	 "source_file":"bin/M4CaveSetup.bin", "patcher":patchM4Cave},
	{"name":"M2 Japes balloon paths", "pointer_table_index":15, "file_index":7,
	 "source_file":"bin/M2JapesPaths.bin", "patcher":patchM2Paths, "do_not_compress":True},
	{"name":"M2 Japes pickups", "pointer_table_index":9, "file_index":7,
	 "source_file":"bin/M2JapesSetup.bin", "patcher":lambda name:(patchM2Setup(name),patchM4Japes(name))},
	{
		"name": "Factory race map draw calls", "start": 0xDF600,
		"compressed_size": 0xE649A - 0xDF600, "source_file": "bin/KrushaRace.bin",
		"use_external_gzip": True, "patcher": patch_race_map,
	},
	{
		"name": "Shop menu code",
		"start": 0xCBE70,
		"compressed_size": 0xD4554 - 0xCBE70,
		"source_file": "bin/KrushaMenu.bin",
		"use_external_gzip": True,
		"patcher": patchKrushaShop,
	},
	{
		"name": "Static ASM Code",
		"start": 0x113F0,
		"compressed_size": 0xB15E4,
		"source_file": "bin/StaticCode.bin",
		"use_external_gzip": True,
		"patcher": patchStaticCode,
	},
	{
		"name": "Nintendo Logo",
		"pointer_table_index": 14,
		"file_index": 94,
		"source_file": "bin/Nintendo_Krusha.png",
		#"source_file": "bin/Nintendo_TJ.png",
		#"source_file": "bin/Nintendo_Adam.png",
		"texture_format": "rgba5551",
	},
	{
		"name": "Dolby Logo",
		"pointer_table_index": 14,
		"file_index": 176,
		"source_file": "bin/Arthan.png",
		"texture_format": "rgba5551",
	},
	{
		"name": "Dolby Text",
		"pointer_table_index": 12,
		"file_index": 13,
		"source_file": "bin/DolbyText.bin",
		"patcher": patchDolbyText,
	},
	{
		"name": "Title Screen",
		"pointer_table_index": 14,
		"file_index": 44,
		"source_file": "bin/ExpansionTitle.png",
		"texture_format": "rgba5551",
		"use_zlib": True,
	},
	{
		"name": "Candy Text",
		"pointer_table_index": 12,
		"file_index": 9,
		"source_file": "bin/CandyText.bin",
		"patcher": patch_candy_dialogue,
	},
	{
		"name": "Menu Text",
		"pointer_table_index": 12,
		"file_index": 37,
		"source_file": "bin/Menu.bin",
		"patcher": patchMainMenu,
	},
	# {
	# 	"name": "Chunky's Vest Back (Green & Yellow)",
	# 	"pointer_table_index": 25,
	# 	"file_index": 3769,
	# 	"do_not_delete": True,
	# 	"do_not_extract": True,
	# 	"source_file": "bin/ChunkyVest.bin",
	# 	# "texture_format": "rgba5551",
	# },
	# {
	# 	"name": "Helm and Rap Font 1",
	# 	"pointer_table_index": 14,
	# 	"file_index": 3,
	# 	"source_file": "bin/Font1/font_1120F28.png",
	# 	"texture_format": "ia8",
	# 	"use_zlib": True,
	# },
	# {
	# 	"name": "Helm and Rap Font 2",
	# 	"pointer_table_index": 14,
	# 	"file_index": 4,
	# 	"source_file": "bin/Font1/font_112122A.png",
	# 	"texture_format": "ia8",
	# 	"use_zlib": True,
	# },
	# {
	# 	"name": "Helm and Rap Font 3",
	# 	"pointer_table_index": 14,
	# 	"file_index": 5,
	# 	"source_file": "bin/Font1/font_1121448.png",
	# 	"texture_format": "ia8",
	# 	"use_zlib": True,
	# },
]

file_dict += recruitmentRoomFiles()
file_dict.append(dict(name="Private R03 resident metadata",start=0xC29D4,compressed_size=0x949C,source_file="bin/RecruitmentData.bin",use_external_gzip=True,patcher=patchRecruitmentData))

map_replacements = [
	# {
	# 	"name": "Test Map",
	# 	"map_index": 0,
	# 	# "map_folder": "maps/208 - Bloopers_Ending/"
	# 	# "map_folder": "maps/38 - Angry_Aztec/"
	# 	"map_folder": "maps/path_test/"
	# },
	# {
	# 	"name": "Fairy Island Exit Test",
	# 	"map_index": 189,
	# 	"map_folder": "maps/exit_test/"
	# },
	# {
	# 	"name": "Japes Exit Test",
	# 	"map_index": 7,
	# 	"map_folder": "maps/exit_test/"
	# },
]

# Test all map replacements at once
# from map_names import maps
# for mapIndex, mapName in enumerate(maps):
# 	mapPath = "maps/" + str(mapIndex) + " - " + make_safe_filename(mapName) + "/"
# 	map_replacements.append({
# 		"name": mapName,
# 		"map_index": mapIndex,
# 		"map_folder": mapPath,
# 	})

with open(ROMName, "rb") as fh:
	print("[2 / 8] - Parsing pointer tables")
	parsePointerTables(fh)
	readOverlayOriginalData(fh)

	for x in map_replacements:
		print(" - Processing map replacement " + x["name"])
		if os.path.exists(x["map_folder"]):
			found_geometry = False
			found_floors = False
			found_walls = False
			should_compress_walls = True
			should_compress_floors = True
			for y in pointer_tables:
				if not "encoded_filename" in y:
					continue

				# Convert decoded_filename to encoded_filename using the encoder function
				# Eg. exits.json to exits.bin
				if "encoder" in y and callable(y["encoder"]):
					if "decoded_filename" in y and os.path.exists(x["map_folder"] + y["decoded_filename"]):
						y["encoder"](x["map_folder"] + y["decoded_filename"], x["map_folder"] + y["encoded_filename"])
				
				if os.path.exists(x["map_folder"] + y["encoded_filename"]):
					if y["index"] == 1:
						with open(x["map_folder"] + y["encoded_filename"], "rb") as fg:
							byte_read = fg.read(10)
							should_compress_walls = (byte_read[9] & 0x1) != 0
							should_compress_floors = (byte_read[9] & 0x2) != 0
						found_geometry = True
					elif y["index"] == 2:
						found_walls = True
					elif y["index"] == 3:
						found_floors = True

			# Check that all walls|floors|geometry files exist on disk, or that none of them do
			walls_floors_geometry_valid = (found_geometry == found_walls) and (found_geometry == found_floors)

			if not walls_floors_geometry_valid:
				print("  - WARNING: In map replacement: " + x["name"])
				print("    - Need all 3 files present to replace walls, floors, and geometry.")
				print("    - Only found 1 or 2 of them out of 3. Make sure all 3 exist on disk.")
				print("    - Will skip replacing walls, floors, and geometry to prevent crashes.")

			for y in pointer_tables:
				if not "encoded_filename" in y:
					continue

				if os.path.exists(x["map_folder"] + y["encoded_filename"]):
					# Special case to prevent crashes with custom level geometry, walls, and floors
					# Some of the files are compressed in ROM, some are not
					if y["index"] in [1, 2, 3] and not walls_floors_geometry_valid:
						continue

					do_not_compress = "do_not_compress" in y and y["do_not_compress"]
					if y["index"] == 2:
						do_not_compress = not should_compress_walls
					elif y["index"] == 3:
						do_not_compress = not should_compress_floors

					print("  - Found " + x["map_folder"] + y["encoded_filename"])
					file_dict.append({
						"name": x["name"] + y["name"],
						"pointer_table_index": y["index"],
						"file_index": x["map_index"],
						"source_file": x["map_folder"] + y["encoded_filename"],
						"do_not_extract": True,
						"do_not_compress": do_not_compress,
						"use_external_gzip": "use_external_gzip" in y and y["use_external_gzip"],
					})

	print("[3 / 8] - Extracting files from ROM")
	for x in file_dict:
		# N64Tex conversions do not need to be extracted to disk from ROM
		if "texture_format" in x:
			x["do_not_extract"] = True
			x["output_file"] = x["source_file"].replace(".png", "." + x["texture_format"])

		if not "output_file" in x:
			x["output_file"] = x["source_file"]

		# gzip.exe appends .gz to the filename, we'll do the same
		if "use_external_gzip" in x and x["use_external_gzip"]:
			x["output_file"] = x["output_file"] + ".gz"

		# If we're not extracting the file to disk, we're using a custom .bin that shoudn't be deleted
		if "do_not_extract" in x and x["do_not_extract"]:
			x["do_not_delete_source"] = True

		# Extract the compressed file from ROM
		if not ("do_not_extract" in x and x["do_not_extract"]):
			byte_read = bytes()
			if "pointer_table_index" in x and "file_index" in x:
				file_info = getFileInfo(x["pointer_table_index"], x["file_index"])
				if file_info:
					x["start"] = file_info["new_absolute_address"]
					x["compressed_size"] = len(file_info["data"])

			fh.seek(x["start"])
			byte_read = fh.read(x["compressed_size"])

			if not ("do_not_delete_source" in x and x["do_not_delete_source"]):
				if os.path.exists(x["source_file"]):
					os.remove(x["source_file"])

				with open(x["source_file"], "wb") as fg:
					dec = byte_read if x.get("do_not_compress") and byte_read[:2] != b"\x1f\x8b" else zlib.decompress(byte_read, 15 + 32)
					fg.write(dec)

print("[4 / 8] - Patching Extracted Files")
for x in file_dict:
	if "patcher" in x and callable(x["patcher"]):
		print(" - Running patcher for " + x["source_file"])
		x["patcher"](x["source_file"])

with open(newROMName, "r+b") as fh:
	print("[5 / 8] - Writing patched files to ROM")
	for x in file_dict:
		if "texture_format" in x:
			if x["texture_format"] in ["rgba5551", "i4", "ia4", "i8", "ia8"]:
				converter = ["./build/n64tex.exe"] if os.name == "nt" else [sys.executable, "build/n64tex.py"]
				subprocess.run(converter + [x["texture_format"], x["source_file"]], check=True)
			else:
				print(" - ERROR: Unsupported texture format " + x["texture_format"])

		if "use_external_gzip" in x and x["use_external_gzip"]:
			if os.path.exists(x["source_file"]):
				# Legacy gzip 1.2.4 has no -k; retain the input using -c.
				with open(x["output_file"], "wb") as compressed:
					subprocess.run([GZIP, "-n", "-q", "-9", "-c", x["source_file"]], stdout=compressed, check=True)
				if os.path.exists(x["output_file"]):
					with open(x["output_file"], "r+b") as outputFile:
						# Chop off gzip footer
						outputFile.truncate(len(outputFile.read()) - 8)

		if os.path.exists(x["output_file"]):
			byte_read = bytes()
			uncompressed_size = 0
			with open(x["output_file"], "rb") as fg:
				byte_read = fg.read()
				uncompressed_size = len(byte_read)

			if "do_not_compress" in x and x["do_not_compress"]:
				compress = bytearray(byte_read)
			elif "use_external_gzip" in x and x["use_external_gzip"]:
				compress = bytearray(byte_read)
			elif "use_zlib" in x and x["use_zlib"]:
				compressor = zlib.compressobj(zlib.Z_BEST_COMPRESSION, zlib.DEFLATED, 25)
				compress = compressor.compress(byte_read)
				compress += compressor.flush()
				compress = bytearray(compress)
				# Zero out timestamp in gzip header to make builds deterministic
				compress[4] = 0
				compress[5] = 0
				compress[6] = 0
				compress[7] = 0
				# They used "Unix" as their Operating System ID, let's do the same
				compress[9] = 3
			else:
				compress = bytearray(gzip.compress(byte_read, compresslevel=9))
				# Zero out timestamp in gzip header to make builds deterministic
				compress[4] = 0
				compress[5] = 0
				compress[6] = 0
				compress[7] = 0
				# They used "Unix" as their Operating System ID, let's do the same
				compress[9] = 3

			print(" - Writing " + x["output_file"] + " (" + hex(len(compress)) + ") to ROM")
			if "pointer_table_index" in x and "file_index" in x:
				# More complicated write, update the pointer tables to point to the new data
				replaceROMFile(x["pointer_table_index"], x["file_index"], compress, uncompressed_size, x["output_file"])
			elif "start" in x:
				if isROMAddressOverlay(x["start"]):
					replaceOverlayData(x["start"], compress)
				else:
					# Simply write the bytes at the absolute address in ROM specified by x["start"]
					fh.seek(x["start"])
					fh.write(compress)
			else:
				print("  - WARNING: Can't find address information in file_dict entry to write " + x["output_file"] + " (" + hex(len(compress)) + ") to ROM")
		else:
			print(x["output_file"] + " does not exist")

		# Cleanup temporary files
		if not ("do_not_delete" in x and x["do_not_delete"]):
			if not ("do_not_delete_output" in x and x["do_not_delete_output"]):
				if os.path.exists(x["output_file"]) and x["output_file"] != x["source_file"]:
					os.remove(x["output_file"])
			if not ("do_not_delete_source" in x and x["do_not_delete_source"]):
				if os.path.exists(x["source_file"]):
					os.remove(x["source_file"])

	print("[6 / 8] - Writing recomputed pointer tables to ROM")
	writeModifiedPointerTablesToROM(fh)
	writeModifiedOverlaysToROM(fh)

	print("[7 / 8] - Dumping details of all pointer tables to rom/pointer_tables_modified.log")
	dumpPointerTableDetails("rom/pointer_tables_modified.log", fh)

# For compatibility with real hardware, the ROM size needs to be aligned to 0x10 bytes
with open(newROMName, "r+b") as fh:
    to_add = len(fh.read()) % 0x10
    if to_add > 0:
        to_add = 0x10 - to_add
        for x in range(to_add):
            fh.write(bytes([0]))

print("[8 / 8] - Generating BizHawk RAM watch")
import generate_watch_file

# Write custom ASM code to ROM
subprocess.run([ARMIPS, "asm/main.asm", "-definelabel", "RECRUITMENT_QA", str(int(RECRUITMENT_QA)), "-strequ", "OUTPUT_ROM", newROMName,
                "-sym", newROMName.replace(".z64", ".sym")], check=True)
if os.path.getsize(newROMName) > 64 * 1024 * 1024:
	raise SystemExit("Unexpected ROM size; check assembler ROM/RDRAM address mappings")

# Embed the supplied recording after all game pointer tables and resident code.
from scream_asset import appendScream
appendScream(newROMName)
appendBarrelAssets(newROMName)
from recruitment_room import patch_native_aliases
patch_native_aliases(newROMName)
from mirror_assets import appendMirrorAssets
appendMirrorAssets(newROMName)
from recruitment_pause import append_rotation_assets
append_rotation_assets(newROMName)

# Flashcart loader transfer padding (libdragon n64tool uses 16 KiB).
# Append only: retain every existing code/asset byte and pointer address.
with open(newROMName, "ab") as fh:
    fh.write(bytes((-fh.tell()) % 0x4000))

# Advertise 16-Kbit EEPROM through the Advanced Homebrew ROM Header.
# A modified ROM is absent from emulator ROM databases; Mupen64Plus-Next
# otherwise defaults it to 4-Kbit EEPROM. Keep the USA region, IPL3 and all
# code/assets intact. ED + the high version nibble is also understood by
# compatible flashcart loaders. Older emulators still need an explicit type.
with open(newROMName, "r+b") as fh:
    fh.seek(0x3C)
    fh.write(b"ED")
    fh.seek(0x3F)
    version = fh.read(1)[0]
    fh.seek(0x3F)
    fh.write(bytes([(version & 0x0F) | 0x20]))

# Fix CRC
from n64crc import fixCRC
fixCRC(newROMName)

# Remove temporary .o files
shutil.rmtree('obj')

end_time = time.time()
with open(newROMName, "rb") as fh:
	print()
	print("Built " + newROMName + " in " + str(round(end_time - start_time, 3)) + " seconds")
	print("SHA1: " + hashlib.sha1(fh.read()).hexdigest().upper())
