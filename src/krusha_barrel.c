#include "../include/common.h"
#include "../include/krusha_recruitment.h"
#include "../include/krusha_progress.h"
#include "../include/klump_colors.generated.h"
#include "../include/m5_campaign.h"
#include "../include/recruitment_assets.generated.h"
#include "../include/recruitment_room.generated.h"
#include "../include/recruitment_barrel.generated.h"

/* Keep the native 0x40-byte barrel data layout. Its five actor pointers are
 * followed immediately by the spotlight pointer; the sixth actor lives here,
 * rather than overwriting that pointer or any of the cutscene data. Only one
 * adventure barrel selector can be open at a time. */
typedef struct {
    void* player;
    u16 timer;
    s8 selected;
    s8 previous;
    void* actors[5];
    void* spotlight;
    s8 direction;
} BarrelData;

typedef struct { s16 model, actor; u8 mesh, pad; } BarrelCharacter;
static const BarrelCharacter characters[6] = {
    {4, 2, 2, 0}, {1, 3, 1, 0}, {6, 4, 3, 0},
    {9, 5, 4, 0}, {12, 6, 0, 0}, {0xDB, 7, 0, 0},
};
/* Preserve the five native instrument masks. Krusha has no sixth stem. */
static const u32 music_masks[6] = {2, 0x48, 4, 0x20, 0x10, 0};
static BarrelData* owner;
static void* sixth;
static s32 selecting_sixth;
static s32 owner_map = -1;
static u8 owner_file = 255;

static int owns(BarrelData* data) {
    return data == owner && CurrentMap == owner_map &&
        krushaProgressActiveFile() == owner_file;
}

/* Deny before native deletion/mesh replacement, including a stale/unavailable
 * unlocked display. The native locked actor also has its own denial path. */
s32 krushaBarrelSelectionBusy(void) {
    s32 busy=((s32 (*)(void))0x8062919C)();
    if (busy) return busy;
    if (selecting_sixth && krushaEnabled() && DetectAdventure() &&
        !krushaRecruitmentPlayable()) {
        if (*(u16*)0x807FD63C&0xE000) playSound(152,0x2FFF,63.0f,1.0f,0,0);
        return 1;
    }
    return 0;
}

extern void vanillaBarrelSpawn(BarrelData*);
extern void vanillaBarrelLayout(BarrelData*);
extern void vanillaBarrelControl(BarrelData*);
extern char* vanillaBarrelName(BarrelData*, s32);
extern void vanillaBarrelAnimation(void*, void*, s32);
extern void krushaPlayActorAnimation(void*, s32);
extern s32 krushaNativeBarrelFlag(s32, s32);
extern void krushaInitCharacterMesh(void*, u16);
extern void krushaNativeActorDelete(void*);
extern f32 krushaSin(s16);
extern f32 krushaCos(s16);
extern void* vanillaBarrelFile(s32 table, s32 index, u8 synchronous, u8 unique);

/* Table 27 is a dedicated uncompressed asset table. Native file allocation,
 * DMA, ownership and cleanup still handle every file. The original table-5
 * barrel and all five original faces remain byte-for-byte available when OFF.
 * Reserved texture IDs belong to the six-face barrel and gray shockwave. */
void* krushaBarrelFile(s32 table, s32 index, u8 synchronous, u8 unique) {
    s32 format = table;
    extern s32 mirrorEnabled(void);
    if (table == 5 && index == RECRUITMENT_BARREL_MODEL_TOKEN - 1) {
        table = 27;
        index = mirrorEnabled() ? RECRUITMENT_BARREL_MIRROR : RECRUITMENT_BARREL_MODEL;
    }
    if (table == 25 && index == RECRUITMENT_BARREL_TEXTURE_TOKEN) {
        table = 27;
        index = RECRUITMENT_BARREL_TEXTURE;
    }
    if (index==RECRUITMENT_ROOM_MAP) {
        if (table==1) {table=27;index=mirrorEnabled()?RECRUITMENT_ROOM_MIRROR:RECRUITMENT_ROOM_GEOMETRY;}
        else if (table==18) {table=27;index=RECRUITMENT_ROOM_ZONE;}
    }
    if (table==4 && index==RECRUITMENT_MODEL_TYPE) { table=27;index=mirrorEnabled()?RECRUITMENT_MIRROR_INDEX:RECRUITMENT_MODEL_INDEX; }
    if (table==25 && index>=RECRUITMENT_TEXTURE_TOKEN && index<RECRUITMENT_TEXTURE_TOKEN+RECRUITMENT_TEXTURE_COUNT) { table=27;index+=RECRUITMENT_TEXTURE_BASE-RECRUITMENT_TEXTURE_TOKEN; }
#if M4_GRENADE_PREVIEW
    if ((table==25 || table==7) && index>=7732 && index<7748) {table=27;index-=7601;}
#endif
    if (table==25 && index>=RECRUITMENT_ROOM_TEXTURE_TOKEN && index<RECRUITMENT_ROOM_TEXTURE_TOKEN+RECRUITMENT_ROOM_TEXTURE_COUNT) {table=27;index-=RECRUITMENT_ROOM_TEXTURE_TOKEN;index=(index<3 ? RECRUITMENT_ROOM_TEXTURE_INDEX+index : RECRUITMENT_ROOM_EXTRA_TEXTURE_INDEX+index-3);}
    s32 campaign=m5FileAlias(table,index);
    if (campaign>=0) {table=27;index=campaign;}
    if (table==5 && index==0xED) { table=27;index=69; }
    if (table==4 && index==42) { table=27;index=70; }
    if (table==25 && index>=7420 && index<7436) { table=27;index-=7349; }
    if (table==4 && index==9) { table=27;index=65; }
    /* Keep the private scripts present for native map-cache restoration even
     * with Krusha OFF. Their private predicate hides the two inert props. */
    if (table==10 && index==7) { table=27;index=67; }
    if (table==4 && index==33) { table=27;index=66; }
    if (table==25 && index==7410) { table=27;index=68; }
    if (table == 5 && index == 0xC0 && krushaEnabled()) {
        table = 27;
        index = 0;
    } else if (table == 25 && (index == 7001 || index == 7002)) {
        table = 27;
        index -= 7000;
    } else if (table == 5 && index == 0xEC) {
        table = 27;
        index = 3;
    } else if (table == 25 && index >= 7003 && index <= 7008) {
        table = 27;
        index -= 6999;
    }
    if (table == 14 && index == 7200) {
        table = 27;
        index = 34;
    }
    if (table == 25 && index >= 7100 && index <= 7123) {
        table = 27;
        index -= 7090;
    }
    if ((table==25 || table==7) && index>=7700 && index<7716) { table=27;index-=7611; }
    if (table==4 && index==49) { table=27;index=105; }
    if ((table==25 || table==7) && index>=7716 && index<7732) { table=27;index-=7610; }
    if (table==4 && index==56) { table=27;index=122; }
    if (table==4 && index==46) { table=27; index=88; }
    if (table == 4 && (index == 2 || index == 4 || index == 6)) {
        table = 27; index = 35 + index/2 - 1;
    } else if (table == 7 && index >= 7100 && index <= 7115) {
        table = 27; index -= 7090;
    } else if (table == 7 && index >= 7201 && index <= 7212) {
        table = 27; index -= 7163;
    }
    if (table == 25 && index >= 7300 && index <= 7307) {
        table = 27; index -= 7250;
    }
    if (krushaEnabled() && DetectAdventure()) {
        if (table==5 && index==54) { table=27; index=58; }
        if (table==16 && index==7) { table=27; index=87; }
    }
    if (table==25 && (index==7400 || index==7401)) { table=27; index-=7341; }
    if (table==4 && index==7) { table=27; index=62; }
    if (table==7 && index>=7500 && index<=7507) { table=27; index-=7474; }
    if (table==25 && (index==7600 || index==7601)) { table=27; index-=7537; }
    extern s32 mirrorFileIndex(s32, s32, s32);
    extern void* mirrorFile(s32, s32, u8, u8);
    s32 mirrored = mirrorFileIndex(format, table, index);
    if (mirrored >= 0) return mirrorFile(format, mirrored, synchronous, unique);
    if (table == 27) {
        /* Native tables4/7/14/25 cache shared files; the originally empty
         * table27 has no cache. World pickups can request each model/frame
         * many times, so preserve the same reference-counted sharing here.
         * Native loading, allocation, reference tracking and release still
         * own every payload. This is a pointer array, not a payload lifetime
         * extension or a separate untracked cache. */
        void (*initTable)(s32)=(void*)0x8066B5F4;
        initTable(27);
        u32** caches=(u32**)0x807F95A8;
        if (!caches[27]) {
            u32* offsets=((u32**)0x807F9528)[27];
            u32 table_offset=(*(u32**)0x807F9520)[27];
            u32 bytes=(offsets[0]&0x7FFFFFFF)-table_offset;
            u32* cache=(bytes >= 4 && bytes <= 4096 && !(bytes&3)) ? dk_malloc(bytes) : 0;
            if (cache) {
                for (u32 i=0;i<bytes/4;i++) cache[i]=0;
                caches[27]=cache;
            }
        }
    }
    if (table == 27 && (format==1 || format==18 || index == 0 || index == 3 || index==58 || index==61 || index==69 || index==87 || index==RECRUITMENT_BARREL_MODEL || index==RECRUITMENT_BARREL_MIRROR || (index>=123 && index<131))) {
        /* These two actor models replace table5 files, which are deliberately
         * uncached in vanilla. Keep each actor's native model ownership while
         * sharing only the table4 models and table7/14/25 texture resources. */
        u32** caches=(u32**)0x807F95A8;
        u32* saved=caches[27];
        caches[27]=0;
        void* result=vanillaBarrelFile(table,index,synchronous,unique);
        caches[27]=saved;
        return result;
    }
    return vanillaBarrelFile(table, index, synchronous, unique);
}

static void patch(u32 address, u32 word) {
    *(volatile u32*)address = word;
    osWritebackDCache((void*)address, 4);
    osInvalICache((void*)address, 4);
}

static void jump(u32 address, void* target) {
    patch(address, 0x08000000 | (((u32)target & 0x0FFFFFFF) >> 2));
    patch(address + 4, 0);
}

static void pointer(u32 hi, u32 lo, const void* target) {
    u32 address = (u32)target;
    patch(hi, (*(u32*)hi & 0xFFFF0000) | ((address + 0x8000) >> 16));
    patch(lo, (*(u32*)lo & 0xFFFF0000) | (address & 0xFFFF));
}

static void* actor(BarrelData* data, s32 index) {
    if (index == 5) return owns(data) ? sixth : 0;
    if (index < 0 || index >= 5) return 0;
    return data->actors[index];
}

s32 krushaBarrelFlag(s32 type, s32 index) {
    /* Native entry records a tag flag. There is no sixth flag to write. */
    return index == 5 ? -1 : krushaNativeBarrelFlag(type, index);
}

void krushaBarrelAnimation(void* model, void* data, s32 action) {
    if (krushaEnabled() && DetectAdventure() &&
        *(u32*)((u8*)model + 0x58) == 316 && *(u16*)data == 7) {
        if (action == 0x8B) {
            // Native multiplayer victory: Krusha's own clip 693. The original
            // barrel entry 1DD uses Chunky's clip 2EB and Chunky's voice cues.
            krushaPlayActorAnimation(model, 0x43A);
            return;
        }
        if (action == 0x8A || action == 0x8C) {
            // His own waiting pose also replaces Chunky's deselection clip.
            krushaPlayActorAnimation(model, 0x1DC);
            return;
        }
    }
    vanillaBarrelAnimation(model, data, action);
}

void krushaBarrelLayout(BarrelData* data) {
    if (!krushaEnabled() || !DetectAdventure() || !owns(data) || !sixth) {
        vanillaBarrelLayout(data);
        return;
    }
    u8* barrel = *(u8**)0x807FBB40;
    f32 amount = data->timer / 20.0f;
    f32 step = 4096.0f / 6.0f;
    f32 base = *(s16*)(barrel + 0xE6) + data->selected * step - amount * step * data->direction;
    for (s32 i = 0; i < 6; i++) {
        u8* model = actor(data, i);
        if (!model) continue;
        s16 angle = ((s32)(base - i * step)) & 0xFFF;
        *(f32*)(model + 0x7C) = *(f32*)(barrel + 0x7C) + krushaSin(angle) * 45.0f;
        *(f32*)(model + 0x80) = *(f32*)(barrel + 0x80) - 10.0f;
        *(f32*)(model + 0x84) = *(f32*)(barrel + 0x84) + krushaCos(angle) * 45.0f;
        f32 focus = i == data->selected ? 1.0f - amount : i == data->previous ? amount : 0.0f;
        focus = (focus - 0.6f) * 2.5f;
        if (focus < 0) focus = 0;
        if (focus > 1) focus = 1;
        model[0x15F] = 3 + 12.0f * focus;
    }
}

void krushaBarrelSpawn(BarrelData* data) {
    owner = data;
    sixth = 0;
    owner_map = CurrentMap;
    owner_file = krushaProgressActiveFile();
    vanillaBarrelSpawn(data);
    if (!krushaEnabled() || !DetectAdventure()) return;
    int available = krushaRecruitmentPlayable();
    if (!spawnActor(available ? 316 : 317,
                    available ? 0xDB : RECRUITMENT_BARREL_MODEL_TOKEN)) return;
    u8* model = *(u8**)0x807FBB44;
    sixth = model;
    *(s16*)(model + 0xE6) = *(s16*)(*(u8**)0x807FBB40 + 0xE6);
    *(u32*)(model + 0x60) |= 0x40000000;
    void* data_model = *(void**)(model + 0x174);
    if (available) {
        *(u16*)data_model = 7;
        krushaInitCharacterMesh(model, 7);
        krushaBarrelAnimation(model, data_model, data->selected == 5 ? 0x8B : 0x8A);
    } else {
        /* The native locked callback has a FIVE-entry palette table. Slot
         * identity lives in our sixth pointer, not that palette byte. */
        *(u8*)data_model = 0;
    }
    krushaBarrelLayout(data);
}

void krushaBarrelControl(BarrelData* data) {
    if (!krushaEnabled() || !DetectAdventure()) {
        vanillaBarrelControl(data);
        return;
    }
    if (!owns(data) || !sixth) {
        /* Allocation failure must not expose actors[5] (the spotlight) as
         * a selectable Kong. Temporarily restore the two native five bounds. */
        patch(0x806837D4, 0x240C0004);
        patch(0x806837EC, 0x28410005);
        if (data->selected < 0 || data->selected >= 5) {
            data->selected = data->previous = 0;
            data->timer = 0;
        }
        vanillaBarrelControl(data);
        patch(0x806837D4, 0x240C0005);
        patch(0x806837EC, 0x28410006);
        return;
    }
    /* Native control indexes actors[selected]. During this synchronous call,
     * slot five aliases the saved spotlight field. Layout and name rendering
     * use actor() instead. Restore the real spotlight before actor rendering.
     * On exit native cleanup deletes the aliased sixth actor and the original
     * five; delete the real spotlight once here. No allocation layout changes. */
    void* spotlight = data->spotlight;
    u8* barrel = *(u8**)0x807FBB40;
    data->spotlight = sixth;
    selecting_sixth=data->selected==5;
    /* Vanilla automatically rotates past locked originals. The agreed sixth
     * question mark must remain highlightable: suppress only that idle skip,
     * keeping s0=locked so native confirmation still refuses it. Horizontal
     * rotation and the original five retain native rules. */
    int locked_sixth = selecting_sixth && *(u32*)((u8*)sixth + 0x58) == 317;
    if (locked_sixth) {
        /* Native control increments +3C before its 9001-tick timeout. Let
         * that timeout skip the lock and leave through an available original;
         * forcing idle retention afterward would trap all carousel input. */
        patch(0x80683768, *(u32*)((u8*)data + 0x3C) < 9000 ?
              0x10000032 : 0x16000032);
        /* Locked originals keep their previous travel direction while they
         * auto-skip. A retained sixth must read the current stick instead.
         * Let native control update direction at its normal timer/input gate;
         * changing it before that gate would distort an in-flight rotation. */
        /* With no horizontal input, automatic timeout travel retains the
         * native previous direction. Only a real new stick turn overrides it. */
        patch(0x806837A0, *(u8*)0x807FD640 >= 41 ? 0 : 0x1200000B);
    }
    vanillaBarrelControl(data);
    if (locked_sixth) {
        patch(0x80683768, 0x16000032);
        patch(0x806837A0, 0x1200000B);
    }
    selecting_sixth=0;
    if (barrel[0x154] == 1) {
        data->spotlight = spotlight;
    } else {
        krushaNativeActorDelete(spotlight);
        data->spotlight = 0;
        sixth = 0;
        owner = 0;
    }
}

char* krushaBarrelName(BarrelData* data, s32 index) {
    if (index == 5) {
        if (!owns(data) || !sixth) return 0;
        return *(u32*)((u8*)sixth + 0x58) == 316 ? "KRUSHA" : "???";
    }
    if (index < 0 || index >= 5) return 0;
    return vanillaBarrelName(data, index);
}

void krushaBarrelInstall(void) {
    jump(0x8066B0F8, krushaBarrelFile);
    jump(0x80682E38, krushaBarrelSpawn);
    jump(0x80682AB4, krushaBarrelLayout);
    jump(0x806836D0, krushaBarrelControl);
    jump(0x80683A80, krushaBarrelName);
    jump(0x80682DF4, krushaBarrelAnimation);
    pointer(0x80683584, 0x8068358C, characters);
    pointer(0x806839C4, 0x806839E4, (u8*)characters + 2);
    pointer(0x806835EC, 0x806835FC, music_masks);
    pointer(0x80683844, 0x80683848, music_masks);
    patch(0x80683620, 0x0C000000 | (((u32)krushaBarrelFlag & 0x0FFFFFFF) >> 2));
}

void krushaBarrelOption(void) {
    static s32 previous = -1;
    s32 count = krushaEnabled() && DetectAdventure() ? 6 : 5;
    if (CurrentMap != owner_map || krushaProgressActiveFile() != owner_file) {
        owner = 0;
        sixth = 0;
        selecting_sixth = 0;
    }
    if (count == previous) return;
    patch(0x806837D4, 0x240C0000 | (count - 1));
    patch(0x806837EC, 0x28410000 | count);
    previous = count;
}
