#include "../include/common.h"
#include "../include/krusha_progress.h"
#include "../include/m3_progress.h"
#include "../include/m3_kasplat.h"

extern int saveNativePackedRead(int,u8,u8,u8);
extern void m3NativeShopPurchase(void*,void*);
extern void m3NativeShopControl(void*,void*,int);
extern void* m3NativePurchaseText(int,int,int);
extern void m3NativeShopAnimation(void*,int);
extern void krushaPlayActorAnimation(void*,int);
extern void krushaPlayRawAnimation(void*,int,f32,f32);
extern void krushaAnimationSpeed(void*,f32,f32);
extern void krushaActorAnimationSpeed(void*,f32,f32);
extern void krushaPlayScream(void);
extern void krushaHolsterModel(void*);

static int lesson_scene;
static int lesson_greeted;
static int offer_type = -1;
static int offer_value;
/* Native two-tile head descriptor, reusing the approved barrel/file portrait.
 * Native shop prices 20..24 show the wallet owner's head; 25 is Krusha. */
typedef struct {
    u32 id;u8 across,down,flags,codec;u32 rgba;
    u8 animated,table;u16 width,height,frames;u16 images[2];
} HeadIcon;
static const HeadIcon face_icon={0x4B520130,2,1,0,2,0xFFFFFFFF,0,1,32,64,1,{7001,7002}};
/* Separate identity/cache key: the energy counter must not replace the
 * approved ordinary portrait used by shop prices, barrels or menus. */
static const HeadIcon shout_icon={0x4B520131,2,1,0,2,0xFFFFFFFF,0,1,32,64,1,{7600,7601}};
const void* m3FaceIcon(void) { return &face_icon; }
const void* m3ShoutIcon(void) { return &shout_icon; }
static unsigned int file(void) { return *(volatile u8*)0x807467C8; }
static int active(void) { return krushaEnabled() && DetectAdventure() && Character == 5; }

/* Ownership is separate from team-wide upgrade bits. An original Kong buying
 * homing/sniper or an energy upgrade benefits Krusha, but never grants his
 * initial weapon or Candy lesson. No new EEPROM fields are needed. */
int m3SavedMoves(unsigned int slot, int type) {
    if (StorySkip) return type==6 ? 7 : 15;
    int bits=0;
    for (int k=0;k<5;k++) bits |= saveNativePackedRead(type,k,0,slot);
    return (bits & (type==6 ? 6 : 14)) |
        (krushaProgressRead(slot,type==6 ? KRUSHA_GUN_BIT : KRUSHA_SHOUT_BIT,1) ? 1 : 0);
}

static int capacity(void) {
    int bits=MovesBase[5].instrument_bitfield;
    int n=1;
    if (!(bits&1)) return 0;
    while (bits) { n++; bits >>= 1; }
    return n*5;
}

/* Safe before player spawn: only the existing private ownership bits, no
 * actor/map scans or new grant policy. The recruitment save can include them. */
void m3SpeedOwnership(void) {
    if (!DetectAdventure() || Gamemode!=6 || CurrentMap==80 || !StorySkip || file()>=3) return;
    if (!krushaProgressRead(file(),KRUSHA_GUN_BIT,1))
        krushaProgressWrite(file(),KRUSHA_GUN_BIT,1,1);
    if (!krushaProgressRead(file(),KRUSHA_SHOUT_BIT,1))
        krushaProgressWrite(file(),KRUSHA_SHOUT_BIT,1,1);
}

void m3ProgressTick(void) {
    m3KasplatTick();
    if (CurrentMap!=25) lesson_scene=lesson_greeted=0;
    if (!DetectAdventure()) return;
    int guns=0, instruments=0;
    for (int k=0;k<5;k++) {
        guns |= MovesBase[k].weapon_bitfield;
        instruments |= MovesBase[k].instrument_bitfield;
    }
    if (StorySkip) {
        guns|=6;instruments|=14;
        m3SpeedOwnership();
    }
    MovesBase[5].weapon_bitfield=(guns&6) | krushaProgressRead(file(),KRUSHA_GUN_BIT,1);
    MovesBase[5].instrument_bitfield=(instruments&14) | krushaProgressRead(file(),KRUSHA_SHOUT_BIT,1);
    /* Speed Mode supplies ownership/upgrades, not infinite energy. The
     * original five are filled in the main menu, not on adventure ticks. */
    MovesBase[5].ammo_belt=StorySkip ? 2 : MovesBase[0].ammo_belt;
    MovesBase[5].simian_slam=StorySkip ? 3 : MovesBase[0].simian_slam;
    if (MovesBase[5].instrument_energy>capacity()) MovesBase[5].instrument_energy=capacity();
}

void m3RestoreMoves(unsigned int slot, int refill) {
    /* File-summary previews call the native loader too. Restore runtime
     * moves here, but only the adventure tick may grant saved Speed Mode
     * ownership; merely previewing another file must not alter its flags. */
    MovesBase[5].weapon_bitfield=m3SavedMoves(slot,6);
    MovesBase[5].instrument_bitfield=m3SavedMoves(slot,8);
    if (StorySkip) { MovesBase[5].ammo_belt=2;MovesBase[5].simian_slam=3; }
    /* Vanilla refills owned instruments on a refill-load. Do not persist a
     * phantom instrument model or invent an incompatible energy-save field. */
    if (refill) MovesBase[5].instrument_energy=StorySkip ? 20 : capacity()/2;
    if (refill && (MovesBase[5].weapon_bitfield&1) && !MovesBase[0].weapon_bitfield)
        CollectableBase.StandardAmmo=((1<<MovesBase[5].ammo_belt)*50)/2;
}

typedef struct { s16 type,value,price; } Offer;
static const Offer funky[7]={{2,1,3},{-1,0,0},{3,1,3},{-1,0,0},{2,2,5},{3,2,5},{2,3,7}};
static const Offer candy[7]={{-1,0,0},{4,1,0},{-1,0,0},{4,2,5},{-1,0,0},{4,3,7},{4,4,9}};

void m3FindPurchase(void* menu, void* progress, int first) {
    u8* data=menu;
    int latest=6;
    int (*level)(int,int)=(void*)0x805FF030;
    while (latest>=0 && !checkFlag(0x1C5+latest,0)) latest--;
    data[0xC]=level(CurrentMap,0);
    data[0xB]=0xFF;
    data[0x10]=CollectableBase.Melons;
    *(s16*)(data+4)=0;
    *(s16*)0x80750AC8=0;
    offer_type=-1;
    const Offer* stock=CurrentMap==1 ? funky : CurrentMap==25 ? candy : 0;
    if (!stock) return; /* Preserve Cranky's native Jetpac eligibility path. */
    /* Candy's first visit is a free lesson regardless of latest world. */
    if (CurrentMap==25 && !(MovesBase[5].instrument_bitfield&1)) {
        data[0xB]=4;data[0x11]=1;lesson_scene=1;
        offer_type=4;offer_value=1;
        return;
    }
    for (int i=0;i<=latest;i++) {
        const Offer* o=&stock[i];
        if (o->type<0) continue;
        int have=((u8*)&MovesBase[5])[o->type];
        if (o->type==2 || o->type==4) {
            if (have & (1<<(o->value-1))) continue;
        } else if (have>=o->value) continue;
        data[0xB]=o->type;data[0x11]=o->value;
        *(s16*)(data+4)=o->price;*(s16*)0x80750AC8=o->price;
        offer_type=o->type;offer_value=o->value;
        return;
    }
}

void m3ShopPurchase(void* menu, void* progress) {
    u8* data=menu;
    if (active()) {
        int price=*(s16*)(data+4);
        if ((s8)data[0xB]<0 || price<0 || price>MovesBase[5].coins) return;
        if ((data[0xB]==2 || data[0xB]==4) && data[0x11]==1) {
            int bit=data[0xB]==2 ? KRUSHA_GUN_BIT : KRUSHA_SHOUT_BIT;
            if (krushaProgressRead(file(),bit,1)) return;
            krushaProgressWrite(file(),bit,1,1);
        }
    }
    /* Native grant/refill/payment/save remains authoritative. Its base move
     * writes the selected sixth record; global upgrades still update five,
     * and our frame adapter mirrors only their shared upgrade bits. */
    m3NativeShopPurchase(menu,progress);
    if (active()) {
        /* Native shared-upgrade grants loop over five records. Mirror them
         * before the final refill, so a sixth Candy/belt purchase fills the
         * new capacity rather than the old capacity. Never charge twice. */
        m3ProgressTick();
        if (data[0xB]==2 || data[0xB]==3 || data[0xB]==4) {
            void (*change)(int,u8,s16)=(void*)0x806F91B4;
            change(data[0xB]==4 ? 7 : 2,0,9999);
        }
    }
}

void m3ShopControl(void* menu, void* progress, int flag) {
    u8* data=menu;
    if (active() && CurrentMap==25 && lesson_scene &&
        !(MovesBase[5].instrument_bitfield&1) && data[0xD]==1 &&
        (data[0xE]==1 || data[0xE]==5)) data[0xE]=10;
    m3NativeShopControl(menu,progress,flag);
}

static void celebration(void* actor) {
    krushaHolsterModel(actor);
    krushaPlayActorAnimation(actor,0);
    krushaPlayRawAnimation(actor,0x2AA,22.0f,0.0f);
    krushaAnimationSpeed(actor,1.2f,0.0f);
    krushaActorAnimationSpeed(actor,0.5f,0.0f);
}

void m3ShopAnimation(void* actor,int animation) {
    if (active() && CurrentMap==1 && actor==(void*)Player) celebration(actor);
    else m3NativeShopAnimation(actor,animation);
}

void m3ShopInstrument(void) {
    /* Native Candy purchase camera/timing owns the scene. No adventure roar,
     * enemy effect, stock charge or nonexistent instrument prop is started. */
    if (!Player) return;
    celebration(Player);
    if (lesson_scene) krushaPlayScream();
}

void* m3PurchaseText(int bank,int index,int arg) {
    if (active() && offer_value==1) {
        if (CurrentMap==1 && offer_type==2) return "BAZOOKA";
        if (CurrentMap==25 && offer_type==4) return "THUNDER ROAR";
    }
    return m3NativePurchaseText(bank,index,arg);
}

static int starts(const u8* text,u16 length,const char* prefix) {
    for (int i=0;prefix[i];i++) if (i>=length || text[i]!=prefix[i]) return 0;
    return 1;
}

const char* m3ShopDialogue(const u8* text,u16 length) {
    if (!active()) return 0;
    /* Only native no-potion lines. Leave all eligible Jetpac offers, scores,
     * retry/return text and the original 15-medal gate untouched. */
    if (CurrentMap==5 && (starts(text,length,"BAH! COME ON, ") ||
        starts(text,length,"I CAN'T BE BOTHERED TO MAKE ANY MORE POTIONS") ||
        starts(text,length,"THAT'S ALL THE POTIONS YOU'RE GETTING")))
        return "MY POTIONS ARE FOR KONGS, NOT WALKING ARMORIES! BRING ME 15 BANANA MEDALS AND WE CAN TALK ABOUT MY COMPUTER GAME.";
    return 0;
}

void m3QueueShopDialogue(void* actor,u16 bank,u8 index) {
    void (*loadText)(void*,u16,u8)=(void*)0x8070D8C0;
    if (bank==9 && CurrentMap==25 && active() && lesson_scene &&
        actor && *(u32*)((u8*)actor+0x58)==191) {
        if (index==18) {
            /* The native tutorial is queued after the demonstration. */
            loadText(actor,bank,23);
            return;
        }
        if (!(MovesBase[5].instrument_bitfield&1) && (index==0 || index==3 || index==4)) {
            /* A first shop visit queues both a greeting and an offer.
             * Collapse them to one lesson opener, including on later visits. */
            if (!lesson_greeted) {
                lesson_greeted=1;
                loadText(actor,bank,22);
            }
            return;
        }
    }
    loadText(actor,bank,index);
}
