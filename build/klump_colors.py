"""Rare-Klump appearance palettes, including reddish orange and pale blue.

The red-orange default uses pale-blue clothing and grenades. Explicit older
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
    'red-orange':(1.28,.48,.12),
}
GEAR={'original':None,'light-blue':(.48,.69,1.12),'pale-blue':(.80,1.03,1.40)}
# Optional third component caps saturation for a lighter, less vivid blue.
GRENADES={'original':None,'navy':(.625,.72),'crimson':(.99,.85),'pale-blue':(.605,1.10,.45)}

def choice(key,choices,default='original'):
    value=os.environ.get(key,default)
    if value not in choices:raise ValueError(f'{key} must be one of {tuple(choices)}')
    return value

def skin_choice():return choice('DK64_KLUMP_SKIN',SKINS,'red-orange')
def skin_multiplier():return SKINS[skin_choice()]
def gear_choice():return choice('DK64_KLUMP_GEAR',GEAR,'pale-blue' if skin_choice()=='red-orange' else 'light-blue' if skin_choice()=='umber-red' else 'original')
def gear_multiplier():return GEAR[gear_choice()]
def grenade_choice():return choice('DK64_KLUMP_GRENADES',GRENADES,'pale-blue' if skin_choice()=='red-orange' else 'original')

def prepare():
    skin=skin_choice();gear=gear_choice();grenade=grenade_choice()
    (ROOT/'include/klump_colors.generated.h').write_text(
        '/* Appearance: '+skin+' / '+gear+' / '+grenade+'. */\n'
        '#define M4_GRENADE_PREVIEW '+str(int(grenade!='original'))+'\n')
    print('Rare Klump appearance:',skin,'/',gear,'/',grenade)

def grenade_texture(raw,held=False):
    """Rehue peel while retaining native alpha, fuse/pin and mip geometry."""
    selected=GRENADES[grenade_choice()]
    if selected is None:return raw
    hue,value_scale=selected[:2];saturation_cap=selected[2] if len(selected)>2 else 1.0;out=bytearray()
    for (v,) in struct.iter_unpack('>H',raw):
        rgb=[(v>>shift&31)/31 for shift in (11,6,1)]
        h,s,l=colorsys.rgb_to_hsv(*rgb)
        if s>.25 and (held or h<.18 or h>.96):
            rgb=colorsys.hsv_to_rgb(hue,min(saturation_cap,s*1.1),min(1,l*value_scale))
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
    assert count>200,count
    return bytes(data)
