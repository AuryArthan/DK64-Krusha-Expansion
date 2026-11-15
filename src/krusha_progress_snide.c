#include "../include/common.h"
#include "../include/krusha_progress.h"
#include "../include/krusha_identity.h"
#include "../include/krusha_victory.generated.h"
#include "../include/krusha_recruitment.h"
#include "../include/krusha_prison_scene.h"

extern void vanillaSnideBoard(void);
extern Gfx* vanillaSnideDraw(Gfx*, void*);
extern int krushaPauseFlagRange(int,int,int,int);
extern void vanillaCharacterScript(void*,s32);
extern int m4VictoryActive(void);

void krushaSnideAnimation(void* actor, s32 script) {
    /* Both queued GB actions and cutscene-driven pickups start these native
     * Chunky/Krusha GB scripts. Substitute only Snide's player presentation,
     * at real script initialization, never while SetAction merely queues it. */
    if ((CurrentMap==15 || m4VictoryActive()) && krushaEnabled() && DetectAdventure() &&
        Character==5 && actor==(void*)Player && (script==0x1D2 || script==0x1D0)) {
        /* Stop momentum at the actual world victory initializer. A high-air
         * pickup that native code deliberately leaves playable must retain
         * its normal movement; the music callback alone is not a dance. */
        if (m4VictoryActive()) Player->hSpeed=0;
        script=script==0x1D2 ? 0x174 : 0x173;
    }
    vanillaCharacterScript(actor,script);
    krushaPrisonTinyAnimation(actor,script);
    if ((CurrentMap==15 || m4VictoryActive()) && krushaEnabled() && DetectAdventure() &&
        Character==5 && actor==(void*)Player && script==0x173) {
        u8* animation=*(u8**)((u8*)actor+4);
        *(const u8**)(animation+0x68)=krushaVictoryScript;
        *(const u8**)(animation+0x6C)=krushaVictoryScript;
        *(const u8**)0x807F5AF0=krushaVictoryScript;
    }
}

static unsigned int activeFile(void) { return *(volatile u8*)0x807467C8; }

int krushaSnideDisplayRewardReady(void) {
    if (!krushaRecruitmentPlayable() || Character!=5) return 0;
    /* The setup prop already sits near the doorway before its presentation.
     * Wait for the native hand-in phase, and require this visit to have held
     * blueprints. A repeat/no-blueprint visit must not collect the idle prop. */
    u32* actors=(u32*)0x807FB930;
    int count=*(u16*)0x807FBB34;
    if (count>64) count=64;
    for (int i=0;i<count;i++) {
        u8* actor=(u8*)actors[i*2];
        if (!actor || *(u32*)(actor+0x58)!=184) continue;
        u8* data=*(u8**)(actor+0x180);
        return data && data[0]==4 && data[0x1A]>0;
    }
    return 0;
}
static int returned(void) {
    int count = 0;
    for (int level = 0; level < 8; level++)
        count += krushaProgressRead(activeFile(), KRUSHA_GB_BIT + level*5 + 4, 1);
    return count;
}
static int totalReturned(void) {
    int (*native)(int,int,int) = (void*)0x80731AA8;
    return native(0x1FD,40,0) + returned();
}

/* This return is consumed solely by the native NPC's two state choices.
 * Keep its "40" bonus sentinel, prioritize any held personal blueprints, and
 * do not pretend the underlying total or board has been completed. */
int krushaSnideChoiceCount(int base, int width, int type) {
    int (*native)(int,int,int) = (void*)0x80731AA8;
    int count = native(base,width,type);
    int pending;
    if (base != 0x1FD || width != 40 || type != 0) return count;
    count += returned();
    pending = krushaPauseFlagRange(0x1D5,0,7,Character) -
              krushaPauseFlagRange(0x1FD,0,7,Character);
    if (count >= 40) return pending > 0 ? 39 : 40;
    return count;
}

int krushaSnideBonusFlag(int flag, int type) {
    /* Only the native bonus-access loop calls this adapter. All board flags
     * and actual progress readers retain their individual ownership. */
    return totalReturned() >= 40;
}

void krushaSnideSetFlag(int flag, int value, int type) {
    if (flag >= 0x4000 && flag < 0x4200) {
        if (!krushaCampaignAvailable() || Character!=5) return;
        krushaProgressWrite(activeFile(),flag-0x4000,1,value != 0);
    } else setFlag(flag,value,type);
}

int krushaSnideBoardComplete(int base, int width, int type) {
    int (*native)(int,int,int) = (void*)0x80731AA8;
    int originals = native(base,width,type);
    /* Native constructor compares this with 40 to choose its finished
     * palette. That visual is distinct from the bonus access threshold. */
    if (!krushaEnabled()) return originals;
    return originals == 40 && returned() == 8 ? 40 : 39;
}

static void codeImmediate(u32 address, u16 value) {
    u32* code = (u32*)address;
    u32 replacement = (*code & 0xFFFF0000) | value;
    if (*code == replacement) return;
    *code = replacement;
    osWritebackDCache(code,4);
    osInvalICache(code,4);
}

void krushaSnideBoard(void) {
    u8* actor = *(u8**)0x807FBB40;
    int first = !(*(u32*)(actor+0x60) & 0x10);
    vanillaSnideBoard();
    if (first && krushaEnabled()) {
        u8* vertices = *(u8**)0x80033F10;
        u8* frame = *(u8**)0x800330D4;
        /* Native code initializes five rows into a deliberately enlarged
         * allocation. Clone one row's topology, then assign sixth ownership. */
        for (int i = 0; i < 0x400; i++) vertices[0x1400+i] = vertices[i];
        for (int i = 0; i < 8*8; i++) {
            u8* v = vertices + 0x1400+i*16;
            *(s16*)(v+2) += 150*4;
            *(s16*)(v+10) += 150*64;
            if (*(u8*)0x80033258) { v[12] = 0; v[13] = v[14] = 255; }
            else v[12] = v[13] = v[14] = KRUSHA_IDENTITY_GRAY;
        }
        for (int i = 0; i < 6*8*8; i++)
            *(s16*)(vertices+i*16+2) -= 15*4;
        /* Expand around the native center; keep the final tick quad intact. */
        for (int i = 0; i < 16; i++) {
            s16* y = (s16*)(frame+i*16+2);
            *y += *y < 480 ? -60 : 60;
        }
    }
}

Gfx* krushaSnideDraw(Gfx* dl, void* actor) {
    int enabled = krushaEnabled();
    /* This overlay is reloaded by native map transitions. Restore OFF bounds
     * explicitly; changing the option cannot leave a sixth stale row. */
    codeImmediate(0x800256A0, enabled ? 180 : 150);
    codeImmediate(0x800259E8, enabled ? 0x1800 : 0x1400);
    codeImmediate(0x80025430, enabled ? 7200 : 0xA3);
    return vanillaSnideDraw(dl,actor);
}
