#include "../include/common.h"
#include "../include/krusha_progress.h"

/* Native unused bonus entry2 resolves flag1C4. Use it only as a token in the
 * new barrel's stock machinery; private slot0 remains the actual saved reward.
 * No global flag hook, new flag stride or out-of-range flag is introduced. */
u8* m4DroppedBonus;
u32 m4DroppedBonusID;
u32 m4CollectingBonus;
s32 m4BonusPhysicalID=-1;
volatile u32 m4BonusTrace[8]={0};
static int last_map=-1;
static u32 last_frame;

static int claimed(void) { return krushaProgressRead(*(u8*)0x807467C8,KRUSHA_GB_BIT,1); }

int m4PrivateBarrel(void* actor) {
    s16 (*spawner)(void*)=(void*)0x80688E68;
    return CurrentMap==7 && actor && *(u32*)((u8*)actor+0x58)==28 && spawner(actor)==610;
}

int m4BonusCheckFlag(s16 flag,u8 type) {
    if (flag==0x1C4 && type==0 && CurrentMap==7) return claimed();
    return checkFlag(flag,type);
}

void m4BonusEligibility(void) {
    u8* actor=*(u8**)0x807FBB40;
    void (*native)(void)=(void*)0x8068086C;
    if (!m4PrivateBarrel(actor)) { native();return; }
    u8* data=Player ? *(u8**)((u8*)Player+0x174) : 0;
    if (krushaEnabled() && DetectAdventure() && Character==5 && data && !data[0xCA]) {
        *(u32*)(actor+0x60)|=0x8000;
        *(u16*)(actor+0x132)=1;
    } else {
        *(u32*)(actor+0x60)&=~0x8000;
        *(u16*)(actor+0x132)=4;
        *(u16*)(actor+0x128)=0x7F;
    }
}

void m4BonusBarrelUpdate(void) {
    u8* actor=*(u8**)0x807FBB40;
    void (*native)(void)=(void*)0x806809F0;
    if (m4PrivateBarrel(actor)) {
        if (!krushaEnabled() || !DetectAdventure() || claimed()) {
            void (*delete)(void*)=(void*)0x806782C0;delete(actor);return;
        }
        m4BonusTrace[0]++;m4BonusTrace[1]=actor[0x154];
    }
    native();
}

void m4BonusGoldUpdate(void) {
    u8* actor=*(u8**)0x807FBB40;
    void (*native)(void)=(void*)0x806A734C;
    u8* params=*(u8**)(actor+0x124);
    u8* data=*(u8**)(actor+0x174);
    /* Spawn parameters are floats, even the flag. Identify the very first
     * update: the native collector can convert this actor before a second. */
    s16 flag=(*(u32*)(actor+0x60)&0x10) ? *(s16*)(data+0xA) : (s16)*(f32*)(params+8);
    if (CurrentMap==7 && flag==0x1C4) {
        if (!krushaEnabled() || claimed()) {
            void (*delete)(void*)=(void*)0x806782C0;delete(actor);return;
        }
        m4DroppedBonus=actor;m4DroppedBonusID=*(u32*)(actor+0x54);
        m4BonusTrace[2]++;
    }
    native();
}

void m4BonusTick(void) {
    u32 frame=*(u32*)0x8076A064;
    if (CurrentMap!=last_map || frame<last_frame) {m4DroppedBonus=0;m4BonusPhysicalID=-1;m4CollectingBonus=0;last_map=CurrentMap;}
    last_frame=frame;
    if (m4DroppedBonus) {
        int found=0,count=*(u16*)0x807FBB34;u32* actors=(void*)0x807FB930;
        if (count<=256) for (int i=0;i<count;i++) {
            u8* actor=(void*)actors[i*2];
            if (actor==m4DroppedBonus && *(u32*)(actor+0x54)==m4DroppedBonusID) found=1;
        }
        if (!found) m4DroppedBonus=0;
    }
}

void m4BonusInstall(void) {
    void (**functions)(void)=(void*)0x8074C0A0;
    functions[28]=m4BonusBarrelUpdate;functions[45]=m4BonusGoldUpdate;
    /* Existing unused entry only: native GB owner lookup now returns actor7. */
    *(u8*)0x80755F56=7;
    osWritebackDCache((void*)0x80755F56,1);
    osWritebackDCache(functions+28,4);osWritebackDCache(functions+45,4);
}
