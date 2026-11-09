"""Private lime bazooka frames; original orange grenades remain byte-identical."""
import colorsys, struct
from barrel_assets import read_file

def payloads(rom):
    frames=[]
    for index in range(0x14F6,0x1506):
        assert not read_file(rom,25,7700+index-0x14F6)
        out=bytearray()
        for (v,) in struct.iter_unpack('>H',read_file(rom,25,index)):
            r,g,b=(v>>11&31)/31,(v>>6&31)/31,(v>>1&31)/31
            h,s,l=colorsys.rgb_to_hsv(r,g,b)
            # Rehue only the orange peel; retain the fuse, pin and highlights.
            if s>.25 and (h<.18 or h>.96):
                r,g,b=colorsys.hsv_to_rgb(.23,s,l)
            rgb=[min(31,max(0,round(c*31))) for c in (r,g,b)]
            out+=struct.pack('>H',rgb[0]<<11|rgb[1]<<6|rgb[2]<<1|v&1)
        frames.append(bytes(out))
    # A private visual Model2. The crate still registers native pineapple
    # collection metadata, so eligibility, shared ammo and homing conversion
    # keep their existing rules. Never replace Chunky's shared model file.
    assert not read_file(rom,4,49) and not read_file(rom,4,56)
    for mid in range(216):
        setup=read_file(rom,9,mid)
        if setup: assert all(struct.unpack_from('>H',setup,4+i*48+40)[0] not in (49,56) for i in range(struct.unpack_from('>I',setup)[0]))
    model=bytearray(read_file(rom,4,0x56))
    assert len(model)==340
    struct.pack_into('>I',model,0x9C,7700)
    struct.pack_into('>I',model,0xA8,16)
    struct.pack_into('>H',model,0x124,7700)
    for i in range(15): struct.pack_into('>I',model,0xAC+i*4,7701+i)
    # A homing crate uses the same red modulation as the scoped HUD tint.
    # Bake it into private frames so the five transient native drops retain
    # their appearance independently of later character tags or crate bursts.
    red=[]
    for frame in frames:
        data=bytearray()
        for (v,) in struct.iter_unpack('>H',frame):
            data+=struct.pack('>H',(v&0xF801)|(round((v>>6&31)*150/255)<<6)|(round((v>>1&31)*150/255)<<1))
        red.append(bytes(data))
    red_model=bytearray(model)
    struct.pack_into('>I',red_model,0x9C,7716)
    struct.pack_into('>H',red_model,0x124,7716)
    for i in range(15):struct.pack_into('>I',red_model,0xAC+i*4,7717+i)
    return frames+[bytes(model)]+red+[bytes(red_model)]

def patch_code(fh,symbols):
    # Only the dedicated orange-gun initialization/trail and HUD homing tint.
    for address,target,name in [(0x80694A7C,0x80714C08,'krushaammoprojectile'),
                                (0x80694BA8,0x80690C60,'krushaammotrail'),
                                (0x806F97D0,0x807149C8,'krushaammohomingtint'),
                                (0x806F5B80,0x80632630,'krushaammocratedrop'),
                                (0x806F6488,0x806F5A48,'krushaammocrateburst')]:
        fh.seek(address-0x805FB300)
        assert int.from_bytes(fh.read(4),'big')==0x0C000000|((target&0xFFFFFFF)>>2)
        fh.seek(address-0x805FB300)
        fh.write((0x0C000000|((int(symbols[name],16)&0xFFFFFFF)>>2)).to_bytes(4,'big'))
