#include "../include/common.h"
#include "../include/recruitment_assets.generated.h"

/* R02: native collision owns the shell/landing. This is an entrance detector,
 * not a map transition. The inner readiness backstop stays until R03 exists.
 * Trace is transient diagnostic RAM, never a save/quest or unlock flag.
 * [0] accepted approaches, [1] safe recoveries, [2] armed, [3] eligible,
 * [4] latched, [5] frame, [6] character, [7] native transformation. */
volatile u32 krushaPrisonTrace[8];
volatile f32 krushaPrisonDistance[3]; /* side, outward depth, foot height */
static void* owner;
static u32 owner_id;
static u32 last_frame;
static f32 last_depth;
static u8 armed,latched;

static int valid(void* p,u32 n) {return (u32)p>=0x80000000 && (u32)p<=0x80800000-n;}
static f32 absolute(f32 x) {return x<0 ? -x : x;}
static void reset(void) {owner=0;armed=latched=0;krushaPrisonTrace[2]=krushaPrisonTrace[3]=krushaPrisonTrace[4]=0;}

static int exteriorLoaded(void) {
    ModelTwoData* objects=ObjectModel2Pointer;
    s32 count=ObjectModel2Count_Dupe;
    if (count<1 || count>1000 || !valid(objects,count*sizeof(ModelTwoData))) return 0;
    for (s32 i=0;i<count;i++) if (objects[i].object_id==RECRUITMENT_OBJECT_ID &&
        objects[i].object_type==RECRUITMENT_MODEL_TYPE) return 1;
    return 0;
}

static void recover(u8* p) {
    /* Native detach, then move only this player out of our aperture before
     * normal-size recovery. No crystal refill, forced action or scale write. */
    ((void (*)(void*))0x80672C30)(p);
    for (s32 base=0x7C;base<=0x88;base+=0xC) {
        *(f32*)(p+base)=RECRUITMENT_DOOR_SAFE_X;
        *(f32*)(p+base+4)=RECRUITMENT_DOOR_Y;
        *(f32*)(p+base+8)=RECRUITMENT_DOOR_SAFE_Z;
    }
    *(f32*)(p+0xB8)=0;
    *(f32*)(p+0xC0)=0;
    krushaPrisonTrace[1]++;
    armed=latched=0;
    krushaPrisonTrace[2]=krushaPrisonTrace[4]=0;
}

void krushaPrisonTick(void) {
    u32 frame=*(u32*)0x8076A064;
    u8* p=(u8*)Player;
    if (!krushaEnabled() || !DetectAdventure() || CurrentMap!=34 ||
        ObjectModel2Timer<5 || !valid(p,0x178)) {reset();last_frame=frame;return;}
    f32 x=*(f32*)(p+0x7C),y=*(f32*)(p+0x80),z=*(f32*)(p+0x84);
    f32 dx=x-RECRUITMENT_DOOR_X,dz=z-RECRUITMENT_DOOR_Z;
    if (absolute(dx)>45 || absolute(dz)>45 || !exteriorLoaded()) {reset();last_frame=frame;return;}
    f32 side=dx*RECRUITMENT_DOOR_TX+dz*RECRUITMENT_DOOR_TZ;
    f32 depth=dx*RECRUITMENT_DOOR_NX+dz*RECRUITMENT_DOOR_NZ;
    krushaPrisonDistance[0]=side;krushaPrisonDistance[1]=depth;
    krushaPrisonDistance[2]=y-RECRUITMENT_DOOR_Y;
    u8* cc=*(u8**)0x807FC924;
    u8* data=*(u8**)(p+0x174);
    if (!valid(cc,0x2C4) || !valid(data,0x1D0)) {reset();last_frame=frame;return;}
    if (owner!=p || owner_id!=*(u32*)(p+0x54) || frame<last_frame) {
        armed=latched=0;last_depth=depth;owner=p;owner_id=*(u32*)(p+0x54);
    }
    if (frame==last_frame) return;
    last_frame=frame;
    krushaPrisonTrace[5]=frame;krushaPrisonTrace[6]=Character;
    krushaPrisonTrace[7]=cc[0x2C0];
    if ((TBVoidByte&3) || CutsceneActive || LZFadeoutProgress>0 || IsAutowalking) {
        armed=0;last_depth=depth;krushaPrisonTrace[2]=krushaPrisonTrace[3]=0;return;
    }
    int tiny=Character==3 && *(u32*)(p+0x58)==5;
    /* Native Mini Monkey is0 (normal1, Hunky2), verified in806D0468.
     * Also require completed native small-scale interpolation and crystals. */
    int small=tiny && cc[0x2C0]==0 && *(f32*)(data+0x1CC)>.045f &&
        *(f32*)(data+0x1CC)<.055f && CollectableBase.Crystals>0;
    int height=y>=RECRUITMENT_DOOR_Y-.5f && y<=RECRUITMENT_DOOR_Y+1.5f;
    int moving=p[0x154]==12 || p[0x154]==13 || p[0x154]==14;
    int eligible=small && height && moving;
    krushaPrisonTrace[3]=eligible;
    if (tiny && (!small || CollectableBase.Crystals<=0) && absolute(side)<6.8f &&
        depth<5.0f && depth>-14 && y>RECRUITMENT_DOOR_Y-5 && y<RECRUITMENT_DOOR_Y+15) {
        recover(p);last_depth=15;return;
    }
    if (depth>7 || absolute(side)>10 || !height) latched=0;
    if (!eligible) armed=0;
    else if (depth>4 && depth<25 && absolute(side)<6) armed=1;
    if (armed && !latched && eligible && absolute(side)<3.5f &&
        last_depth>4.0f && depth<=4.0f && depth>-4) {
        /* Native collision pads the actor beyond its visible mesh. Accept
         * inward capsule contact in the first4 world units of the aperture,
         * rather than requiring the feet to cross a blocked wall plane. */
        krushaPrisonTrace[0]++;latched=1;armed=0;
    }
    krushaPrisonTrace[2]=armed;krushaPrisonTrace[4]=latched;
    last_depth=depth;
}

/* Prevent changing identity inside the owned doorway between entry detection
 * and the future R03 transfer. Ordinary outdoor tagging is unchanged. */
s32 krushaPrisonBusy(void) {
    return krushaEnabled() && DetectAdventure() && CurrentMap==34 && Character==3 &&
        owner && owner==Player && owner_id==*(u32*)((u8*)Player+0x54) && absolute(krushaPrisonDistance[0])<6.8f &&
        krushaPrisonDistance[1]<5 && krushaPrisonDistance[1]>-14 &&
        krushaPrisonDistance[2]>-5 && krushaPrisonDistance[2]<15;
}
