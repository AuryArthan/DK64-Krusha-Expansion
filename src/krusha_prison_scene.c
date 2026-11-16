#pragma GCC optimize("Os","no-strict-aliasing")
#include "../include/common.h"
#include "../include/krusha_prison_scene.h"
#include "../include/krusha_recruitment.h"
#include "../include/krusha_progress.h"
#include "../include/recruitment_scene.generated.h"

/* Seven bounded native display actors, never K. Lumsy's story controllers.
 * Map216 has no native actors of these classes. Elsewhere dispatch is exact.
 * The native map destructor owns actor/model lifetimes; handles include UID. */
static struct {u8* actor;u32 uid;} displays[7];
static u32 active,file,page,age,text_clock,held_buttons,finished,empty,intro,last_timer,built,begun,voiced_page,voice_cooldown;
volatile u32 krushaPrisonSceneTrace[12];
/* quiet script installs, voice count, last voice, current cooldown. */
volatile u32 krushaPrisonDialogueTrace[4];
/* Native Tiny standing170 prefix: speed1, generic breathing clip0 with
 * six-frame interpolation. Wait for its cycle and repeat; omit all native
 * random boredom branches and their0x39/0x3D sound commands. */
const u8 krushaPrisonTinyIdleScript[]={
    0x24,0x3F,0x80,0,0,0,0,0,0,0x19,0,0,0x40,0xC0,0,0,0x04,0x34
};
void krushaPrisonTinyAnimation(void* actor,int script);

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
        *(s16*)(a+0xE6)=1900;return;
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
    active=begun=held_buttons=0;
    /* The owned visit always leaves through a native map transition. Let
     * its destructor release each actor once, including interrupted visits. */
    /* Do not follow or delete a handle from a previous map generation. */
}
static void construct(void) {
    if (built) return;
    built=1;
    /* The private room is centered on this cage; Mini Tiny remains
     * outside on an existing native floor. Captive stands132 units
     * behind its center, facing the rendered Tiny, clear of the front bars. */
    if (!empty && !spawn(0,316,0xDB,900,95,1832,8.415f,1900)) finished=1;
    if (!spawn(1,115,0xC4,900,95,1700,3.553f,0)) finished=1;
    u32 locks=krushaRecruitmentLocks(file);
    /* Lower front rail; keyless locks face Tiny. Keep saved-owner gaps. */
    for (int i=0;i<5;i++) if (!(locks&(1u<<i)) &&
        !spawn(i+2,334,RECRUITMENT_LOCK_MODEL_TOKEN+i,
            1184.2835f-i*180,115,503.639f,.48f,2048)) finished=1;
    krushaPrisonSceneTrace[8]=ObjectModel2Timer;
}
void krushaPrisonScenePrepare(unsigned int f) {
    if (active || CurrentMap!=216 || !DetectAdventure() || f!=krushaProgressActiveFile() || Character!=3 || !Player) return;
    /* Wait for THIS map's live player, not an exterior pointer carried
     * through the map/heap transfer. Preparation still precedes fade-in. */
    int found=0;
    for (int n=0;n<ActorCount && n<256;n++) if ((void*)ActorArray[n]==Player) {found=1;break;}
    if (!found) return;
    for (int i=0;i<7;i++) {displays[i].actor=0;displays[i].uid=0;}
    active=1;file=f;page=age=text_clock=held_buttons=finished=built=begun=0;last_timer=ObjectModel2Timer;
    empty=krushaRecruitmentRecruited(file)!=0;
    intro=!empty && !krushaRecruitmentIntroSeen(file);
    krushaPrisonSceneTrace[0]++;krushaPrisonSceneTrace[5]=0;
    krushaPrisonSceneTrace[9]=krushaPrisonSceneTrace[10]=krushaPrisonSceneTrace[11]=0;
    construct();
}
void krushaPrisonSceneBegin(unsigned int f) {
    krushaPrisonScenePrepare(f);
    if (!context() || begun) return;
    begun=1;age=text_clock=held_buttons=0;last_timer=ObjectModel2Timer;
    voiced_page=~0u;voice_cooldown=0;
    if (valid(Player,0xF0)) {
        *(u16*)((u8*)Player+0xE6)=3948;*(u16*)((u8*)Player+0xEE)=3948;
        krushaPlayActorAnimation(Player,0x170);
    }
    krushaPrisonSceneTrace[9]=ObjectModel2Timer;
}
void krushaPrisonTinyAnimation(void* actor,int script) {
    if (!context() || !begun || finished || actor!=Player || script!=0x170) return;
    u8* animation=*(u8**)((u8*)actor+4);
    if (!valid(animation,0x8C)) return;
    *(const u8**)(animation+0x68)=krushaPrisonTinyIdleScript;
    *(const u8**)(animation+0x6C)=krushaPrisonTinyIdleScript;
    *(const u8**)0x807F5AF0=krushaPrisonTinyIdleScript;
    krushaPrisonDialogueTrace[0]++;
}
static const char* first[6][6]={
    {"KRUSHA", "WE CAUGHT SOME MONKEYS.", "I WAS HUNGRY... SO I", "DEALT WITH THE WHOLE", "BUNCH MYSELF.",0},
    {"TINY", "YOU FREED THEM? AND", "THE OTHER KREMLINGS", "PUNISHED YOU?",0,0},
    {"KRUSHA", "ER... YES, YES,", "FREED THEM... THEY", "WERE FURIOUS I", "HADN'T SHARED.",0},
    {"TINY", "SHARED THE CREDIT?",0,0,0,0},
    {"KRUSHA", "ER... YEAH, YEAH,", "WHATEVER... ANYWAY,", "FIND THE FIVE COLORED", "KEYS, GET ME OUT,", "AND I'M ON YOUR SIDE."},
    {"TINY", "ONE KEY FOR EACH OF", "US. WE'LL BRING THEM", "HERE.",0,0}
};
static const char* again[6]={"KRUSHA","STILL LOCKED UP.","STILL HUNGRY.","KEEP LOOKING!",0,0};
static const char* held[6]={"TINY","WE'VE FOUND SOME","COLORED KEYS!",0,0,0};
static const char* wip[6]={"KRUSHA","THE LOCKS ARE STUCK","FOR NOW. KEEP YOUR","KEYS. TRY AGAIN SOON.",0,0};
static const char* gone[6]={"TINY","HE'S OUT. BETTER","FIND THE OTHERS.",0,0,0};
static const char** lines(void) {
    if (empty) return gone;
    if (intro && page<6) return first[page];
    if (krushaRecruitmentKeys(file) && page==(intro?6:0)) return held;
    if (!intro && !page && !krushaRecruitmentKeys(file)) return again;
    return wip;
}
static u32 length(const char* text) {
    u32 n=0;if (text) while (n<95 && text[n]) n++;return n;
}
static u32 characters(void) {
    const char** text=lines();u32 n=0;for(int i=1;i<6;i++) n+=length(text[i]);return n;
}
static Gfx* draw(Gfx* dl,void* actor) {
    if (!context() || !begun || (TBVoidByte&3) || finished) return dl;
    const char** text=lines();
    /* Native animated cloud and its four tapering pointer bubbles. Use
     * native deferred frame storage, exactly as the game's text renderer;
     * no persistent text actor or K. Lumsy story controller is involved. */
    Mtx* matrices=dk_malloc(0x3C0);
    if (!matrices) return dl;
    ((void(*)(void*))0x8061134C)(matrices);
    u8 bubble[0x3C] __attribute__((aligned(8)));
    /* Native pointer renderer reads only20..3B; these two angles are zero. */
    *(u32*)(bubble+0x38)=0;
    extern s32 mirrorEnabled(void);
    s32 krusha=text[0][0]=='K';
    f32 mouth=krusha?220:65,center=100;
    if (mirrorEnabled()) {mouth=320-mouth;center=320-center;}
    *(f32*)(bubble+0x20)=1;
    *(f32*)(bubble+0x24)=mouth;
    *(f32*)(bubble+0x28)=krusha?75:180;
    *(f32*)(bubble+0x2C)=center;*(f32*)(bubble+0x30)=110;
    *(Mtx**)(bubble+0x34)=matrices;
    gSPDisplayList(dl++,(void*)0x01000118);
    dl->words.w0=0xDA380007;dl->words.w1=0x020000C0;dl++;
    dl->words.w0=0xE3000A01;dl->words.w1=0;dl++;
    dl->words.w0=0xE200001C;dl->words.w1=0x00504240;dl++;
    gDPSetCombineMode(dl++,G_CC_MODULATEIA_PRIM,G_CC_MODULATEIA_PRIM);
    /* Native smooth-shading bit; the SDK value would enable front culling. */
    dl->words.w0=0xD9000000;dl->words.w1=0x00200004;dl++;
    s32 frame=(ObjectModel2Timer>>1)&7;
    dl=((Gfx*(*)(Gfx*,void*,s16))0x806A3E9C)(dl,bubble,frame);
    f32 matrix[4][4];
    guScaleF(matrix,7.5f,7.5f,1);
    matrix[3][0]=center*4-360;matrix[3][1]=200;
    guMtxF2L(matrix,matrices);
    dl=((Gfx*(*)(Gfx*,Mtx*,u8,s32))0x806A3C6C)(dl,matrices,150,frame);
    /* The same blue native font6 as ordinary conversations. Full-line
     * widths keep the left edge fixed as each prefix is revealed. */
    Gfx*(*print)(Gfx*,s16,s16,s16,char*,u32)=(void*)0x806FC530;
    u32 remaining=text_clock/4;
    s32(*width)(s16,char*)=(void*)0x806FBD5C;
    s32 rows=0;for (int i=1;i<6;i++) if (text[i]) rows++;
    for (int i=1;i<6;i++) if (text[i]) {
        char prefix[96];u32 n=length(text[i]),shown=remaining<n?remaining:n;
        for (u32 j=0;j<shown;j++) prefix[j]=text[i][j];
        prefix[shown]=0;
        remaining-=shown;
        if (shown) {
            guScaleF(matrix,.65f,.65f,1);
            matrix[3][0]=center*4-1.3f*width(6,(char*)text[i]);
            matrix[3][1]=440-rows*22+(i-1)*44;
            guMtxF2L(matrix,matrices+9+i);
            dl->words.w0=0xDA380003;dl->words.w1=(u32)(matrices+9+i)&0x1FFFFFFF;dl++;
            gDPSetPrimColor(dl++,0,0,40,40,255,255);
            dl=print(dl,6,0,0,prefix,0);
        }
    }
    return dl;
}
void krushaPrisonSceneInput(unsigned int buttons) {if(context() && begun) held_buttons=buttons;}
int krushaPrisonSceneTick(void) {
    if (!context() || !begun) return 1;
    if (ObjectModel2Timer<last_timer) {krushaPrisonSceneReset();return 1;}
    last_timer=ObjectModel2Timer;
    if (finished) return ++age>30;
    ((void(*)(void*,void*,u8))0x8068C350)(draw,Player,3);
    age++;
    if (voice_cooldown) voice_cooldown--;
    if (voiced_page!=page) {
        voiced_page=page;
        if (!empty && lines()[0][0]=='K' && !voice_cooldown && alive(0)) {
            u16 cue=(!intro || (page&2)) ? 0x275 : 0x266;
            playSound(cue,0x3FFF,63.0f,1.0f,0,0);
            krushaPrisonDialogueTrace[1]++;krushaPrisonDialogueTrace[2]=cue;
            voice_cooldown=90;
        }
    }
    krushaPrisonDialogueTrace[3]=voice_cooldown;
    /* Native textbox convention: held A accelerates, held Z slows. B has
     * deliberately no skip/close action in this recruitment conversation. */
    text_clock+=(held_buttons&0x2000)?1:held_buttons==0x8000?6:2;
    krushaPrisonSceneTrace[1]=page;krushaPrisonSceneTrace[2]=age;
    krushaPrisonSceneTrace[3]=(empty?2:intro?0:1);
    krushaPrisonSceneTrace[6]=krushaRecruitmentKeys(file);krushaPrisonSceneTrace[7]=krushaRecruitmentLocks(file);
    krushaPrisonSceneTrace[10]=text_clock;krushaPrisonSceneTrace[11]=characters();
    u32 duration=characters()*4+120;if (duration<180) duration=180;
    if (text_clock>=duration && age>=45) {
        text_clock=0;age=0;
        if (intro && page==5) {krushaRecruitmentMarkIntro(file);krushaPrisonSceneTrace[5]++;}
        page++;
        u32 pages=empty?1:intro?7:krushaRecruitmentKeys(file)?2:1;
        if (!empty && intro && krushaRecruitmentKeys(file)) pages++;
        if (page>=pages) {finished=1;age=0;}
    }
    return 0;
}
