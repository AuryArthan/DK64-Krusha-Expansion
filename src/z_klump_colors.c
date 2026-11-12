#include "../include/common.h"
#include "../include/klump_colors.generated.h"

/* Compiled out when original grenades are selected. Recolor hooks are only
 * at the native thrown-orange and idle-snack initializer callsites. The
 * validated rare-grenade loop or rare-parent constructor scopes each call;
 * ordinary player/enemy oranges and the lime bazooka retain their own sprites.
 */
#if M4_GRENADE_PREVIEW
extern int m4EncounterKlump(void*);
u8 m4GrenadeVisualScope;
typedef struct {
    u32 id; u8 across,down,flags,codec; u32 rgba;
    u8 animated,table; u16 width,height,frames; u16 images[16];
} KlumpGrenadeSprite;
static const KlumpGrenadeSprite grenade={
    0x4B520142,1,1,0,2,0xFFFFFFFF,0,1,32,32,16,
    {7732,7733,7734,7735,7736,7737,7738,7739,
     7740,7741,7742,7743,7744,7745,7746,7747}
};
void m4GrenadeColor(u8 r,u8 g,u8 b,u8 a) {
    void (*native)(u8,u8,u8,u8)=(void*)0x807149C8;
    if (m4GrenadeVisualScope) r=g=b=255;
    native(r,g,b,a);
}
void* m4GrenadeSprite(const void* sprite,f32 scale,void* actor,s32 bone,u8 mode) {
    void* (*native)(const void*,f32,void*,s32,u8)=(void*)0x80714C08;
    if (m4GrenadeVisualScope) sprite=&grenade;
    return native(sprite,scale,actor,bone,mode);
}

/* The snack is a native idle-particle actor, not a thrown actor50 or a belt
 * texture. Retain its native attachment, parent UID and deletion lifecycle;
 * scope only the constructor's color/sprite calls to the rare parent. */
void m4EncounterIdleParticle(void* parent) {
    void (*native)(void*)=(void*)0x806192A4;
    u8 previous=m4GrenadeVisualScope;
    m4GrenadeVisualScope=krushaEnabled() && DetectAdventure() && m4EncounterKlump(parent);
    native(parent);
    m4GrenadeVisualScope=previous;
}
/* Keep the native grenade's80690C60 call and NULL argument untouched. A
 * non-NULL sprite there enters player-only homing/camera logic; enemy actors
 * do not have that player data. Recoloring needs no trail/homing change. */
#endif
