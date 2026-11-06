"""Gray ownership palette for M1 pause icons, preserving animation and alpha."""
from character_colors import identity_color

def owned_icon_payloads(rom, read_file):
    gray = identity_color()[0]
    result=[]
    for table, first, pixels in [(7,0xA8,44*44),(7,0xE0,48*42),(25,0x15F8,48*42)]:
        for index in range(first,first+8):
            native=read_file(rom,table,index)
            assert pixels*2 <= len(native) <= 4096 and len(native)%2 == 0, (table,index,len(native))
            out=bytearray()
            for offset in range(0,len(native),2):
                value=int.from_bytes(native[offset:offset+2],'big')
                r,g,b=(value>>11)&31,(value>>6)&31,(value>>1)&31
                # Native yellow's luminance is .9278 of white. Normalize it
                # before tinting so silver bananas retain their intended value.
                light=min(31,round((.2126*r+.7152*g+.0722*b)*gray/(255*.9278)))
                packed=light<<11 | light<<6 | light<<1 | value&1
                out.extend(packed.to_bytes(2,'big'))
            result.append(bytes(out))
    return result
