#pragma GCC optimize("Os","no-strict-aliasing")
#include "../include/common.h"
#include "../include/krusha_prison_scene.h"
#include "../include/krusha_recruitment.h"
#include "../include/krusha_progress.h"
#include "../include/recruitment_scene.generated.h"
#include "../include/krusha_prison_turnin.h"

/* At most13 bounded native displays, never K. Lumsy's story controllers.
 * Map216 has no native actors of these classes. Elsewhere dispatch is exact.
 * The native map destructor owns actor/model lifetimes; handles include UID. */
static struct {u8* actor;u32 uid;} displays[13];
static u32 active,file,page,age,text_clock,held_buttons,finished,empty,intro,last_timer,built,begun,voiced_page,voice_cooldown;
static u32 sequence; /*0 dialogue,1 independent key/lock motion,2 report,3 rescue,4 banana departure*/
/* Enlarge only the owned cage assembly about its fixed floor center.
 * Tiny, the native room and camera are independent of this display group. */
#define ASSEMBLY_SCALE 1.06f
#define CAPTIVE_YAW 2002 /*Reverse the previous18 degrees:1900 plus9.*/
static f32 sceneX(f32 x) {return 900+(x-900)*ASSEMBLY_SCALE;}
static f32 sceneY(f32 y) {return 95+(y-95)*ASSEMBLY_SCALE;}
static f32 sceneZ(f32 z) {return 1700+(z-1700)*ASSEMBLY_SCALE;}
volatile u32 krushaPrisonSceneTrace[12];
/* departure started,age,native banana progress,captive hidden,native finish */
volatile u32 krushaPrisonDepartureTrace[5];
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
    for (int i=0;i<13;i++) if (displays[i].actor==actor && alive(i)) return i;
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
        *(s16*)(a+0xE6)=CAPTIVE_YAW;return;
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
    x=sceneX(x);y=sceneY(y);z=sceneZ(z);scale*=ASSEMBLY_SCALE;
    u8* a=*(u8**)0x807FBB44;displays[i].actor=a;displays[i].uid=*(u32*)(a+0x54);
    *(f32*)(a+0x7C)=x;*(f32*)(a+0x80)=y;*(f32*)(a+0x84)=z;
    u8* anim=*(u8**)(a+4);
    for (int j=0;j<3;j++) *(f32*)(anim+0x34+j*4)=scale;
    /* Owned cage: original round X/Z footprint, height reduced20%.
     * Native cage actors elsewhere and Mini physics are untouched. */
    if (i==1) *(f32*)(anim+0x38)=2.8424f*ASSEMBLY_SCALE;
    *(s16*)(a+0xE6)=angle;
    *(s16*)(a+0x128)=255;  /* shadow opacity, not distance */
    *(s16*)(a+0x12A)=3000; /* native display draw distance */
    /* These owned cutscene displays use the native no-distance/chunk-
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
     * outside on an existing native floor. Move the captive half of the
     * earlier264-unit step forward:132 WORLD units after group scaling. */
    if (!empty && !spawn(0,316,0xDB,900,95,1795.4717f,8.415f,CAPTIVE_YAW)) finished=1;
    if (!spawn(1,115,RECRUITMENT_CAGE_MODEL_TOKEN,900,95,1700,3.553f,0)) finished=1;
    u32 locks=krushaRecruitmentLocks(file);
    /* Five equal cells along the front rail. Align actual body vertices,
     * not bone2's offset origin: body center=root+(0.117,72.759,0).
     * Rail centerY211.537; follow its original round frontZ502.641.
     * Keep saved-owner gaps so presenting a key never reorders colors. */
    for (int i=0;i<5;i++) if (!(locks&(1u<<i)) &&
        !spawn(i+2,334,RECRUITMENT_LOCK_MODEL_TOKEN+i,
            1294.9758f-i*197.5464f,138.7783f,503.639f,.48f,2048)) finished=1;
    u32 pending=krushaPrisonPendingKeys(file);
    for (int i=0;i<5;i++) if ((pending&(1u<<i)) &&
        !spawn(i+7,334,RECRUITMENT_TURN_KEY_MODEL_TOKEN+i,
            1294.9758f-i*197.5464f,-2000,503.639f,.48f,2048)) finished=1;
    krushaPrisonSceneTrace[8]=ObjectModel2Timer;
}
void krushaPrisonScenePrepare(unsigned int f) {
    if (active || CurrentMap!=216 || !DetectAdventure() || f!=krushaProgressActiveFile() || Character!=3 || !Player) return;
    /* Wait for THIS map's live player, not an exterior pointer carried
     * through the map/heap transfer. Preparation still precedes fade-in. */
    int found=0;
    for (int n=0;n<ActorCount && n<256;n++) if ((void*)ActorArray[n]==Player) {found=1;break;}
    if (!found) return;
    for (int i=0;i<13;i++) {displays[i].actor=0;displays[i].uid=0;}
    active=1;file=f;page=age=text_clock=held_buttons=finished=built=begun=0;last_timer=ObjectModel2Timer;
    sequence=0;
    for (int i=0;i<5;i++) krushaPrisonDepartureTrace[i]=0;
    krushaPrisonTurnBegin(f);
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
static const char* held[6]={"TINY","WE'VE ALREADY FOUND","SOME. LET'S TRY THEM.",0,0,0};
static const char* more[6]={"TINY","MORE KEYS.","HOLD STILL!",0,0,0};
static const char* release[3][6]={
    {"KRUSHA","FREE AT LAST!","I'M WITH YOU NOW.",0,0,0},
    {"KRUSHA","I CAN HELP YOU BY","COLLECTING GRAY","BANANAS.",0,0},
    {"KRUSHA","SEE YOU IN THE","TAG BARREL.",0,0,0}
};
static const char* counts[5]={"ONE LOCK LEFT.","TWO LOCKS LEFT.","THREE LOCKS LEFT.","FOUR LOCKS LEFT.","FIVE LOCKS LEFT."};
static const char* remaining[6]={"KRUSHA",0,"KEEP LOOKING!",0,0,0};
static const char* gone[6]={"TINY","HE'S OUT. BETTER","FIND THE OTHERS.",0,0,0};
static const char** lines(void) {
    if (empty) return gone;
    if (sequence==3) return release[page<3?page:2];
    if (intro && page<6) return first[page];
    if (sequence==2) {
        u32 mask=krushaRecruitmentLocks(file),count=0;
        for (int i=0;i<5;i++) if (!(mask&(1u<<i))) count++;
        remaining[1]=counts[count?count-1:0];return remaining;
    }
    if (krushaPrisonPendingKeys(file)) return intro?held:more;
    return again;
}
static void poseWorld(int i,f32 x,f32 y,f32 z,f32 scale,s16 yaw) {
    if (!alive(i)) return;
    u8* a=displays[i].actor;u8* anim=*(u8**)(a+4);
    *(f32*)(a+0x7C)=x;*(f32*)(a+0x80)=y;*(f32*)(a+0x84)=z;
    *(s16*)(a+0xE6)=yaw;
    for (int j=0;j<3;j++) *(f32*)(anim+0x34+j*4)=scale;
}
static void pose(int i,f32 x,f32 y,f32 z,f32 scale,s16 yaw) {
    poseWorld(i,sceneX(x),sceneY(y),sceneZ(z),scale*ASSEMBLY_SCALE,yaw);
}
static void present(void) {
    u32 phase=krushaPrisonTurnTrace[0],owner=krushaPrisonTurnTrace[1];
    f32 timer=krushaPrisonTurnTrace[2],rise=0,factor=1;
    if (phase==PRISON_LOCK_OPEN) {factor=1-timer/PRISON_OPEN_FRAMES;rise=timer*4;}
    if (phase==PRISON_LOCK_COMMIT || phase==PRISON_SELECT) factor=.0001f;
    for (int i=0;i<5;i++) {
        f32 x=1294.9758f-i*197.5464f;
        if (krushaRecruitmentLocks(file)&(1u<<i)) pose(i+2,x,-2000,503.639f,.0001f,2048);
        else if (i==owner && phase==PRISON_LOCK_OPEN) pose(i+2,x,138.7783f+rise,503.639f,.48f*factor,2048);
        pose(i+7,x,-2000,503.639f,.48f,2048);
    }
    if (phase==PRISON_KEY_FLY) {
        f32 p=timer/PRISON_FLY_FRAMES;
        /* Keep the approved key origin while Tiny moves another half-step
         * left. This is intentionally independent of her render staging. */
        f32* pos=(f32*)((u8*)Player+0x7C);
        f32 x=pos[0]+1090,y=pos[1],z=pos[2]-430;
        poseWorld(owner+7,x+(sceneX(1294.9758f-owner*197.5464f)-x)*p,
            y+(sceneY(138.7783f)-y)*p,z+(sceneZ(503.639f)-z)*p,.48f*ASSEMBLY_SCALE,2048);
    } else if (phase==PRISON_KEY_TURN || phase==PRISON_LOCK_OPEN) {
        pose(owner+7,1294.9758f-owner*197.5464f,138.7783f+rise,503.639f,.48f*factor,2048);
    }
}
void krushaPrisonKeyBones(void* actor) {
    u32 phase=krushaPrisonTurnTrace[0],owner=krushaPrisonTurnTrace[1];
    if (!context() || owner>=5 || displays[owner+7].actor!=actor || !alive(owner+7)) return;
    if (phase!=PRISON_KEY_TURN && phase!=PRISON_LOCK_OPEN) return;
    /* Native build has just selected and rebuilt THIS frame's bone bank.
     * Bone3 origin is the insertion anchor; local Z is the long shaft. Rotate only
     * its X/Y basis so the shaft axis and anchor stay bit-exactly fixed in the lock.
     * Changing actor yaw/roll would swing the whole offset skeleton around
     * the actor root, rather than rotate a physical key in its keyhole. */
    Mtx* bones=*(Mtx**)((u8*)actor+8);
    if (!valid(bones,256)) return;
    f32 matrix[4][4];Mtx turned;
    f32 angle=-1.570796327f;
    if (phase==PRISON_KEY_TURN) angle*=krushaPrisonTurnTrace[2]/(f32)PRISON_TURN_FRAMES;
    extern f32 sinf(f32),cosf(f32);
    f32 sine=sinf(angle),cosine=cosf(angle);
    guMtxL2F(matrix,bones+3);
    for (int i=0;i<3;i++) {
        f32 x=matrix[0][i],y=matrix[1][i];
        matrix[0][i]=cosine*x+sine*y;
        matrix[1][i]=-sine*x+cosine*y;
    }
    guMtxF2L(matrix,&turned);
    for (int row=0;row<2;row++) for (int col=0;col<3;col++) {
        int i=row*4+col;
        ((s16*)(bones+3))[i]=((s16*)&turned)[i];
        ((u16*)(bones+3))[i+16]=((u16*)&turned)[i+16];
    }
    osWritebackDCache(bones+3,64);
}
static u32 length(const char* text) {
    u32 n=0;if (text) while (n<95 && text[n]) n++;return n;
}
static u32 characters(void) {
    const char** text=lines();u32 n=0;for(int i=1;i<6;i++) n+=length(text[i]);return n;
}
static Gfx* draw(Gfx* dl,void* actor) {
    if (!context() || !begun || (TBVoidByte&3) || finished || sequence==1 || sequence==4) return dl;
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
    f32 mouth=krusha?220:80,mouth_y=krusha?75:215,center=100;
    if (mirrorEnabled()) {mouth=320-mouth;center=320-center;}
    if (!krusha) {
        /* Tiny's rendered head bone, including the existing staging shift.
         * Project through this frame's owned view, so Wide/Mirror follow her
         * actual head rather than an approximate screen-space anchor. The
         * native first pointer dot lies8% of the way back toward the cloud. */
        u8* info=*(u8**)((u8*)Player+0x140);
        if (valid(info,0x8C)) {
            u8 bank=*(u8*)0x807444FC^(*(u32*)(info+0x88)!=*(u32*)0x8076A064);
            Mtx* bones=*(Mtx**)(info+0x74+bank*4);
            if (valid(bones,256)) {
                f32 head[4][4],x,y;guMtxL2F(head,bones+3);
                ((s32(*)(f32,f32,f32,f32*,f32*,s32,f32,s32))0x80626F8C)(head[3][0],head[3][1],head[3][2],&x,&y,0,1,0);
                if (x>0 && x<320 && y>0 && y<240) {
                    /* The cloud uses the contracted HUD orthographic view;
                     * the projected head is already a world-screen point.
                     * Undo that extra contraction just for the tail target. */
                    if (*(u8*)0x807444C0) x=160+(x-160)*(4.0f/3.0f);
                    mouth=(x-.08f*center)/.92f;mouth_y=(y-8.8f)/.92f;
                }
            }
        }
    }
    *(f32*)(bubble+0x20)=1;
    *(f32*)(bubble+0x24)=mouth;
    *(f32*)(bubble+0x28)=mouth_y;
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
    if (sequence==3 && page==1 && text_clock>=characters()*4) {
        /* Same eight RGBA16 silver CB frames as the existing pickup/HUD.
         * Immediate native image drawing uses its bounded frame cache;
         * no per-frame sprite actors or texture allocations are introduced. */
        extern Gfx* widescreenImage(Gfx*,u16,s32,s32,s32,s32,s16,s16,f32,f32,s32,f32);
        gDPPipeSync(dl++);
        gDPSetPrimColor(dl++,0,0,255,255,255,255);
        gDPSetCombineMode(dl++,G_CC_MODULATEIA_PRIM,G_CC_MODULATEIA_PRIM);
        dl->words.w0=0xDA380007;dl->words.w1=0x020000C0;dl++;
        dl->words.w0=0xDA380003;dl->words.w1=0x02000180;dl++;
        dl=widescreenImage(dl,7202+((ObjectModel2Timer>>2)&7),0,2,44,44,center*4,560,2.4f,2.4f,180,0);
    }
    return dl;
}
static void hideCaptive(void) {
    if (!alive(0)) return;
    pose(0,900,-2000,1795.4717f,.0001f,CAPTIVE_YAW);
    displays[0].actor[0x16D]=0;*(s16*)(displays[0].actor+0x128)=0;
    krushaPrisonDepartureTrace[3]=1;
}
static void departure(void) {
    krushaPrisonDepartureTrace[1]=++age;
    if (alive(12)) {
        u8* banana=displays[12].actor;
        u32 progress=banana[0x155];krushaPrisonDepartureTrace[2]=progress;
        /* Native rescue banana script298 advances its OWN progress at
         * closure and completion. Do not run actor60/225's callback: those
         * mutate the real player/old cutscene controller. */
        if (progress==1) {hideCaptive();banana[0x155]=2;}
        if (progress>=3) {
            banana[0x16D]=0;*(s16*)(banana+0x128)=0;
            pose(12,900,-2000,1795.4717f,.0001f,CAPTIVE_YAW);
            hideCaptive();krushaPrisonDepartureTrace[4]=1;finished=1;age=0;return;
        }
    }
    /* Fail closed if a native resource cannot be constructed; never trap
     * Tiny after the durable rescue transaction has already succeeded. */
    if (age>180) {hideCaptive();finished=1;age=0;}
}
void krushaPrisonSceneInput(unsigned int buttons) {if(context() && begun) held_buttons=buttons;}
int krushaPrisonSceneTick(void) {
    if (!context() || !begun) return 1;
    if (ObjectModel2Timer<last_timer) {krushaPrisonSceneReset();return 1;}
    last_timer=ObjectModel2Timer;
    if (finished) return ++age>30;
    if (sequence==4) {departure();return 0;}
    ((void(*)(void*,void*,u8))0x8068C350)(draw,Player,3);
    if (sequence==1) {
        int done=krushaPrisonTurnTick();present();
        if (done) {
            sequence=krushaRecruitmentRecruited(file)?3:2;
            page=sequence==3?0:page+1;age=text_clock=0;
        }
        return 0;
    }
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
    /* Halve only the fully revealed gray-banana interval, not the reading
     * time or native A/Z speech pacing. */
    u32 duration=characters()*4+((sequence==3 && page==1)?180:120);if (duration<180) duration=180;
    if (text_clock>=duration && age>=45) {
        text_clock=0;age=0;
        if (intro && page==5) {krushaRecruitmentMarkIntro(file);krushaPrisonSceneTrace[5]++;}
        if (sequence==3) {
            if (page<2) page++;
            else {
                sequence=4;krushaPrisonDepartureTrace[0]=1;
                if (alive(0)) krushaPlayActorAnimation(displays[0].actor,0xEA);
                /* Closure used to hide him about16 native frames later.
                 * Retire now, half a second earlier, before the forming
                 * envelope can intersect his larger captive mesh. */
                hideCaptive();
                /* Native banana-port/rescue model152 and script298, sized
                 * to this captive. One owned display; native teardown owns
                 * all its model/animation resources exactly once. */
                if (spawn(12,115,0x98,900,95,1795.4717f,8.415f,CAPTIVE_YAW)) {
                    krushaPlayActorAnimation(displays[12].actor,0x298);
                    *(void**)(displays[12].actor+0x11C)=displays[0].actor;
                    *(s16*)(displays[12].actor+0x128)=0;
                }
            }
        }
        else if (sequence==2 || empty) finished=1;
        else if (intro && page<6) {
            page++;
            if (page==6 && !krushaPrisonPendingKeys(file)) sequence=2;
        } else if (krushaPrisonPendingKeys(file)) {
            sequence=1;page++;krushaPrisonTurnBegin(file);
        } else finished=1;
    }
    return 0;
}
