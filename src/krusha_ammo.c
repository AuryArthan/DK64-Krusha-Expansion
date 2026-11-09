#include "../include/common.h"

typedef struct {
    u32 id; u8 across,down,flags,codec; u32 rgba;
    u8 animated,table; u16 width,height,frames; u16 images[16];
} AmmoSprite;
static const AmmoSprite lime = {
    0x4B520140,1,1,0,2,0xFFFFFFFF,0,1,32,32,16,
    {7700,7701,7702,7703,7704,7705,7706,7707,
     7708,7709,7710,7711,7712,7713,7714,7715}
};
const void* krushaAmmoSprite(void) { return &lime; }
/* A stationary upright frame for the cage. The moving round deliberately
 * tumbles through all sixteen frames; frame zero shows its pin below it. */
static const AmmoSprite cage_hint = {
    0x4B520141,1,1,0,2,0xFFFFFFFF,0,1,32,32,1,{7710}
};
const void* krushaCageHintSprite(void) { return &cage_hint; }

static u8 homing_crate;
void krushaAmmoCrateBurst(u8 player,s16 id,void* actor,u16 crate) {
    void (*native)(u8,s16,void*,u16)=(void*)0x806F5A48;
    u8 previous=homing_crate;
    homing_crate=crate==0x11;
    native(player,id,actor,crate);
    homing_crate=previous;
}

s32 krushaAmmoCrateDrop(s16 type,f32 x,f32 y,f32 z,f32 angle,u8 mode) {
    s32 (*native)(s16,f32,f32,f32,f32,u8)=(void*)0x80632630;
    if (krushaEnabled() && DetectAdventure() && Character==5 && type==0x15F) type=homing_crate ? 56 : 49;
    return native(type,x,y,z,angle,mode);
}

void* krushaAmmoProjectile(const void* sprite,f32 scale,void* actor,s32 bone,u8 mode) {
    void* (*native)(const void*,f32,void*,s32,u8)=(void*)0x80714C08;
    if (krushaEnabled() && DetectAdventure()) sprite=&lime;
    return native(sprite,scale,actor,bone,mode);
}
void krushaAmmoTrail(u16 kind,void* actor,const void* sprite,u8 mode) {
    void (*native)(u16,void*,const void*,u8)=(void*)0x80690C60;
    if (krushaEnabled() && DetectAdventure()) sprite=&lime;
    native(kind,actor,sprite,mode);
}
void krushaAmmoHomingTint(u8 r,u8 g,u8 b,u8 a) {
    void (*native)(u8,u8,u8,u8)=(void*)0x807149C8;
    /* Native HUD item3 uses pure red modulation. Keep a red accent but
     * enough green to identify the lime round. No homing mechanics change. */
    if (krushaEnabled() && DetectAdventure() && Character==5) {g=150;b=150;}
    native(r,g,b,a);
}
