#include "../include/common.h"
#include "../include/krusha_progress.h"
#include "../include/m4_rewards.generated.h"

extern void m4NativeCollectEffect(s16,u8);
extern void m4BonusTick(void);
extern s32 m4BonusPhysicalID;

static s32 reward_map=-1;
static u32 started,effect_at;
static void* owner;
static u8 cage_open;
volatile u32 m4RewardTrace[8]={0};
static u32 frame(void) { return *(u32*)0x8076A064; }

static int reward(u16 map,u16 id) {
    for (int i=0;i<sizeof(m4Rewards)/sizeof(m4Rewards[0]);i++)
        if (m4Rewards[i].map==map && m4Rewards[i].object_id==id) return m4Rewards[i].reward;
    return -1;
}

int m4SetupHidden(s32 map,s32 id) {
    if (map==7 && (id==M4_GATE_ID || id==M4_SWITCH_ID))
        return !krushaEnabled() || !DetectAdventure() || krushaProgressRead(*(u8*)0x807467C8,KRUSHA_GB_BIT+1,1);
    int slot=reward(map,id);
    if (slot<0) return -1;
    return !krushaEnabled() || !DetectAdventure() ||
        krushaProgressRead(*(u8*)0x807467C8,KRUSHA_GB_BIT+slot,1);
}

int m4VictoryActive(void) { return reward_map==CurrentMap && owner==Player && owner; }
int m4RewardBusy(void) { return m4VictoryActive(); }

void m4RewardsTick(void) {
    m4BonusTick();
    cage_open=0;
    if (CurrentMap==7 && krushaEnabled() && DetectAdventure()) {
        s16 runtime=*(s16*)(0x807F6240+2*M4_SWITCH_ID);
        s16 (*indexOf)(s16)=(void*)0x80659470;
        s16 index=runtime>=0 ? indexOf(runtime) : -1;
        ModelTwoData* objects=ObjectModel2Pointer;
        if (index>=0 && index<ObjectModel2Count_Dupe && objects[index].object_id==M4_SWITCH_ID) {
            u8* script=objects[index].behaviour_pointer;
            if (script && script[0x48]>=2) cage_open=1;
        }
    }
    if (reward_map<0) return;
    if (CurrentMap!=reward_map || Player!=owner || Character!=5 || !krushaEnabled() ||
        frame()<started || frame()-started>300 ||
        (effect_at && frame()-effect_at>12 && Player->control_state!=0x70)) {
        reward_map=-1;owner=0;
    }
}

int m4PickupAllowed(s16 object_id,u8 player,u16 type) {
    if (type!=9) return -1;
    if (!krushaEnabled() || !DetectAdventure() || Character!=5 || player || !Player) return 0;
    s16 (*setupId)(s16)=(void*)0x8063D990;
    int slot=(CurrentMap==7 && object_id==m4BonusPhysicalID) ? 0 : reward(CurrentMap,setupId(object_id));
    if (slot<0) return 0;
    if (slot==1 && !cage_open) return 0;
    u8 file=*(u8*)0x807467C8;
    if (krushaProgressRead(file,KRUSHA_GB_BIT+slot,1)) return 0;
    krushaProgressWrite(file,KRUSHA_GB_BIT+slot,1,1);
    MovesBase[5].gb_count[0]=krushaProgressGoldenBananas(file,0);
    reward_map=CurrentMap;owner=Player;started=frame();effect_at=0;
    m4RewardTrace[0]++;m4RewardTrace[1]=slot;m4RewardTrace[2]=object_id;
    void (*hud)(u8)=(void*)0x806F8278;
    void (*save)(void)=(void*)0x8060DEC8;
    hud(0);save();
    return 1;
}

void m4CollectEffect(s16 type,u8 player) {
    if (type==9) {
        m4RewardTrace[3]++;
        if (m4VictoryActive() && Character==5) {
            effect_at=frame();m4NativeCollectEffect(0x74,player);
        }
        return;
    }
    m4NativeCollectEffect(type,player);
}
