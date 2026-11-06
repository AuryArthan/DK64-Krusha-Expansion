"""Verified USA pause callsites; keep native arrays and flag strides intact."""

def patchPause(fh, symbols):
    base = 0x805FB300

    def word(address):
        fh.seek(address-base)
        return int.from_bytes(fh.read(4), 'big')

    def patch(address, expected, value):
        assert word(address) == expected, f'Pause instruction differs at {address:X}'
        fh.seek(address-base)
        fh.write(value.to_bytes(4, 'big'))

    def pointer(high, low, expected_address, name):
        h, l = word(high), word(low)
        assert h >> 26 == 15, f'Expected pause LUI at {high:X}'
        signed = (l & 0xFFFF) - (0x10000 if l & 0x8000 else 0)
        assert ((h & 0xFFFF) << 16) + signed == expected_address
        target = int(symbols[name], 16)
        patch(high, h, h & 0xFFFF0000 | ((target + 0x8000) >> 16 & 0xFFFF))
        patch(low, l, l & 0xFFFF0000 | (target & 0xFFFF))

    for high, low in [(0x806A842C,0x806A8448), (0x806A8A4C,0x806A8A58),
                      (0x806AABE0,0x806AAC04), (0x806AAE40,0x806AAE44)]:
        pointer(high,low,0x807505A4,'krushapauseangles')
    for high, low in [(0x806A8AB8,0x806A8ABC),(0x806A8B28,0x806A8B2C),
                      (0x806AA9F4,0x806AA9F8),(0x806A9BD0,0x806A9C1C)]:
        pointer(high,low,0x80750530,'krushapauseunlocked')
    pointer(0x806AAA1C,0x806AAA28,0x80750518,'krushapausefaces')
    pointer(0x806A9A5C,0x806A9A68,0x807FC840,'krushapausex')
    pointer(0x806A9BA8,0x806A9C14,0x807FC868,'krushapausey')
    pointer(0x806A9BAC,0x806A9BC4,0x807FC890,'krushapausescale')

    patch(0x806A9B14,0x0019A080,0x08000000 | (int(symbols['krushapauseringstride'],16)&0xFFFFFFF)>>2)
    patch(0x806A9B78,0x46140202,0x08000000 | (int(symbols['krushapauseringy'],16)&0xFFFFFFF)>>2)
    # All earned area totals include hidden credit; visual face count alone
    # follows the option. Medal/blueprint readers are narrow pause wrappers.
    patch(0x806AACD8,0x2A010005,0x2A010006)
    patch(0x806A9E44,0x2A610005,0x2A610006)
    patch(0x806A9ED8,0x24070019,0x2407001E)
    patch(0x806AAB0C,0x2A010005,0x2A010006)
    calls = {0x807319D8:'krushapauseflagindex',0x80731A04:'krushapauseflagrange',
             0x8073110C:'krushapausecheckflag'}
    for address in range(0x806AA310,0x806AB4EC,4):
        value=word(address)
        for target,name in calls.items():
            expected=0x0C000000 | (target & 0xFFFFFFF)>>2
            if value==expected:
                patch(address,expected,0x0C000000 | (int(symbols[name],16)&0xFFFFFFF)>>2)

    # The new mode10 wrapper owns portrait layout, then invokes mode16 for
    # shared cleanup. This native ten-entry layout block is unreachable.
    # Keep ACA00 onward (shared page/fade exit), and every other mode intact.
    assert word(0x806AC954) == 0xC4E80008
    fh.seek(0x806AC954-base)
    fh.write(bytes(0x806ACA00-0x806AC954))

    patch(0x806ABB48,0x0C1AAEE6,0x0C000000 | (int(symbols['krushapausenametext'],16)&0xFFFFFFF)>>2)

    # These immediates change only when the option changes. Validate their
    # complete original words here as strictly as the static relocations.
    for address,expected in [
        (0x806A8AF0,0x28410005),(0x806A8B24,0x24040004),
        (0x806A8AEC,0x272CFCCD),(0x806A8B44,0x25F80333),
        (0x806AAA64,0x26060005),(0x806AAA94,0x24010005),
        (0x806A9AB8,0x3C014334),(0x806A9C20,0x2A610005),
        (0x806A9C44,0x26520333),(0x806AAF44,0x24010005),
    ]:
        assert word(address)==expected, f'Pause option instruction differs at {address:X}'
