#include "../include/common.h"
#include "../include/recruitment_assets.generated.h"
#include "../include/recruitment_room.generated.h"

/* Transient R03 scene ownership. No quest/save bits and no allocated actors.
 * Never carry player/camera pointers across a map load. Native exits own the
 * return; native transformation owns Mini's flags, matrix and interpolation. */
enum { OUTSIDE, ENTERING, STAGED, RETURNING };
static u32 phase, ticks, travel_ticks, cooldown, file, previous_buttons;
static u8 skip;
/* phase, entries, returns, aborts, drain calls suppressed, entry crystals,
 * staged crystals, return crystals, staged frames, last native frame. */
volatile u32 krushaPrisonVisitTrace[10];
static int valid(void* p,u32 size) {return (u32)p>=0x80000000 && (u32)p<=0x80800000-size;}
static int tiny(void) {return valid(Player,0x178) && Character==3 && *(u32*)((u8*)Player+0x58)==5;}
static int ready(void) {return ObjectModel2Timer>5 && tiny() && LZFadeoutProgress<=0 && !IsAutowalking;}
static void transform(void) {
    u8* cc=*(u8**)0x807FC924;
    if (tiny() && valid(cc,0x2C4) && CollectableBase.Crystals>0 && cc[0x2C0]!=0)
        ((void (*)(void*,u8))0x806D0468)(Player,0);
}
static void end(int returned) {
    if (returned) {krushaPrisonVisitTrace[2]++;krushaPrisonVisitTrace[7]=CollectableBase.Crystals;}
    else krushaPrisonVisitTrace[3]++;
    phase=OUTSIDE;cooldown=45;ticks=travel_ticks=skip=previous_buttons=0;
    krushaPrisonVisitTrace[0]=OUTSIDE;
}
s32 krushaPrisonVisitBusy(void) {return phase!=OUTSIDE;}
s32 krushaPrisonVisitBegin(void) {
    if (phase || cooldown || !DetectAdventure() || CurrentMap!=34 || !tiny() || *(u8*)0x807467C8>2) return 0;
    phase=ENTERING;file=*(u8*)0x807467C8;ticks=travel_ticks=skip=previous_buttons=0;
    krushaPrisonVisitTrace[0]=phase;krushaPrisonVisitTrace[1]++;
    krushaPrisonVisitTrace[5]=CollectableBase.Crystals;
    initiateTransition(RECRUITMENT_ROOM_MAP,0);
    return 1;
}
void krushaPrisonVisitTick(void) {
    u32 frame=*(u32*)0x8076A064;
    krushaPrisonVisitTrace[9]=frame;
    if (!DetectAdventure() || !krushaEnabled() || (phase && file!=*(u8*)0x807467C8)) {
        if (phase) end(0);
        return;
    }
    if (!phase) {
        if (cooldown && !(TBVoidByte&3)) cooldown--;
        /* An orphaned map load (e.g. interrupted state) has no story or
         * freeroam contract. Eject through the same authored safe exit. */
        if (CurrentMap==RECRUITMENT_ROOM_MAP && ObjectModel2Timer>5 && LZFadeoutProgress<=0) {
            file=*(u8*)0x807467C8;phase=RETURNING;
            initiateTransition(34,RECRUITMENT_RETURN_EXIT);
        }
        return;
    }
    /* A rejected native transfer must never leave world input captured. */
    if (phase!=STAGED && !(TBVoidByte&3) && LZFadeoutProgress<=0 && ++travel_ticks>300) {end(0);return;}
    if (CurrentMap!=34 && CurrentMap!=RECRUITMENT_ROOM_MAP) {end(0);return;}
    if (CurrentMap==RECRUITMENT_ROOM_MAP) {
        if (!tiny() && ObjectModel2Timer>10) {phase=RETURNING;travel_ticks=0;initiateTransition(34,RECRUITMENT_RETURN_EXIT);}
        if (phase==ENTERING && ready()) {
            transform();phase=STAGED;ticks=travel_ticks=0;
            krushaPrisonVisitTrace[6]=CollectableBase.Crystals;
        }
        /* Native pause Exit Level also uses our landing, not Isles exit0. */
        if (LZFadeoutProgress>0 && phase!=ENTERING && DestMap==34) DestExit=RECRUITMENT_RETURN_EXIT;
        if (phase==STAGED && !(TBVoidByte&3) && !CutsceneActive && LZFadeoutProgress<=0) {
            ticks++;krushaPrisonVisitTrace[8]=ticks;
            if (ticks>=RECRUITMENT_STAGE_TICKS || (skip && ticks>=45)) {
                phase=RETURNING;travel_ticks=0;initiateTransition(34,RECRUITMENT_RETURN_EXIT);
            }
        }
    } else {
        /* A native door can interrupt the stage without using our timer's
         * transition helper. It still owns the same return/cleanup contract. */
        if (phase==STAGED) {phase=RETURNING;travel_ticks=0;}
        if (phase==RETURNING && ready()) {transform();end(1);}
    }
    krushaPrisonVisitTrace[0]=phase;
}

/* Hook only the native Mini/Hunky per-frame crystal debit call. No generic
 * refill, and no effect on shockwave, shout or the exterior/fade budget. */
void krushaPrisonCrystalDrain(s32 item,s32 player,s32 amount) {
    u8* cc=*(u8**)0x807FC924;
    if (phase && CurrentMap==RECRUITMENT_ROOM_MAP && DetectAdventure() &&
        file==*(u8*)0x807467C8 && tiny() && valid(cc,0x2C4) && cc[0x2C0]==0 &&
        item==5 && player==0 && amount==-1) {krushaPrisonVisitTrace[4]++;return;}
    ((void (*)(s32,s32,s32))0x806F91B4)(item,player,amount);
}

void krushaPrisonVisitInput(void* raw) {
    if (!phase || !DetectAdventure() || (CurrentMap!=34 && CurrentMap!=RECRUITMENT_ROOM_MAP)) return;
    u16 buttons=*(u16*)raw;
    if (!(TBVoidByte&3)) {
        if (phase==STAGED && ticks>=45 && (buttons & ~previous_buttons & 0xC000)) skip=1;
        /* Start remains native, including its pause screens and Quit Game. */
        for (s32 i=0;i<4;i++) {
            u8* pad=(u8*)raw+i*6;*(u16*)pad &= 0x1000;pad[2]=pad[3]=0;
        }
    }
    previous_buttons=buttons;
}

extern void vanillaBuildCameraMatrices(void*);
s32 krushaPrisonVisitCamera(void* display) {
    u8* cc=*(u8**)0x807FC924;
    if (phase!=STAGED || CurrentMap!=RECRUITMENT_ROOM_MAP || !tiny() || !valid(cc,0x284)) return 0;
    /* Temporary renderer-only view. Native collision/input camera state is
     * restored before returning; no persistent camera ownership or flags. */
    f32* eye=(f32*)(cc+0x210);f32* target=(f32*)(cc+0x228);
    f32 saved[7];
    for (s32 i=0;i<3;i++) {saved[i]=eye[i];saved[i+3]=target[i];}
    saved[6]=*(f32*)(cc+0x27C);
    f32* pos=(f32*)((u8*)Player+0x7C);
    eye[0]=pos[0]+55;eye[1]=pos[1]+8;eye[2]=pos[2]-100;
    target[0]=pos[0];target[1]=pos[1]+5;target[2]=pos[2];
    *(f32*)(cc+0x27C)=50;
    vanillaBuildCameraMatrices(display);
    for (s32 i=0;i<3;i++) {eye[i]=saved[i];target[i]=saved[i+3];}
    *(f32*)(cc+0x27C)=saved[6];return 1;
}
