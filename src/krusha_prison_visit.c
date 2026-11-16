#include "../include/common.h"
#include "../include/krusha_prison_scene.h"
#include "../include/recruitment_assets.generated.h"
#include "../include/recruitment_room.generated.h"

/* Transient R03 scene ownership. No quest/save bits and no allocated actors.
 * Never carry player/camera pointers across a map load. Native exits own the
 * return; native transformation owns Mini's flags, matrix and interpolation. */
enum { OUTSIDE, ENTERING, STAGED, RETURNING };
static u32 phase, ticks, travel_ticks, cooldown, file, previous_buttons;
static u8 skip,restore_mini,door_return;
static u8 exterior_hud_owned;
static u32 exterior_hud_started;
/* phase, entries, returns, aborts, drain calls suppressed, entry crystals,
 * staged crystals, return crystals, staged frames, last native frame. */
volatile u32 krushaPrisonVisitTrace[10];
/* Early form restores, first frame, last frame. */
volatile u32 krushaPrisonReturnTrace[3];
static int valid(void* p,u32 size) {return (u32)p>=0x80000000 && (u32)p<=0x80800000-size;}
static int tiny(void) {return valid(Player,0x178) && Character==3 && *(u32*)((u8*)Player+0x58)==5;}
static int liveTiny(void) {
    if (!tiny()) return 0;
    for (int n=0;n<ActorCount && n<256;n++) if ((void*)ActorArray[n]==Player) return 1;
    return 0;
}
static int ready(void) {return ObjectModel2Timer>5 && valid(Player,0x178) && LZFadeoutProgress<=0 && !IsAutowalking;}
/* Halfway from the earlier neutral0.65 light to native warm(102,64,30)/255.
 * Write a fixed blend, not a repeated average that would drift every frame. */
static void roomLighting(void) {
    s32 count=*(s32*)0x807F6C28;
    if (count<=0 || count>255) return;
    for (s32 i=0;i<3;i++)
        if (!valid(*(void**)(0x8076A0B4+i*4),count*sizeof(f32))) return;
    extern void krushaSetChunkLighting(f32,f32,f32,s16);
    krushaSetChunkLighting(.525f,.4504902f,.3838235f,-1);
}
/* A manually restored persistent counter has no native barrel actor to end
 * its hold. Release ONLY our hold when Mini ends, through the native HUD
 * cleanup (including saved pause-group masks). Never retain a HUD pointer or
 * clear a counter belonging to a newly loaded map/file. */
static void exteriorHudTick(void) {
    u8* cc=*(u8**)0x807FC924;
    if (!exterior_hud_owned) return;
    if (!DetectAdventure() || CurrentMap!=34 || file!=*(u8*)0x807467C8 ||
        ObjectModel2Timer<exterior_hud_started) {exterior_hud_owned=0;return;}
    if (tiny() && valid(cc,0x2C4)) {
        u8* data=*(u8**)((u8*)Player+0x174);
        if (cc[0x2C0]==0 && CollectableBase.Crystals>0) return;
        /* Keep native tag restrictions through the growth interpolation. */
        if (valid(data,0x1D0) && *(f32*)(data+0x1CC)<.149f) return;
    }
    if (valid(HUD,6*sizeof(HUDDisplay)))
        ((void (*)(s32,s32))0x806F8D58)(5,0);
    exterior_hud_owned=0;
}
static void transform(void) {
    u8* cc=*(u8**)0x807FC924;
    u8* data=tiny()?*(u8**)((u8*)Player+0x174):0;
    u8* anim=tiny()?*(u8**)((u8*)Player+4):0;
    if (restore_mini && tiny() && valid(cc,0x2C4) && valid(data,0x1E8) &&
        valid(anim,0x40) && valid(*(void**)(data+0x104),0x180) && CollectableBase.Crystals>0 &&
        (cc[0x2C0]!=0 || *(f32*)(data+0x1CC)>.051f ||
         *(f32*)(data+0x1C0)>.051f || *(f32*)(anim+0x34)>.051f)) {
        ((void (*)(void*,u8))0x806D0468)(Player,0);
        if (CurrentMap==34 && phase==RETURNING) {
            /* The map constructor initialized a normal-size camera before
             * Mini existed. Rebuild it once for the restored native form,
             * during black loading, using the native player-load helper. */
            ((void (*)(void*,u8))0x8061EB04)(Player,0);
            if (!krushaPrisonReturnTrace[0]) krushaPrisonReturnTrace[1]=ObjectModel2Timer;
            krushaPrisonReturnTrace[0]++;krushaPrisonReturnTrace[2]=ObjectModel2Timer;
        }
    }
    if (restore_mini && tiny() && valid(cc,0x2C4) && cc[0x2C0]==0 &&
        CurrentMap==34 && CollectableBase.Crystals>0 &&
        valid(HUD,6*sizeof(HUDDisplay)) && !HUD[5].freeze_timer) {
        ((void (*)(s32,u8,s32))0x806F8BC4)(5,1,0);
        exterior_hud_owned=1;exterior_hud_started=ObjectModel2Timer;
    }
}
static void end(int returned) {
    if (returned) {krushaPrisonVisitTrace[2]++;krushaPrisonVisitTrace[7]=CollectableBase.Crystals;}
    else krushaPrisonVisitTrace[3]++;
    krushaPrisonSceneReset();
    phase=OUTSIDE;restore_mini=door_return=0;cooldown=45;ticks=travel_ticks=skip=previous_buttons=0;
    krushaPrisonVisitTrace[0]=OUTSIDE;
}
s32 krushaPrisonVisitBusy(void) {return phase!=OUTSIDE;}
s32 krushaPrisonVisitBegin(void) {
    if (phase || cooldown || !DetectAdventure() || CurrentMap!=34 || !tiny() || *(u8*)0x807467C8>2) return 0;
    krushaPrisonSceneReset();
    for (int i=0;i<3;i++) krushaPrisonReturnTrace[i]=0;
    phase=ENTERING;restore_mini=1;door_return=0;file=*(u8*)0x807467C8;ticks=travel_ticks=skip=previous_buttons=0;
    krushaPrisonVisitTrace[0]=phase;krushaPrisonVisitTrace[1]++;
    krushaPrisonVisitTrace[5]=CollectableBase.Crystals;
    initiateTransition(RECRUITMENT_ROOM_MAP,0);
    return 1;
}
void krushaPrisonVisitTick(void) {
    u32 frame=*(u32*)0x8076A064;
    exteriorHudTick();
    krushaPrisonVisitTrace[9]=frame;
    if (!DetectAdventure() || (phase && file!=*(u8*)0x807467C8)) {
        if (phase) end(0);
        return;
    }
    if (!krushaEnabled() && phase && phase!=RETURNING) end(0);
    if (!phase) {
        if (cooldown && !(TBVoidByte&3)) cooldown--;
        /* An orphaned map load (e.g. interrupted state) has no story or
         * freeroam contract. Eject through the same authored safe exit. */
        if (CurrentMap==RECRUITMENT_ROOM_MAP && ObjectModel2Timer>5 && LZFadeoutProgress<=0) {
            file=*(u8*)0x807467C8;phase=RETURNING;restore_mini=door_return=0;travel_ticks=0;
            initiateTransition(34,RECRUITMENT_RETURN_EXIT);
        }
        return;
    }
    /* A rejected native transfer must never leave world input captured. */
    if (phase!=STAGED && !(TBVoidByte&3) && LZFadeoutProgress<=0 && ++travel_ticks>300) {end(0);return;}
    if (CurrentMap!=34 && CurrentMap!=RECRUITMENT_ROOM_MAP) {end(0);return;}
    if (CurrentMap==RECRUITMENT_ROOM_MAP) {
        if (phase==ENTERING && ObjectModel2Timer>0 && tiny()) krushaPrisonScenePrepare(file);
        if (!tiny() && ObjectModel2Timer>10 && phase!=RETURNING) {phase=RETURNING;travel_ticks=0;initiateTransition(34,RECRUITMENT_RETURN_EXIT);}
        if (phase==ENTERING && ready() && tiny()) {
            transform();phase=STAGED;ticks=travel_ticks=0;
            krushaPrisonVisitTrace[6]=CollectableBase.Crystals;
            krushaPrisonSceneBegin(file);
        }
        if (phase==STAGED && !(TBVoidByte&3)) roomLighting();
        /* Native pause Exit Level also uses our landing, not Isles exit0. */
        if (LZFadeoutProgress>0 && phase!=ENTERING && DestMap==34) DestExit=RECRUITMENT_RETURN_EXIT;
        if (phase==STAGED && !(TBVoidByte&3) && !CutsceneActive && LZFadeoutProgress<=0) {
            ticks++;krushaPrisonVisitTrace[8]=ticks;
            if (krushaPrisonSceneTick()) {
                phase=RETURNING;travel_ticks=0;initiateTransition(34,RECRUITMENT_RETURN_EXIT);
            }
        }
    } else {
        /* Restore native Mini/camera during the loading fade, rather than
         * waiting until the exterior walk-in finishes in visible gameplay. */
        if (phase==RETURNING && ObjectModel2Timer>0 && liveTiny()) {
            transform();
        }
        /* A native door can interrupt the stage without using our timer's
         * transition helper. It still owns the same return/cleanup contract. */
        if (phase==STAGED) {phase=RETURNING;door_return=1;travel_ticks=0;}
        if (phase==RETURNING && ready()) {
            /* Native door handling can carry its exit walking/momentum through
             * the load. Reinitialize ONLY this interrupted return using the
             * authored native exit: detach, reset motion/collision and camera.
             * Never move a saved actor pointer or force an action/scale. */
            if (door_return) ((void (*)(s32))0x806C92C4)(RECRUITMENT_RETURN_EXIT);
            transform();end(1);
        }
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
        if (phase==STAGED) krushaPrisonSceneInput(buttons);
        /* Start remains native, including its pause screens and Quit Game. */
        for (s32 i=0;i<4;i++) {
            u8* pad=(u8*)raw+i*6;*(u16*)pad &= 0x1000;pad[2]=pad[3]=0;
        }
    }
    previous_buttons=buttons;
}

extern void vanillaBuildCameraMatrices(void*);
/* Owned scene framing only: eye XYZ, target XYZ, vertical FOV. */
f32 krushaPrisonCameraFraming[7]={700,650,-650,1450,750,1700,58};
f32 krushaPrisonTinyStaging[3]={1000,0,-430};
s32 krushaPrisonVisitCamera(void* display) {
    u8* cc=*(u8**)0x807FC924;
    if (!phase || !restore_mini || CurrentMap!=RECRUITMENT_ROOM_MAP ||
        !DetectAdventure() || file!=*(u8*)0x807467C8 ||
        !tiny() || !valid(cc,0x28C)) return 0;
    if (phase==ENTERING && !(TBVoidByte&3)) roomLighting();
    /* Temporary renderer-only view. Native collision/input camera state is
     * restored before returning; no persistent camera ownership or flags. */
    f32* eye=(f32*)(cc+0x210);f32* target=(f32*)(cc+0x228);
    f32 saved[11];
    for (s32 i=0;i<3;i++) {saved[i]=eye[i];saved[i+3]=target[i];}
    saved[6]=*(f32*)(cc+0x27C);
    saved[7]=*(f32*)(cc+0x288);
    for (int i=0;i<3;i++) saved[8+i]=*(f32*)(cc+0x240+i*4);
    *(f32*)(cc+0x240)=0;*(f32*)(cc+0x244)=1;*(f32*)(cc+0x248)=0;
    for (s32 i=0;i<3;i++) {eye[i]=krushaPrisonCameraFraming[i];target[i]=krushaPrisonCameraFraming[i+3];}
    *(f32*)(cc+0x27C)=krushaPrisonCameraFraming[6];
    *(f32*)(cc+0x288)=5000;
    vanillaBuildCameraMatrices(display);
    for (s32 i=0;i<3;i++) {eye[i]=saved[i];target[i]=saved[i+3];}
    *(f32*)(cc+0x27C)=saved[6];*(f32*)(cc+0x288)=saved[7];
    for (int i=0;i<3;i++) *(f32*)(cc+0x240+i*4)=saved[8+i];
    return 1;
}

/* Render-only43.2-fold Mini appearance; native form/movement/upkeep and
 * collision remain untouched. Normalize the zero-budget normal form to the
 * same visible size during the owned scene. Never carry a model pointer. */
f32 krushaPrisonVisualScale(void* actor) {
    if (!phase || !restore_mini || CurrentMap!=RECRUITMENT_ROOM_MAP ||
        actor!=Player || !tiny()) return 1;
    u8* data=*(u8**)((u8*)actor+0x174);
    if (!valid(data,0x1D0)) return 1;
    f32 scale=*(f32*)(data+0x1CC);
    return scale>.045f && scale<.16f ? 2.16f/scale : 1;
}
