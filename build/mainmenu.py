def patchMainMenu(filename):
	with open(filename, "r+b") as fh:
		fh.seek(0x70E)
		fh.write("SPEED MODE".encode("ascii")) # Originally: STORY SKIP

def patchDolbyText(filename):
	# Rebuild the native two-textbox resource with correct lengths/offsets.
	# Derive all offsets from the strings instead of the old fixed fields.
	import struct
	from pathlib import Path
	lines = [b"WITH HELP FROM: TAG-ANYWHERE, DONKVIEWER,",
	         b"DK64 DECOMP, RECOMP, RANDOMIZER; AND CODEX"]
	header = bytearray([len(lines)])
	offset = 0
	for line in lines:
		header += bytes([1, 1, 1]) + struct.pack('>IH', offset, len(line)) + bytes(6)
		offset += len(line)
	Path(filename).write_bytes(header + struct.pack('>H', offset) + b''.join(lines))
