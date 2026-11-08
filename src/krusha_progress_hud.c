#include "../include/common.h"

extern const void* krushaProgressFace(void);
extern void krushaNativeGBHUDInit(s32);
extern Gfx* widescreenNativeHUDGroup(s32,void*,Gfx*);
extern Gfx* widescreenNativeHUDCounter(s32,void*,Gfx*);

/* The native five portrait arrays abut unrelated state. The sixth face owns
 * a separate transform; no sixth access is ever made to those native arrays. */
f32 krushaGBPortraitTransform[3]={-200,-200,1};
static int enabled(void) { return krushaEnabled() && DetectAdventure(); }

static void portrait(void* sprite,s8* done) {
    u8* p=sprite;
    if (!enabled() || krushaGBPortraitTransform[0]==-200) { *done=1;return; }
    *(f32*)(p+0x340)=krushaGBPortraitTransform[0];
    *(f32*)(p+0x344)=krushaGBPortraitTransform[1];
    *(f32*)(p+0x360)=*(f32*)(p+0x364)=krushaGBPortraitTransform[2];
    krushaGBPortraitTransform[0]=-200;
}

void krushaGBHUDInit(s32 item) {
    krushaNativeGBHUDInit(item);
    if (!enabled() || item!=8) return;
    void (*reset)(void)=(void*)0x8071495C;
    void (*layer)(s32)=(void*)0x807149FC;
    void (*callback)(void*)=(void*)0x8071498C;
    void (*argument)(s32)=(void*)0x80714950;
    void* (*spawn)(const void*,f32,f32,f32,f32)=(void*)0x80714CC0;
    reset();layer(-1);callback(portrait);argument(5);
    krushaGBPortraitTransform[0]=-100;
    spawn(krushaProgressFace(),1,-200,0,-10);
}

Gfx* krushaGBHUDGroup(s32 item,void* child,Gfx* dl) {
    if (!enabled() || item!=8) return widescreenNativeHUDGroup(item,child,dl);
    s32* origin=*(s32**)((u8*)child+0x14);
    s32 saved_y=origin[1],saved_count=HUD[item].hud_count;
    /* Six native-size rows. Leave room for the selected sixth portrait's
     * taller sprite, including the native ten-pixel lower overscan border. */
    origin[1]-=22;
    f32 (*sine)(s16)=(void*)0x80612794;
    s32 (*selected)(s32)=(void*)0x806C8DE0;
    s32 (*levelOf)(s32,s32)=(void*)0x805FF030;
    int kong=selected(0),level=levelOf(CurrentMap,1);
    f32 x=origin[0]*4.0f-4.0f*(6.0f-(1.0f-sine(*(s16*)((u8*)child+0x10)))*(*(f32*)((u8*)child+4)));
    f32 y=origin[1]*4.0f+92;
    for (int i=0;i<6;i++) {
        if (i>0 && i<5 && !checkFlag(((s16*)0x807505AE)[i],0)) continue;
        f32 scale=i==kong ? 2.0f : 1.5f;
        HUD[item].hud_count=i==kong ? saved_count : (level>=0 && level<8 ? MovesBase[i].gb_count[level] : 0);
        dl=widescreenNativeHUDCounter(item,child,dl);
        if (i!=kong) { gDPSetPrimColor(dl++,0,0,0,0,0,*(u8*)0x807FD7E4>>1); }
        if (i<5) {
            ((f32*)0x807FD7A0)[i]=x-10*scale;
            ((f32*)0x807FD7B8)[i]=y-30*scale;
            ((f32*)0x807FD7D0)[i]=scale*1.15f;
        } else {
            krushaGBPortraitTransform[0]=x-10*scale;
            krushaGBPortraitTransform[1]=y-30*scale;
            krushaGBPortraitTransform[2]=scale*1.15f;
        }
        y+=136;origin[1]+=34;
    }
    HUD[item].hud_count=saved_count;origin[1]=saved_y;
    gSPMatrix(dl++,(Mtx*)0x02000180,G_MTX_MODELVIEW|G_MTX_LOAD|G_MTX_NOPUSH);
    return dl;
}
