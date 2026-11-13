#include "../include/common.h"
#include "../include/krusha_progress.h"
#include "../include/m5_campaign.h"
#include "../include/m4_rewards.generated.h"

extern void m4NativeCollectEffect(s16,u8);
extern void m4BonusTick(void);
extern s32 m4BonusPhysicalID;
extern s32 m4EncounterPickupID;
extern void m4EncounterTick(void);
extern const void* krushaCageHintSprite(void);

static s32 reward_map=-1;
static u32 started,effect_at;
static u32 pickup_frame;
static void* pickup_owner;
static s32 pickup_map=-1;
static void* owner;
static u8 cage_open;
volatile u32 m4RewardTrace[16]={0};
static u32 frame(void) { return *(u32*)0x8076A064; }

/* Native world sprites normally billboard toward the camera. Give only the
 * cage decal a complete world matrix, laying its XY quad flat on the roof.
 * Mode3 tells the native updater the matrix is complete (no billboard).
 * The one-frame descriptor is freed normally on the following update. */
static void cageHintMatrix(u8* sprite,u8* done) {
    f32 s=*(f32*)(sprite+0x360);
    f32 matrix[4][4]={{s,0,0,0},{0,0,-s,0},{0,1,0,0},
        {*(f32*)(sprite+0x340),*(f32*)(sprite+0x344),*(f32*)(sprite+0x348),1}};
    guMtxF2L(matrix,(Mtx*)(sprite+0x128+64*(*(u8*)0x807444FC)));
    sprite[0x32C]=3;
}

/* Model2's render subtype is separate from its pickup/flag identity. Native
 * 80636FFC rotates render subtype74 by ten degrees per draw. Keep type9 in
 * every ownership, suction and save path, but give its renderer that subtype.
 * Native GB glitter is normally registered by hardcoded setup type74; emit
 * the same sprite/settings for these private models, including dynamic drops. */
static void presentation(void) {
    if (!krushaEnabled() || !DetectAdventure() || !Player) return;
    ModelTwoData* objects=ObjectModel2Pointer;
    u8* changes=*(u8**)0x807FC924;
    s32 (*random)(void)=(void*)0x80611A44;
    int (*visible)(s16)=(void*)0x8063C2A8;
    void (*setMode)(s32)=(void*)0x807149B8;
    void (*setType)(s32)=(void*)0x80714998;
    void (*setLayer)(s32)=(void*)0x80714A28;
    void (*sprite)(void*,f32,f32,f32,f32)=(void*)0x80714CC0;
    for (int i=0;i<ObjectModel2Count_Dupe;i++) {
        if (objects[i].object_type!=9 || objects[i].unk_86!=1) continue;
        u8* model=*(u8**)((u8*)&objects[i]+0x20);
        if (!model) continue;
        *(s16*)(model+0xB4)=0x74;
        /* Native 805FC668 returns scene bit2 to select paused sprite updates.
         * Those freeze world-sprite animation/expiry unless flag1 is set.
         * Keep model bookkeeping, but do not add glitter to that frozen list. */
        if ((TBVoidByte & 2) || !visible(objects[i].runtime_id)) continue;
        f32 x=*(f32*)model,y=*(f32*)(model+4),z=*(f32*)(model+8);
        f32 dx=*(f32*)(changes+0x21C)-x;
        f32 dy=*(f32*)(changes+0x220)-y;
        f32 dz=*(f32*)(changes+0x224)-z;
        if (dx*dx+dy*dy+dz*dz>=90000 || (random()%10000)%10) continue;
        f32 scale=*(f32*)(model+0xC)*4;
        setMode(1);setType(2);setLayer(4);
        f32 sx=x+(((random()%10000)%300)/20.0f-7.5f)*scale;
        f32 sy=y+(((random()%10000)%600)/20.0f)*scale;
        f32 sz=z+(((random()%10000)%300)/20.0f-7.5f)*scale;
        sprite((void*)0x80720A7C,0.4f,sx,sy,sz);
        m4RewardTrace[4]++;
    }
}

static int reward(u16 map,u16 id) {
    for (int i=0;i<sizeof(m4Rewards)/sizeof(m4Rewards[0]);i++)
        if (m4Rewards[i].map==map && m4Rewards[i].object_id==id) return m4Rewards[i].reward;
    return -1;
}

/* Native interior caching keeps the dynamic model2 but resets map-local
 * bindings. Resolve only a live unregistered private type9, on demand. Native
 * type74 and registered static rewards (including the locked cage) are excluded.
 * runtime<0 asks whether an unclaimed drop already blocks another summon. */
s32 m4EncounterFindPickup(s16 runtime) {
    if (!m5Area(CurrentMap)) return -1;
    ModelTwoData* objects=ObjectModel2Pointer;
    for (int i=0;i<ObjectModel2Count_Dupe;i++) {
        if ((runtime<0 || objects[i].runtime_id==runtime) &&
            objects[i].object_type==9 && objects[i].unk_86==1 &&
            reward(CurrentMap,objects[i].object_id)<0) return objects[i].runtime_id;
    }
    return -1;
}

int m4SetupHidden(s32 map,s32 id) {
    const M5Area* area=m5Area(map);
    if (area && id==area->gate_id)
        /* Native cached-script restore assumes every scripted prop exists.
         * Keep these records alive; their scripts hide/disable them instead. */
        return 0;
    if (area && id==area->pad_id)
        return !krushaEnabled() || !DetectAdventure() ||
            krushaProgressRead(*(u8*)0x807467C8,KRUSHA_GB_BIT+area->world*5,1);
    int slot=reward(map,id);
    if (slot<0) return -1;
    return !krushaEnabled() || !DetectAdventure() ||
        krushaProgressRead(*(u8*)0x807467C8,KRUSHA_GB_BIT+slot,1);
}

/* Native cage collision has no gun-switch hit group. Wait for a type171's
 * FIRST native explosion frame plus a solid wall/floor contact at the cage.
 * A flying round inside a generous box used to open it before hitting
 * anything. Keep native collision, explosion/sound and deletion in control.
 * The private .33-scale body is +/-17.16XZ, roof312.67. A small contact
 * margin admits the projectile radius; the ground280 and removed chain are
 * outside this envelope. Nearby enemies/explosions cannot satisfy it. */
static int cageProjectile(void) {
    const M5Area* area=m5Area(CurrentMap);
    if (!area) return 0;
    u8* node=*(u8**)0x807FC400;
    for (int n=0;node && n<512;n++,node=*(u8**)(node+0x68)) {
        u8* actor=*(u8**)(node+0x44);
        if (!actor || *(u32*)(actor+0x58)!=171 || actor[0x154]!=1 ||
            (!actor[0xFD] && !(*(u16*)(actor+0x6A)&1))) continue;
        f32 x=*(f32*)(actor+0x7C)-area->cage[0];
        f32 y=*(f32*)(actor+0x80)-area->cage[1];
        f32 z=*(f32*)(actor+0x84)-area->cage[2];
        if (x>=-21 && x<=21 && z>=-21 && z<=21 && y>=-2 && y<=28) {
            m4RewardTrace[13]++;m4RewardTrace[14]=*(u32*)(actor+0x54);
            return 1;
        }
    }
    return 0;
}

int m4ScriptCondition(u16* instruction,s16 runtime) {
    if ((instruction[0]&0x7FFF)!=0x7FFE || (instruction[1]!=0x4D34 && instruction[1]!=0x4D35) || !m5Area(CurrentMap)) return -1;
    s16 (*setupId)(s16)=(void*)0x8063D990;
    s16 id=setupId(runtime);
    const M5Area* area=m5Area(CurrentMap);
    if (id!=area->gate_id) return -1;
    if (instruction[1]==0x4D35) return id==area->gate_id && krushaEnabled() && DetectAdventure() && cageProjectile();
    int disabled=!krushaEnabled() || !DetectAdventure() ||
        krushaProgressRead(*(u8*)0x807467C8,KRUSHA_GB_BIT+area->world*5+1,1);
    return (instruction[0]&0x8000) ? !disabled : disabled;
}

int m4VictoryActive(void) { return reward_map==CurrentMap && owner==Player && owner; }
int m4RewardBusy(void) { return m4VictoryActive(); }

/* A renderer/pickup callback can request the native GB action separately
 * from the effect callback. Tag Anywhere skips its state/animation writes,
 * but the rest of that initializer still runs and can inherit prior motion.
 * A skipped private world reward must never queue that initializer. Keep a
 * short same-player/contact token after releasing the dance/tagging token. */
int m4SkipGBAction(s16 action,void* source,u8 player) {
    if (action!=0x29 || player || Character!=5 || !krushaEnabled() ||
        !DetectAdventure() || CurrentMap!=pickup_map || Player!=pickup_owner ||
        frame()<pickup_frame || frame()-pickup_frame>12) return 0;
    m4RewardTrace[8]++;m4RewardTrace[9]=frame()-pickup_frame;
    m4RewardTrace[10]=Player->control_state;
    return StorySkip && CurrentMap!=15;
}

void m4RewardsTick(void) {
    m4BonusTick();
    m4EncounterTick();
    presentation();
    cage_open=0;
    const M5Area* area=m5Area(CurrentMap);
    if (area && frame()>1) {
        int disabled=!krushaEnabled() || !DetectAdventure() ||
            krushaProgressRead(*(u8*)0x807467C8,KRUSHA_GB_BIT+area->world*5+1,1);
        const s16 ids[1]={area->gate_id};
        s16 (*indexOf)(s16)=(void*)0x80659470;
        void (*runState)(void*,s8,s16)=(void*)0x8064199C;
        ModelTwoData* objects=ObjectModel2Pointer;
        for (int i=0;i<1;i++) {
            s16 runtime=*(s16*)(0x807F6240+2*ids[i]);
            s16 index=runtime>=0 ? indexOf(runtime) : -1;
            if (index<0 || index>=ObjectModel2Count_Dupe || objects[index].object_id!=ids[i]) continue;
            u8* script=objects[index].behaviour_pointer;
            if (!script) continue;
            /* A cached/opened button may be sleeping when its GB is claimed.
             * Wake only until native script operations have hidden it. */
            if (disabled && (script[0x60]!=1 || *(u16*)(script+0x62) || script[0x70] || script[0x71]))
                runState(script,1,0);
            if (!disabled && ids[i]==area->gate_id) {
                if (script[0x48]>=10) cage_open=1;
                else if (!(TBVoidByte & 2)) {
                    /* Match the native world-sprite clock. A new one-frame
                     * decal every paused frame cannot expire and exhausts
                     * the heap, even with the cage outside the camera view. */
                    /* Native one-frame world sprite: no extra actor or collision. */
                    void (*begin)(s32)=(void*)0x807149B8;
                    void (*mode)(s32)=(void*)0x80714998;
                    void (*layer)(s32)=(void*)0x80714A28;
                    void (*callback)(void*)=(void*)0x8071498C;
                    void (*draw)(const void*,f32,f32,f32,f32)=(void*)0x80714CC0;
                    begin(1);mode(1);layer(4);callback(cageHintMatrix);
                    /* Roof is cage origin+26.4. Clear it by0.8 to avoid
                     * z-fighting;14.4 units is larger than the old11.2. */
                    draw(krushaCageHintSprite(),0.45f,area->cage[0],area->cage[1]+27.2f,area->cage[2]);
                }
            }
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
    const M5Area* area=m5Area(CurrentMap);
    int slot=(area && (object_id==m4BonusPhysicalID || object_id==m4EncounterPickupID)) ? area->world*5 : reward(CurrentMap,setupId(object_id));
    if (slot<0 && m4EncounterFindPickup(object_id)>=0) {
        m4EncounterPickupID=object_id;slot=area->world*5;
    }
    if (slot<0) return 0;
    if (slot%5==1 && !cage_open) return 0;
    u8 file=*(u8*)0x807467C8;
    if (krushaProgressRead(file,KRUSHA_GB_BIT+slot,1)) return 0;
    krushaProgressWrite(file,KRUSHA_GB_BIT+slot,1,1);
    MovesBase[5].gb_count[slot/5]=krushaProgressGoldenBananas(file,slot/5);
    reward_map=CurrentMap;owner=Player;started=frame();effect_at=0;
    pickup_map=CurrentMap;pickup_owner=Player;pickup_frame=frame();
    m4RewardTrace[0]++;m4RewardTrace[1]=slot;m4RewardTrace[2]=object_id;
    void (*hud)(u8)=(void*)0x806F8278;
    void (*save)(void)=(void*)0x8060DEC8;
    hud(0);save();
    return 1;
}

void m4CollectEffect(s16 type,u8 player) {
    if (pickup_map==CurrentMap && Player==pickup_owner && frame()>=pickup_frame && frame()-pickup_frame<12) {
        m4RewardTrace[11]=type;m4RewardTrace[12]++;
    }
    if (type==9) {
        m4RewardTrace[3]++;
        if (m4VictoryActive() && Character==5) {
            effect_at=frame();
            if (StorySkip && CurrentMap!=15) {
                /* Tag Anywhere blanks the GB initializer in Speed Mode,
                 * including the state write. Queuing its action can therefore
                 * trap the previous running/jumping action for the music.
                 * A skipped world dance needs its music, not that action. */
                playSong(18,1.0f);
                reward_map=-1;owner=0;
            } else {
                m4NativeCollectEffect(0x74,player);
            }
        }
        return;
    }
    m4NativeCollectEffect(type,player);
}
