#include "../include/common.h"
#include "../include/krusha_progress.h"
#include "../include/m3_progress.h"
#include "../include/krusha_recruitment.h"
#include "../include/m2_pickups.generated.h"
#include "../include/recruitment_assets.generated.h"
extern int m4SetupHidden(s32,s32);

/* Only the setup constructor's permanent-object predicate calls this wrapper.
 * The original pickup ordering/counts are unchanged, as are cached map files. */
s32 m2SetupHidden(s32 map, s32 object_id) {
    if (map==34 && object_id==RECRUITMENT_OBJECT_ID) return !krushaEnabled() || !DetectAdventure();
    int private=m4SetupHidden(map,object_id);
    if (private>=0) return private;
    s32 (*nativeHidden)(s32,s32) = (void*)0x807315D4;
    for (s32 i=0;i<sizeof(m2Pickups)/sizeof(m2Pickups[0]);i++) {
        if (map!=m2Pickups[i].map || object_id != m2Pickups[i].object_id) continue;
        if (!krushaCampaignAvailable()) return 1;
        return krushaProgressRead(*(u8*)0x807467C8,m2Pickups[i].slot,1);
    }
    return nativeHidden(map,object_id);
}

/* Native ownership/range/action tests run before this contact predicate. Native
 * suction/despawn run afterward. The original flag index is -1 for private types;
 * only this registry can award them, once, to the independent sixth wallet. */
static s32 m2Award(u16 slot,u8 units,u8 coin,u8 world) {
        if (!krushaCampaignAvailable() || Character!=5) return 0;
        u8 file=*(u8*)0x807467C8;
        if (krushaProgressRead(file,slot,1)) return 0;
        s32 before=krushaProgressBananas(file,world);
        krushaProgressWrite(file,slot,1,1);
        if (coin) {
            if (MovesBase[5].coins < 255) MovesBase[5].coins++;
            playSong(23,1.0f);
        } else {
            s32 total=before+units;
            MovesBase[5].cb_count[world]=total-MovesBase[5].tns_cb_count[world];
            playSound(0x2A0,0x7FFF,63.0f,1.0f,0,0);
            if (before<50 && total>=50) playSong(172,1.0f);
        }
        void (*refresh)(s32,u8,s32)=(void*)0x806F8BC4;
        if (Character == 5) refresh(coin ? 1 : 0,0,0);
        return 1;
}

volatile u32 m2ContactTrace[6] = {0,0,0,0,0,0};
s32 m2PickupAllowed(s16 object_id,u8 player,u16 type) {
    m2ContactTrace[0]++; m2ContactTrace[1]=object_id; m2ContactTrace[2]=type;
    if (type != 2 && type != 4 && type != 6) return -1;
    m2ContactTrace[3]++;
    s16 (*setupId)(s16)=(void*)0x8063D990;
    object_id=setupId(object_id);
    if (!krushaCampaignAvailable() || Character != 5 || player) return 0;
    for (s32 i=0;i<sizeof(m2Pickups)/sizeof(m2Pickups[0]);i++) {
        if (CurrentMap!=m2Pickups[i].map || object_id != m2Pickups[i].object_id || type != m2Pickups[i].type) continue;
        m2ContactTrace[4]++;
        if (!m2Award(m2Pickups[i].slot,m2Pickups[i].units,m2Pickups[i].coin,m2Pickups[i].world)) return 0;
        m2ContactTrace[5]++;
        return 1;
    }
    return 0;
}

/* Match the same animated silver icons used by the pause pages. Item13 is
 * T&S's selected donor: preserve its independent selector rather than the
 * current player identity. */
extern void* m2NativeHUDSprite(u32 item);
extern const void* krushaPauseIcon(const void*);
extern const void* krushaOwnedIcon(int);
extern const void* krushaAmmoSprite(void);
void* m2HUDSprite(u32 item) {
    if (krushaEnabled() && DetectAdventure() && item==13 && *(u32*)0x80754288==5)
        return (void*)krushaOwnedIcon(0);
    if (krushaEnabled() && DetectAdventure() && Character == 5) {
        if (item == 2 || item == 3) return (void*)krushaAmmoSprite();
        if (item == 0) return (void*)krushaPauseIcon((void*)0);
        if (item == 1) return (void*)krushaPauseIcon((void*)1);
        if (item == 14) return (void*)krushaOwnedIcon(1);
        if (item == 12) return (void*)krushaOwnedIcon(2);
        /* Native price displays request sprite 20+character. 25 has no
         * vanilla descriptor and crashes the sprite allocator on entry. */
        if (item == 7) return (void*)m3ShoutIcon();
        if (item == 25) return (void*)m3FaceIcon();
    }
    return m2NativeHUDSprite(item);
}

/* Extend the native billboard ownership fade without changing collection IDs.
 * The renderer supplies the distance-faded alpha and opaque-pass flag afresh
 * each draw. Match its non-owner cap100 and preserve any lower distance alpha.
 * Native logic remains in charge of every original item and menu/MP context. */
void m2PickupOpacity(s16 type,u8* opaque,s16* alpha) {
    void (*nativeOpacity)(s16,u8*,s16*)=(void*)0x806392BC;
    if (krushaEnabled() && DetectAdventure() &&
        (type == 2 || type == 4 || type == 6 || type == 7)) {
        /* Cached maps can retain a model2 after eligibility changes. Its
         * contact path is gated separately; never expose a retained colored
         * pickup while locked. Blueprints follow native visible-drop rules. */
        if (type!=7 && !krushaCampaignAvailable()) {
            *opaque=0;*alpha=0;return;
        }
        u8* changes=*(u8**)0x807FC924;
        u8 viewport=*(u8*)0x807FC929;
        u8* actor=(changes && viewport < 4) ? *(u8**)(changes+viewport*0x2F0+4) : 0;
        if (!actor || *(u32*)(actor+0x58) != 7) {
            *opaque=0;
            if (*alpha > 100) *alpha=100;
        }
        return;
    }
    nativeOpacity(type,opaque,alpha);
}

/* Reuse the native nonpersistent K.Rool balloon actor, with explicit private
 * spawner identities. It consumes no original permanent balloon flag. Routes,
 * collision volumes, sprite lifetime and actor cleanup remain native. */
typedef struct { u8 path,speed; s8 route; u8 pad; u16 angle; s16 flag; } M2BalloonData;
typedef struct {
    u32 id; u8 across,down,flags,codec; u32 rgba;
    u8 animated,table; u16 width,height,frames; u16 images[8];
} M2BalloonSprite;
static const M2BalloonSprite m2_balloon_sprite = {
    0x4B520110,1,1,0,2,0xFFFFFFFF,0,1,32,64,8,
    {7300,7301,7302,7303,7304,7305,7306,7307}
};

static s32 balloonIndex(u8* actor) {
    if (!actor || *(u32*)(actor+0x58) != 147) return -1;
    s16 (*spawnerId)(void*)=(void*)0x80688E68;
    s32 id=spawnerId(actor);
    for (s32 i=0;i<sizeof(m2Balloons)/sizeof(m2Balloons[0]);i++)
        if (CurrentMap==m2Balloons[i].map && id == m2Balloons[i].spawner_id) return i;
    return -1;
}

extern void m2NativeActorCollision(void*,void*);
static const u32 m2_balloon_collisions[] = {
    0x00AB0000,0x8074BF24, /* Native balloon gun-hit command, bazooka171 only. */
    0,0,
};
void m2ActorCollision(void* actor,void* collision) {
    const u32** entry=(void*)0x8074CA9C;
    if (balloonIndex(actor) < 0) {
        m2NativeActorCollision(actor,collision);
        return;
    }
    if (!krushaCampaignAvailable() || Character!=5) return;
    /* Single-threaded native dispatch consumes this pointer synchronously.
     * Restore it before any other actor is processed, including boss balloons. */
    const u32* saved=*entry;
    *entry=m2_balloon_collisions;
    m2NativeActorCollision(actor,collision);
    *entry=saved;
}

extern void vanillaBananaBalloon(void*);
extern void krushaNativeActorDelete(void*);
s32 m2Balloon(void* sprite) {
    u8* actor=*(u8**)0x807FBB40;
    s32 index=balloonIndex(actor);
    if (index < 0) return 0;
    u8 file=*(u8*)0x807467C8;
    if (!krushaCampaignAvailable() || krushaProgressRead(file,m2Balloons[index].slot,1)) {
        krushaNativeActorDelete(actor);
        return 1;
    }
    if (!(*(u32*)(actor+0x60)&0x10)) {
        vanillaBananaBalloon((void*)&m2_balloon_sprite);
        return 1;
    }
    M2BalloonData* data=*(M2BalloonData**)(actor+0x174);
    if (data->route != -1) {
        void (*advance)(s32,void*)=(void*)0x80723484;
        void (*position)(s32,f32*,f32*,f32*)=(void*)0x807238D4;
        advance(data->route,actor);
        position(data->route,(f32*)(actor+0x7C),(f32*)(actor+0x80),(f32*)(actor+0x84));
    }
    f32 (*sinAngle)(s16)=(void*)0x80612794;
    *(f32*)(actor+0x80)+=5.0f*sinAngle(data->angle);
    data->angle=(data->angle+0x50)&0xFFF;
    if (*(u32*)0x8076A068%24==0) {
        void (*begin)(u8)=(void*)0x807149B8;
        void (*callback)(void*)=(void*)0x8071498C;
        void (*duration)(s32)=(void*)0x80714950;
        void (*color)(u8,u8,u8,u8)=(void*)0x807149C8;
        void (*layer)(u8)=(void*)0x80714A28;
        void (*mode)(u8)=(void*)0x80714998;
        void* (*attach)(void*,f32,void*,s32,u8)=(void*)0x80714C08;
        begin(1);
        if (Character == 5) {
            callback((void*)0x8071EB70);
            duration(0x226);
        } else color(255,255,255,150);
        layer(4); mode(3);
        attach((void*)&m2_balloon_sprite,0.8f,actor,1,2);
        actor[0x144]=2;
    }
    if (Character==5 && *(u8*)0x807FBD70==4) {
        void (*pop)(void*)=(void*)0x80686CF8;
        pop(actor);
        playSound(0x2BF,0x7FFF,63.0f,1.0f,5,0);
        m2Award(m2Balloons[index].slot,10,0,m2Balloons[index].world);
        krushaNativeActorDelete(actor);
    }
    return 1;
}
