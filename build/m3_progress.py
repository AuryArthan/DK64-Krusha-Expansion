"""Scoped M3 native shop adapters; retain five-character stock tables."""
def patch_shop(fh,symbols):
    def patch(a,expected,words):
        fh.seek(a-0x80024000)
        expected=bytes.fromhex(expected)
        assert fh.read(len(expected))==expected, f'M3 shop differs at {a:X}'
        fh.seek(a-0x80024000)
        for word in words:fh.write(word.to_bytes(4,'big'))
    def target(name,op):return op | ((int(symbols[name],16)&0xFFFFFFF)>>2)
    for a,name,expected in [(0x80025E04,'m3shoppurchase','27bdffe0afa40020'),
                            (0x80027028,'m3shopcontrol','27bdffe000803825')]:
        patch(a,expected,[target(name,0x08000000),0])
    patch(0x800269D0,'0c18539e',[target('m3shopanimation',0x0C000000)])
    patch(0x80027C78,'0c1c39d4',[target('m3purchasetext',0x0C000000)])

def patch_pickups(fh,symbols):
    base=0x805FB300
    fh.seek(0x806F7498-base)
    assert fh.read(8)==bytes.fromhex('8662000c50400005'), 'Blueprint actor owner differs'
    fh.seek(0x806F7498-base)
    fh.write((0x08000000|((int(symbols['m3blueprintowner'],16)&0xFFFFFFF)>>2)).to_bytes(4,'big')+bytes(4))
    # Actor drops become model2 items in a later global collection pass, not
    # inside the actor's own bounce/draw callback. Scope both conversion calls
    # to the private actor selected by the owner bridge. All originals retain
    # their native types/flags and the original42-row actor scan.
    for native,name in [(0x80632630,'m3spawnphysical'),(0x806F50C8,'m3registerphysical')]:
        call=0x0C000000|((native&0xFFFFFFF)>>2)
        hits=[]
        for address in range(0x806F73A0,0x806F79A8,4):
            fh.seek(address-base)
            if int.from_bytes(fh.read(4),'big')==call:hits.append(address)
        assert len(hits)==1,(name,hits)
        fh.seek(hits[0]-base)
        fh.write((0x0C000000|((int(symbols[name],16)&0xFFFFFFF)>>2)).to_bytes(4,'big'))
