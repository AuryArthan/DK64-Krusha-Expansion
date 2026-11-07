#include "../include/common.h"
#include "../include/krusha_progress.h"
#include "../include/m3_kasplat.h"

extern void m3NativeKasplatInit(u8);
extern void m3NativeEnemyDrop(void*);
extern void m3NativeBlueprint(void);
extern void krushaNativeActorDelete(void*);
extern u32 m4CollectingBonus;
extern u8* m4DroppedBonus;
extern s32 m4BonusPhysicalID;

u8* m3DroppedBlueprint=0;
u32 m3DroppedBlueprintID=0;
u32 m3CollectingBlueprint=0;
static u8* pending_spawner=0;
static s16 physical_id=-1;
static int previous_map=-1;
static u32 previous_frame;
volatile u32 m3KasplatTrace[8]={0};
static unsigned int file(void) { return *(u8*)0x807467C8; }

void m3KasplatTick(void) {
    u32 frame=*(u32*)0x8076A064;
    if (CurrentMap!=previous_map || frame<previous_frame) {
        m3DroppedBlueprint=0;pending_spawner=0;physical_id=-1;m3CollectingBlueprint=0;
    }
    previous_map=CurrentMap;previous_frame=frame;
    /* Native drops queue an ActorSpawner; allocation happens on a later
     * update. Resolve only a node still in the native live list, never an
     * enemy/parent pointer after death. */
    if (pending_spawner) {
        u8* node=*(u8**)0x807FC400;
        int found=0;
        for (int i=0;node && i<512;i++,node=*(u8**)(node+0x68)) {
            if (node!=pending_spawner) continue;
            found=1;
            u8* actor=*(u8**)(node+0x44);
            if (actor && *(u32*)(actor+0x58)==78) {
                m3DroppedBlueprint=actor;m3DroppedBlueprintID=*(u32*)(actor+0x54);
                pending_spawner=0;m3KasplatTrace[1]++;
            }
            break;
        }
        if (!found) pending_spawner=0;
    }
    /* Never dereference a saved actor address after its native deletion. */
    if (m3DroppedBlueprint) {
        int present=0, count=*(u16*)0x807FBB34;
        u32* actors=(void*)0x807FB930;
        if (count<=256) for (int i=0;i<count;i++) {
            u8* actor=(void*)actors[i*2];
            if (actor==m3DroppedBlueprint && *(u32*)(actor+0x54)==m3DroppedBlueprintID) present=1;
        }
        if (!present) m3DroppedBlueprint=0;
    }
}

int m3GrayKasplat(void* actor) {
    if (!actor || CurrentMap!=7 || ((actorData*)actor)->actorType!=241) return 0;
    /* Enemy spawners are table16 records, unlike setup-actor IDs returned
     * by 80688E68. Check the tied native record and its live actor link. */
    /* Enemy actor module layout: +178 is EnemySpawner, +17C is AI state.
     * The generic actorData +180 label is not this actor's module layout. */
    u8* spawner=*(u8**)((u8*)actor+0x178);
    return (u32)spawner>=0x80000000 && (u32)spawner<0x807FFFB8 &&
        spawner[0]==61 && spawner[19]==3 && *(void**)(spawner+0x18)==actor;
}

void m3KasplatInit(u8 color) {
    u8* actor=*(u8**)0x807FBB40;
    if (!m3GrayKasplat(actor)) {
        if (krushaEnabled() && DetectAdventure() && color<5 && (*(u32*)(actor+0x60)&0x10)) {
            int (*level)(int,int)=(void*)0x805FF030;
            int world=level(CurrentMap,1);
            if (world<8) {
                static const u8 owners[5]={3,4,1,2,0};
                int (*held)(int,int,int,int)=(void*)0x80731A04;
                int uncollected=!held(0x1D5,world,world,owners[color]);
                if (actor[0x15F]!=uncollected) {
                    void (*hair)(u8)=(void*)0x806B1D78;
                    hair(uncollected ? color : 5);actor[0x15F]=uncollected;
                }
            }
        }
        m3NativeKasplatInit(color);return;
    }
    if (!krushaEnabled() || !DetectAdventure()) { krushaNativeActorDelete(actor); return; }
    int uncollected=!krushaProgressRead(file(),KRUSHA_BLUEPRINT_BIT,1);
    if (!(*(u32*)(actor+0x60)&0x10) || actor[0x15F]!=uncollected) {
        void (*hair)(u8)=(void*)0x806B1D78;
        hair(uncollected ? 6 : 5);
        actor[0x15F]=uncollected;
        m3KasplatTrace[0]++;
    }
    void (*ai)(u8)=(void*)0x806B13B4;
    ai(actor[0x15F]);
}

void m3EnemyDrop(void* enemy) {
    if (!m3GrayKasplat(enemy)) { m3NativeEnemyDrop(enemy); return; }
    if (!krushaEnabled() || pending_spawner || m3DroppedBlueprint || physical_id>=0 || krushaProgressRead(file(),KRUSHA_BLUEPRINT_BIT,1)) return;
    u8* before=*(u8**)0x807FC400;
    m3NativeEnemyDrop(enemy);
    u8* after=*(u8**)0x807FC400;
    if (after && after!=before && *(s16*)after==78-16) pending_spawner=after;
}

typedef struct {
    u32 id;u8 across,down,flags,codec;u32 rgba;
    u8 animated,table;u16 width,height,frames;u16 images[8];
} BlueprintSprite;
static const BlueprintSprite silver_blueprint={
    0x4B520120,1,1,0,2,0xFFFFFFFF,1,1,48,42,8,
    {7116,7117,7118,7119,7120,7121,7122,7123}
};

void m3Blueprint(void) {
    u8* actor=*(u8**)0x807FBB40;
    m3KasplatTick();
    if (actor!=m3DroppedBlueprint || *(u32*)(actor+0x54)!=m3DroppedBlueprintID) { m3NativeBlueprint();return; }
    if (CurrentMap!=7 || !krushaEnabled() || krushaProgressRead(file(),KRUSHA_BLUEPRINT_BIT,1)) {
        m3DroppedBlueprint=0;krushaNativeActorDelete(actor);return;
    }
    /* Native actor bounce/lifetime and owner opacity. The collector's scoped
     * owner bridge handles contact separately from this actor's update. */
    void (*native)(const void*,int)=(void*)0x806A6004;
    native(&silver_blueprint,7);
}

int m3SpawnPhysical(s16 type,f32 x,f32 y,f32 z,f32 angle,u32 flags) {
    int (*native)(s16,f32,f32,f32,f32,u32)=(void*)0x80632630;
    if (m3CollectingBlueprint) type=7;
    if (m4CollectingBonus) {
        type=9;
        /* Native bonus GBs hang at barrel height. Place this private model
         * near the actual floor so Krusha's native foot contact can take it
         * on return, through the ordinary suction/award path. */
        f32 ground=y+20;
        int (*floor)(f32,f32,f32*)=(void*)0x80667110;
        if (floor(x,z,&ground) && ground<=y && y-ground<128) y=ground+4;
    }
    int id=native(type,x,y,z,angle,flags);
    if (m3CollectingBlueprint) physical_id=id;
    if (m4CollectingBonus) m4BonusPhysicalID=id;
    return id;
}

void m3RegisterPhysical(s16 id,s16 type,s16 arg2,u8 arg3,u8 arg4,u8 arg5) {
    void (*native)(s16,s16,s16,u8,u8,u8)=(void*)0x806F50C8;
    if (m3CollectingBlueprint) type=7;
    if (m4CollectingBonus) type=9;
    native(id,type,arg2,arg3,arg4,arg5);
    if (m4CollectingBonus) {m4DroppedBonus=0;m4CollectingBonus=0;}
    if (m3CollectingBlueprint) {
        m3DroppedBlueprint=0;m3CollectingBlueprint=0;m3KasplatTrace[4]++;
    }
}

int m3BlueprintAllowed(s16 object_id,u8 player,u16 type) {
    if (type!=7) return -1;
    m3KasplatTrace[2]++;
    m3KasplatTrace[5]=object_id;m3KasplatTrace[6]=physical_id;
    if (!krushaEnabled() || Character!=5 || player || !DetectAdventure() ||
        CurrentMap!=7 || object_id!=physical_id || krushaProgressRead(file(),KRUSHA_BLUEPRINT_BIT,1)) return 0;
    krushaProgressWrite(file(),KRUSHA_BLUEPRINT_BIT,1,1);
    m3KasplatTrace[3]++;
    playSong(69,1.0f);
    void (*change)(int,u8,s16)=(void*)0x806F91B4;
    change(12,0,1);
    return 1;
}
