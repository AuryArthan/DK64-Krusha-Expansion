"""Rare-Klump appearance palettes, including royal blue and red grenades.

The red-orange default uses steel-gray belly armor with green edges, royal-blue helmet and pouches and red grenades. Explicit older
skin presets retain their previous clothing and original grenades unless
overridden. These are build selectors, not gameplay options.
"""
from pathlib import Path
import colorsys,json,os,struct

ROOT=Path(__file__).resolve().parents[1]
SKINS={
    'original':None,
    'ochre':(1.00,.78,.26),
    'umber':(1.00,.58,.18),
    'olive':(.86,.76,.26),
    'umber-red':(1.00,.51,.22),
    'red-orange':(1.42,.31,.15),
}
GEAR={'original':None,'light-blue':(.48,.69,1.12),'pale-blue':(.80,1.03,1.40),'royal-blue':(.44,.71,1.52)}
# Optional third component caps saturation for a lighter, less vivid blue.
GRENADES={'original':None,'navy':(.625,.72),'crimson':(.99,.85),'pale-blue':(.605,1.10,.45),'red-orange':(.045,1.10,.95),'red':(0.0,.84,1.0)}

def choice(key,choices,default='original'):
    value=os.environ.get(key,default)
    if value not in choices:raise ValueError(f'{key} must be one of {tuple(choices)}')
    return value

def skin_choice():return choice('DK64_KLUMP_SKIN',SKINS,'red-orange')
def skin_multiplier():return SKINS[skin_choice()]
def gear_choice():return choice('DK64_KLUMP_GEAR',GEAR,'royal-blue' if skin_choice()=='red-orange' else 'light-blue' if skin_choice()=='umber-red' else 'original')
def gear_multiplier():return GEAR[gear_choice()]
def grenade_choice():return choice('DK64_KLUMP_GRENADES',GRENADES,'red' if skin_choice()=='red-orange' else 'original')

def prepare():
    skin=skin_choice();gear=gear_choice();grenade=grenade_choice()
    (ROOT/'include/klump_colors.generated.h').write_text(
        '/* Appearance: '+skin+' / '+gear+' / '+grenade+'. */\n'
        '#define M4_GRENADE_PREVIEW '+str(int(grenade!='original'))+'\n')
    print('Rare Klump appearance:',skin,'/',gear,'/',grenade)

def grenade_texture(raw):
    """Rehue peel while retaining native alpha, fuse/pin and mip geometry."""
    palette=grenade_choice()
    selected=GRENADES[palette]
    if selected is None:return raw
    hue,value_scale=selected[:2];saturation_cap=selected[2] if len(selected)>2 else 1.0;out=bytearray()
    for (v,) in struct.iter_unpack('>H',raw):
        rgb=[(v>>shift&31)/31 for shift in (11,6,1)]
        h,s,l=colorsys.rgb_to_hsv(*rgb)
        if s>.25 and (h<.18 or h>.96):
            rgb=colorsys.hsv_to_rgb(hue,min(saturation_cap,s*1.1),min(1,l*value_scale))
            if palette=='red':
                red=min(1,rgb[0]+.5*rgb[1])
                # Only the native glint rises above the normal peel red.
                # Lift it toward white equally in green and blue to keep its red hue.
                highlight=.30*max(0,red-value_scale)/(1-value_scale)
                rgb=(red+(1-red)*highlight,highlight,highlight)
        elif palette=='red':
            # The native pin has a few yellow-gray pixels. Neutral metal
            # keeps its filtered edge from adding warmth to the red peel.
            gray=.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
            rgb=(gray,gray,gray)
        r,g,b=[max(0,min(31,round(c*31))) for c in rgb]
        out+=struct.pack('>H',r<<11|g<<6|b<<1|v&1)
    return bytes(out)

def grenade_payloads(rom,read_file):
    if grenade_choice()=='original':return []
    assert all(not read_file(rom,25,i) for i in range(7732,7748))
    return [grenade_texture(read_file(rom,25,i)) for i in range(0x14F6,0x1506)]

def recolor_model_skin(raw):
    """The pink prelit skin is vertex RGB; keep geometry and other materials.

    Texture recoloring alone misses these untextured body panels. The native
    vertex block starts at0x28; its end follows the model's display-list header.
    Pink hue selection excludes brown gear, red mouth, teeth and purple eyes.
    """
    color=skin_multiplier()
    if color is None:return raw
    data=bytearray(raw);base,endptr=struct.unpack_from('>II',raw)
    end=0x28+endptr-base;start=0x28+struct.unpack_from('>I',raw,end)[0]-base
    assert start>=0x28 and (start-0x28)%16==0
    count=0
    for offset in range(0x28,start,16):
        r,g,b,a=data[offset+12:offset+16];h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
        if .87<h<.995 and r>g*1.35 and (b>g*1.25 or (r,g,b)==(230,107,120)):
            light=max(r,g,b)*.8
            data[offset+12:offset+15]=bytes(max(0,min(255,round(light*c))) for c in color)
            count+=1
    if skin_choice()=='red-orange':
        # Model 57 has separate fangs, eye whites and textured eye fronts.
        # Tint their native shading so the purple iris still shows through.
        for first, stop in ((13, 29), (91, 96), (100, 105), (166, 176)):
            for vertex in range(first, stop):
                offset = 0x28 + 16 * vertex + 12
                r, g, b = raw[offset:offset + 3]
                assert r == g == b
                data[offset:offset + 3] = bytes((r, round(g * .94), round(b * .42)))
        # Model 57 uses these private vertices exclusively for the two torso
        # panels (104D/1058) and their side strips (1059). Remove the baked
        # orange lighting from the metal while retaining the sculpted shadows.
        for first,stop in ((198,236),(246,259),(261,276),(280,284)):
            for vertex in range(first,stop):
                offset=0x28+16*vertex+12
                r,g,b=raw[offset:offset+3]
                gray=round(.50*r+.40*g+.10*b)
                data[offset:offset+3]=bytes((gray,gray,gray))
    assert count>200,count
    return bytes(data)


def armored_belly(raw, front_panel):
    # Private torso textures use RGBA5551 with 8-byte-aligned rows per mip.
    width,height=(32,32) if front_panel else (16,8)
    out=bytearray(raw)
    offset=0
    while width:
        stride=max(4,width)*2
        for y in range(height):
            # Color follows the horizontal plate lips around the torso. The
            # two front panels share a vertical UV seam through the middle.
            # Average the finish at each mip level to keep thin rims stable.
            base_height = 32 if front_panel else 8
            span = base_height // height
            bevel = 0.0
            patina = 0.0
            for row in range(y * span, (y + 1) * span):
                edge = min(row, base_height - 1 - row)
                rim = max(0.0, 1.0 - edge / (3 if front_panel else 2))
                if front_panel and row in (9, 20):
                    bevel += 3.0
                if front_panel and row in (10, 21):
                    bevel -= 5.0
                    rim = max(rim, 0.58)
                patina += rim
            bevel /= span
            patina /= span
            steel = (0.86, 1.00, 1.11)
            green = (0.68, 1.04, 0.78)
            tint = [a + (b - a) * patina for a, b in zip(steel, green)]
            for x in range(width):
                pos=offset+y*stride+x*2
                word=struct.unpack_from('>H',raw,pos)[0]
                r,g,b=(word>>shift&31 for shift in (11,6,1))
                light=.2126*r+.7152*g+.0722*b
                shade=max(0,3.5+.96*light+bevel)
                rgb=[min(31,round(shade*k)) for k in tint]
                struct.pack_into('>H',out,pos,rgb[0]<<11|rgb[1]<<6|rgb[2]<<1|word&1)
        offset+=stride*height
        width//=2
        height=max(1,height//2)
    assert offset==len(raw),(offset,len(raw))
    return bytes(out)
