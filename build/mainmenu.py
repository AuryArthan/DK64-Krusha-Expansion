def patchMainMenu(filename):
	with open(filename, "r+b") as fh:
		fh.seek(0x70E)
		fh.write("SPEED MODE".encode("ascii")) # Originally: STORY SKIP

def patchDolbyText(filename):
	# Rebuild the native three-textbox resource with correct lengths/offsets.
	# The new second line is longer than the old fixed 33-byte field.
	import struct
	from pathlib import Path
	lines = [b"WITH THE HELP FROM: TAG-ANYWHERE TOOLS,",
	         b"DK64 DECOMPILATION AND RANDOMIZER, DK64 RECOMPILED,",
	         b"DK64 REVERSE ENGINEERED AND DONKVIEWER"]
	header = bytearray([len(lines)])
	offset = 0
	for line in lines:
		header += bytes([1, 1, 1]) + struct.pack('>IH', offset, len(line)) + bytes(6)
		offset += len(line)
	Path(filename).write_bytes(header + struct.pack('>H', offset) + b''.join(lines))
