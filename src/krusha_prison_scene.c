#include "../include/common.h"
#include "../include/krusha_prison_scene.h"
#include "../include/krusha_recruitment.h"
#include "../include/krusha_progress.h"
#include "../include/recruitment_scene.generated.h"

/* Seven bounded native display actors, never K. Lumsy's story controllers.
 * Map216 has no native actors of these classes. Elsewhere dispatch is exact.
 * The native map destructor owns actor/model lifetimes; handles include UID. */
static struct {u8* actor;u32 uid;} displays[7];
static u32 active,file,page,age,advance,finished,empty,intro,last_timer,built;
volatile u32 krushaPrisonSceneTrace[12];
extern void krushaPlayActorAnimation(void*,s32);
extern void krushaInitCharacterMesh(void*,u16);
extern void krushaHolsterModel(void*);
static int valid(void* p,u32 size) {return (u32)p>=0x80000000 && (u32)p<=0x80800000-size;}
static int context(void) {return active && CurrentMap==216 && DetectAdventure() && file==krushaProgressActiveFile() && Character==3 && Player;}
static int alive(int i) {
    if (!displays[i].actor || CurrentMap!=216) return 0;
    for (int n=0;n<ActorCount && n<256;n++) if ((void*)ActorArray[n]==displays[i].actor)
        return *(u32*)(displays[i].actor+0x54)==displays[i].uid;
    return 0;
}
int krushaPrisonDisplayOwned(void* actor) {
    return CurrentMap==216 && displays[0].actor==actor && alive(0);
}
static int slot(void* actor) {
    for (int i=0;i<7;i++) if (displays[i].actor==actor && alive(i)) return i;
    return -1;
}
static void update(void) {
    /* Legacy CurrentActorPointer label names the last-spawned slot. The
     * actual update iterator uses807FBB40; never dispatch from last-spawned. */
    u8* a=*(u8**)0x807FBB40;
    u32 type=*(u32*)(a+0x58);
    if (CurrentMap!=216) {
        ((void(*)(void))(type==316 ? 0x80683158 : type==115 ? 0x806A1F28 : 0x806BD7B0))();return;
    }
    int i=slot(a);
    if (!context() || i<0) return; /* native map teardown owns release */
    if (i==0 && !(*(u32*)(a+0x60)&0x10)) {
        /* Native display init allocates its32 animation-channel records and
         * initializes Krusha's own mesh. It has no parent-barrel dependency. */
        ((void(*)(void))0x80683158)();krushaHolsterModel(a);
        /* Barrel displays request their own lighting path. In this world
         * scene use native room lighting, preserving Krusha's blue skin. */
        *(u32*)(a+0x60)&=~0x1000;
        *(s16*)(a+0xE6)=2048;return;
    }
    ((void(*)(void*,s32))0x806319C4)(a,0);
}
void krushaPrisonSceneInstall(void) {
    void(**functions)(void)=(void*)0x8074C0A0;
    const u16 types[3]={316,115,334};
    for (int i=0;i<3;i++) {functions[types[i]]=update;osWritebackDCache(functions+types[i],4);}
}
static int spawn(int i,int type,int model,f32 x,f32 y,f32 z,f32 scale,s16 angle) {
    if (!spawnActor(type,model)) return 0;
    u8* a=*(u8**)0x807FBB44;displays[i].actor=a;displays[i].uid=*(u32*)(a+0x54);
    *(f32*)(a+0x7C)=x;*(f32*)(a+0x80)=y;*(f32*)(a+0x84)=z;
    u8* anim=*(u8**)(a+4);
    for (int j=0;j<3;j++) *(f32*)(anim+0x34+j*4)=scale;
    *(s16*)(a+0xE6)=angle;
    *(s16*)(a+0x128)=255;  /* shadow opacity, not distance */
    *(s16*)(a+0x12A)=3000; /* native display draw distance */
    /* These seven owned cutscene displays use the native no-distance/chunk-
     * cull bit. Their positions need not follow Mini Tiny's normal camera. */
    *(u32*)(a+0x60)|=0x40000400;
    /* Preserve native RGB/lighting; set opacity without a synthetic tint. */
    a[0x16D]=255;a[0x15F]=255;
    if (i==0) {
        *(u16*)*(u8**)(a+0x174)=7;krushaInitCharacterMesh(a,7);krushaHolsterModel(a);
        krushaPlayActorAnimation(a,0x1DC);
    }
    krushaPrisonSceneTrace[4]++;return 1;
}
void krushaPrisonSceneReset(void) {
    active=0;
    /* The owned visit always leaves through a native map transition. Let
     * its destructor release each actor once, including interrupted visits. */
    /* Do not follow or delete a handle from a previous map generation. */
}
void krushaPrisonSceneBegin(unsigned int f) {
    for (int i=0;i<7;i++) {displays[i].actor=0;displays[i].uid=0;}
    active=1;file=f;page=age=advance=finished=built=0;last_timer=ObjectModel2Timer;
    if (valid(Player,0xF0)) {
        *(u16*)((u8*)Player+0xE6)=3484;*(u16*)((u8*)Player+0xEE)=3484;
    }
    empty=krushaRecruitmentRecruited(file)!=0;
    intro=!empty && !krushaRecruitmentIntroSeen(file);
    krushaPrisonSceneTrace[0]++;krushaPrisonSceneTrace[5]=0;
}
static const char* first[6][4]={
    {"KRUSHA", "WE CAUGHT SOME MONKEYS. I WAS HUNGRY...", "SO I DEALT WITH THE WHOLE BUNCH MYSELF.",0},
    {"TINY", "YOU FREED THEM? AND THE OTHER", "KREMLINGS PUNISHED YOU?",0},
    {"KRUSHA", "ER... YES! FREED THEM. THEY WERE", "FURIOUS I HADN'T SHARED.",0},
    {"TINY", "SHARED THE CREDIT?",0,0},
    {"KRUSHA", "EXACTLY! FIND THE FIVE COLORED KEYS,", "GET ME OUT, AND I'M ON YOUR SIDE.",0},
    {"TINY", "ONE KEY FOR EACH OF US.", "WE'LL BRING THEM HERE.",0}
};
static const char* again[4]={"KRUSHA","STILL LOCKED UP. STILL HUNGRY.","KEEP LOOKING!",0};
static const char* held[4]={"TINY","WE'VE FOUND SOME COLORED KEYS!",0,0};
static const char* wip[4]={"KRUSHA","THE LOCKS ARE STUCK FOR NOW.","KEEP YOUR KEYS. TRY AGAIN SOON.",0};
static const char* gone[4]={"TINY","HE'S OUT. BETTER FIND THE OTHERS.",0,0};
static const char** lines(void) {
    if (empty) return gone;
    if (intro && page<6) return first[page];
    if (krushaRecruitmentKeys(file) && page==(intro?6:0)) return held;
    if (!intro && !page && !krushaRecruitmentKeys(file)) return again;
    return wip;
}
static Gfx* draw(Gfx* dl,void* actor) {
    if (!context() || (TBVoidByte&3) || finished) return dl;
    const char** text=lines();
    Gfx*(*print)(Gfx*,s16,s16,f32,char*)=(void*)0x806ABB98;
    gDPPipeSync(dl++);
    dl->words.w0=0xE3000A01;dl->words.w1=0;dl++;
    dl->words.w0=0xE200001C;dl->words.w1=0x00504240;dl++;
    gDPSetCombineMode(dl++,G_CC_PRIMITIVE,G_CC_PRIMITIVE);
    gDPSetPrimColor(dl++,0,0,0,0,0,165);
    s32 scale=*(u8*)0x8074450C;if (scale<1 || scale>2) scale=1;
    gDPFillRectangle(dl++,8*scale,155*scale,312*scale,231*scale);
    gDPPipeSync(dl++);
    gSPDisplayList(dl++,(void*)0x01000118);
    dl->words.w0=0xDA380007;dl->words.w1=0x020000C0;dl++;
    dl->words.w0=0xE200001C;dl->words.w1=0x00504240;dl++;
    gDPSetCombineLERP(dl++,0,0,0,TEXEL0,TEXEL0,0,PRIMITIVE,0,0,0,0,TEXEL0,TEXEL0,0,PRIMITIVE,0);
    gDPSetPrimColor(dl++,0,0,255,225,110,255);
    s16 center=*(s16*)0x80744490*2;
    dl=print(dl,center,162*4,.42f,(char*)text[0]);
    gDPSetPrimColor(dl++,0,0,255,255,255,255);
    for (int i=1;i<4;i++) if (text[i]) dl=print(dl,center,(173+i*11)*4,.35f,(char*)text[i]);
    dl=print(dl,center,218*4,.25f,"A OR B: CONTINUE");
    return dl;
}
void krushaPrisonSceneInput(unsigned int pressed) {if(context() && age>=15 && (pressed&0xC000)) advance=1;}
int krushaPrisonSceneTick(void) {
    if (!context()) return 1;
    if (ObjectModel2Timer<last_timer) {krushaPrisonSceneReset();return 1;}
    last_timer=ObjectModel2Timer;
    /* One bounded construction attempt per slot, no retry allocation storm. */
    if (!built) {
        built=1;
        if (!empty && !spawn(0,316,0xDB,900,95,1000,4.5f,2048)) finished=1;
        if (!spawn(1,115,0xC4,900,95,1000,1.9f,0)) finished=1;
        u32 locks=krushaRecruitmentLocks(file);
        /* Follow the front of the enlarged cage. Keep every owner's fixed
         * slot when an opened lock is omitted; no shifting saved colors. */
        for (int i=0;i<5;i++) if (!(locks&(1u<<i)) &&
            !spawn(i+2,334,RECRUITMENT_LOCK_MODEL_TOKEN+i,1260-i*180,435,
                1000-dk_sqrt(655.0f*655.0f-(360.0f-i*180)*(360.0f-i*180)),.24f,2048)) finished=1;
    }
    if (finished) return ++age>30;
    ((void(*)(void*,void*,u8))0x8068C350)(draw,Player,3);
    age++;krushaPrisonSceneTrace[1]=page;krushaPrisonSceneTrace[2]=age;
    krushaPrisonSceneTrace[3]=(empty?2:intro?0:1);
    krushaPrisonSceneTrace[6]=krushaRecruitmentKeys(file);krushaPrisonSceneTrace[7]=krushaRecruitmentLocks(file);
    if (age>=240 || advance) {
        advance=0;age=1;
        if (intro && page==5) {krushaRecruitmentMarkIntro(file);krushaPrisonSceneTrace[5]++;}
        page++;
        u32 pages=empty?1:intro?7:krushaRecruitmentKeys(file)?2:1;
        if (!empty && intro && krushaRecruitmentKeys(file)) pages++;
        if (page>=pages) {finished=1;age=0;}
    }
    return 0;
}
