"""Native Snide board/NPC consumers only; never change shared flag strides."""

def blueprint_payload(rom, read_file):
    native=read_file(rom,14,0xA3)
    assert len(native)==240*150//2
    # Preserve the full schematic, repartitioning it into six rows. Native
    # per-cell topology/tile dimensions stay 30x30; no sixth-row UV overread.
    stride=240//2
    rows=[native[(y*150//180)*stride:(y*150//180+1)*stride] for y in range(180)]
    # RDP load-tile endpoints are inclusive. Pad the bottom edge so the
    # final tile's border taps stay inside this allocation.
    return b''.join(rows + [rows[-1],rows[-1]])

def patchSnide(fh,symbols):
    base=0x80024000
    def word(a):
        fh.seek(a-base);return int.from_bytes(fh.read(4),'big')
    def patch(a,expected,new):
        assert word(a)==expected, f'Snide instruction differs at {a:X}'
        fh.seek(a-base);fh.write(new.to_bytes(4,'big'))
    def call(a,target,name):
        patch(a,0x0C000000|((target&0xFFFFFFF)>>2),
              0x0C000000|((int(symbols[name],16)&0xFFFFFFF)>>2))
    patch(0x80024F8C,0x24041400,0x24041800)  # 48 cells * 8 vertices * 16 bytes
    call(0x80024FA4,0x80731AA8,'krushasnideboardcomplete')
    call(0x80024CF0,0x80731AA8,'krushasnidechoicecount')
    calls={0x807319D8:'krushapauseflagindex',0x80731A04:'krushapauseflagrange',
           0x8073110C:'krushapausecheckflag',0x8073129C:'krushasnidesetflag'}
    for a in range(0x800240BC,0x80024EF0,4):
        value=word(a)
        for target,name in calls.items():
            if value==0x0C000000|((target&0xFFFFFFF)>>2):call(a,target,name)
    # One bonus-access loop; do not falsify the board's native flags.
    a=0x80024980;fh.seek(a-base)
    expected=0x0C000000|((int(symbols['krushapausecheckflag'],16)&0xFFFFFFF)>>2)
    patch(a,expected,0x0C000000|((int(symbols['krushasnidebonusflag'],16)&0xFFFFFFF)>>2))
    call(0x80025494,0x807319D8,'krushapauseflagindex')
    call(0x800254A8,0x8073110C,'krushapausecheckflag')
    for a,expected in [(0x800256A0,0x28610096),(0x800259E8,0x24041400),
                       (0x80025430,0x240400A3)]:
        assert word(a)==expected
