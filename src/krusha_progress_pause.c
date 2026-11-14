#include "../include/common.h"
#include "../include/krusha_progress.h"
#include "../include/krusha_recruitment.h"
#include "../include/krusha_identity.h"

extern void vanillaPauseBuild(void*, u8);
extern void vanillaPauseSprite(void*, u8*);
extern const void* krushaProgressFace(void);

/* Native pause arrays are all five-wide. These own the expanded UI; neither
 * original flag strides nor adjacent native menu state are enlarged. */
s32 krushaPauseCount = 5;
static u8* pause_data = 0;
/* Read-only QA observations of actual rendered fractions: personal(value,max,
 * character), team(value,max), overall(kind,value,max), and total draw calls. */
volatile s32 krushaPauseFractionTrace[9] = {0};

s16 krushaPauseFractionTotal(s16 value, s16 total) {
    if (!DetectAdventure()) return total;
    if (total == 5) {
        if (pause_data && pause_data[0x12] == 1 &&
            pause_data[0x14] == 5 && krushaEnabled()) total = 3;
        krushaPauseFractionTrace[0] = value;
        krushaPauseFractionTrace[1] = total;
        krushaPauseFractionTrace[2] = pause_data ? pause_data[0x14] : -1;
    } else if (total == 30) {
        /* Five native allotments plus three personal rewards, even OFF. */
        total = 28;
        krushaPauseFractionTrace[3] = value;
        krushaPauseFractionTrace[4] = total;
    } else {
        /* Native807FC80C selects one of eight overall carousel slots.
         * 807FC818 maps their visual order to the permanent category. */
        u8 slot = *(u8*)0x807FC80C;
        s8 kind = slot < 8 ? *(s8*)(0x807FC818 + slot) : -1;
        /* Native pause caps GBs at200; the file score counts Rareware too. */
        if (kind == 0 && total == 200) total = 225;
        if (kind == 7 && total == 40) total = 48;
        krushaPauseFractionTrace[5] = kind;
        krushaPauseFractionTrace[6] = value;
        krushaPauseFractionTrace[7] = total;
    }
    krushaPauseFractionTrace[8]++;
    return total;
}
s16 krushaPauseAngles[6] = {0};
u8 krushaPauseUnlocked[6] = {0};
const void* krushaPauseFaces[6] = {0};
f32 krushaPauseX[12] = {0};
f32 krushaPauseY[12] = {0};
f32 krushaPauseScale[12] = {0};

static unsigned int file(void) { return *(volatile u8*)0x807467C8; }

static int privateFlag(int base, int level) {
    if (level < 0 || level > 7) return -1;
    if (base == 0x1D5) return KRUSHA_BLUEPRINT_BIT + level;
    if (base == 0x1FD) return KRUSHA_GB_BIT + level * 5 + 4;
    return -1;
}

/* Only pause builder callsites use this private sentinel. General permanent
 * flag readers keep their original five-character indexing and validation. */
int krushaPauseFlagIndex(int base, int level, int character) {
    int (*native)(int,int,int) = (void*)0x807319D8;
    int bit;
    if (character != 5) return native(base, level, character);
    bit = privateFlag(base, level);
    return bit < 0 ? 0x4200 : 0x4000 + bit;
}
int krushaPauseCheckFlag(int flag, int type) {
    if (flag >= 0x4000 && flag <= 0x4200) {
        if (flag == 0x4200) return 0;
        return krushaProgressRead(file(), flag - 0x4000, 1);
    }
    if (pause_data && DetectAdventure() && Character == 5 && (flag == 0x18B || flag == 0x18C)) return 1;
    return checkFlag(flag, type);
}
int krushaPauseFlagRange(int base, int first, int last, int character) {
    int (*native)(int,int,int,int) = (void*)0x80731A04;
    int bit, count = 0;
    if (character != 5) return native(base, first, last, character);
    for (int level = first; level <= last && level < 8; level++) {
        bit = privateFlag(base, level);
        if (bit >= 0) count += krushaProgressRead(file(), bit, 1);
    }
    return count;
}

static void refresh(void) {
    int count = krushaEnabled() && DetectAdventure() ? 6 : 5;
    for (int i = 0; i < 5; i++) {
        krushaPauseFaces[i] = ((const void**)0x80750518)[i];
        krushaPauseUnlocked[i] = ((u8*)0x80750530)[i];
    }
    krushaPauseFaces[5] = krushaProgressFace();
    krushaPauseUnlocked[5] = krushaAvailable(file());
    for (int i = 0; i < 6; i++)
        krushaPauseAngles[i] = count == 6 ? 682 * i : (i < 5 ? ((s16*)0x807505A4)[i] : 0);
}

void krushaPauseBuild(void* data, u8 update) {
    refresh();
    pause_data = data;
    /* A remembered sixth selection from another file/earlier page must not
     * expose locked personal stats. Native input already skips locked slots. */
    if (pause_data[0x14] == 5 && !krushaPauseUnlocked[5]) {
        pause_data[0x14] = 0;
        *(s16*)(pause_data + 0x10) = 0;
    }
    vanillaPauseBuild(data, update);
}

void krushaPauseSprite(void* node, u8* deleted) {
    u8* n = node;
    f32* meta = *(f32**)(n + 0x384);
    if (meta && meta[0] == 10.0f) {
        int index = meta[2];
        int character = index % krushaPauseCount;
        if (index >= 0 && index < krushaPauseCount * 2) {
            *(f32*)(n + 0x340) = krushaPauseX[index];
            *(f32*)(n + 0x344) = krushaPauseY[index];
            f32 scale = krushaPauseScale[index] * (krushaPauseCount == 6 ? 0.95f : 1.0f);
            *(f32*)(n + 0x360) = scale;
            *(f32*)(n + 0x364) = scale;
            krushaPauseX[index] = krushaPauseY[index] = -200.0f;
            if (krushaPauseUnlocked[character]) {
                n[0x36A] = n[0x36B] = n[0x36C] = 255;
            } else if (character == 5) {
                n[0x36A] = n[0x36B] = n[0x36C] = KRUSHA_IDENTITY_GRAY;
            } else {
                const u8* color = (const u8*)(0x8075054C + character * 4);
                for (int i = 0; i < 3; i++) n[0x36A+i] = color[i];
            }
        }
        /* An unused mode goes directly to native common fade/deletion logic.
         * It preserves transition ownership, without reading its ten arrays. */
        meta[0] = 16.0f;
        vanillaPauseSprite(node, deleted);
        meta[0] = 10.0f;
    } else vanillaPauseSprite(node, deleted);
}

static void immediate(u32 address, u16 value) {
    u32* code = (u32*)address;
    *code = (*code & 0xFFFF0000) | value;
    osWritebackDCache(code, 4);
    osInvalICache(code, 4);
}

void krushaPauseOption(void) {
    static int previous = -1;
    int count = krushaEnabled() && DetectAdventure() ? 6 : 5;
    if (previous == count) return;
    krushaPauseCount = count;
    refresh();
    /* Verified individual native bounds/spacing, never a blanket 5->6. */
    immediate(0x806A8AF0, count);       /* right input wrap */
    immediate(0x806A8B24, count - 1);   /* left input wrap */
    immediate(0x806A8AEC, -(4096 / count));
    immediate(0x806A8B44, 4096 / count);
    immediate(0x806AAA64, count);       /* second carousel page */
    immediate(0x806AAA94, count);       /* portrait creation */
    immediate(0x806A9AB8, count == 6 ? 0x435C : 0x4334); /* 220/180 ring radius */
    immediate(0x806A9C20, count);       /* portrait transform loop */
    immediate(0x806A9C44, 4096 / count);
    immediate(0x806AAF44, count);       /* medal ring */
    previous = count;
}

Gfx* krushaPauseNameText(Gfx* dl, s16 x, s16 y, f32 scale, char* text) {
    Gfx* (*native)(Gfx*,s16,s16,f32,char*) = (void*)0x806ABB98;
    if (pause_data && pause_data[0x12] == 1 && pause_data[0x14] == 5)
        text = krushaAvailable(file()) ? "KRUSHA" : "???";
    return native(dl,x,y,scale,text);
}

/* Exact native single-tile animated descriptors; only the owned icon colors
 * differ. The approved face itself remains fully colored. */
typedef struct OwnedSprite {
    u32 id;
    u8 across, down, flags, codec;
    u32 rgba;
    u8 animated, table;
    u16 width, height, frames;
    u16 images[8];
} OwnedSprite;
static const OwnedSprite owned_icons[3] = {
    {0x4B520100,1,1,0,2,0xFFFFFFFF,1,1,44,44,8,{7100,7101,7102,7103,7104,7105,7106,7107}},
    {0x4B520101,1,1,0,2,0xFFFFFFFF,1,1,48,42,8,{7108,7109,7110,7111,7112,7113,7114,7115}},
    {0x4B520102,1,1,0,2,0xFFFFFFFF,1,1,48,42,8,{7116,7117,7118,7119,7120,7121,7122,7123}},
};
const void* krushaOwnedIcon(int index) {
    return index>=0 && index<3 ? &owned_icons[index] : 0;
}
const void* krushaPauseIcon(const void* sprite) {
    if (!krushaEnabled() || !DetectAdventure() || Character != 5) return sprite;
    if ((u32)sprite == 0) return &owned_icons[0];
    if ((u32)sprite == 1) return &owned_icons[1];
    if ((u32)sprite == 12) return &owned_icons[2];
    return sprite;
}

/* Krusha now has50 CB/world and no medals. Keep all medal displays five-wide. */
int krushaPauseMedalLayout(void* menu, const void* sprite, s32* x, s32 mode) {
    u8* data = menu;
    int bank = data[0x15];
    int area;
    if (!krushaEnabled() || !DetectAdventure() || bank > 1) return 0;
    area = ((s16*)(data+8))[bank];
    if (area < 0 || area > 8) return 0;
    if (data[0x12] == 1 && data[0x14] == 5 && (u32)sprite == 10) return 1;
    if (data[0x12] == 2 && (mode == 3 || mode == 14)) {
        for (int i = 0; i < 6; i++) if (*x == krushaPauseAngles[i]) {
            if (i == 5) return 1;
            *x = ((s16*)0x807505A4)[i];
            break;
        }
    }
    return 0;
}
