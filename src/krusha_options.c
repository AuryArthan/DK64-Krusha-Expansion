#include "../include/common.h"

extern void vanillaOptionsInput(void*, s32);
extern void krushaSetEnabled(s32);
extern s32 krushaMenuTransform(void*, f32, f32, f32*, f32*, s32, s8, f32);
extern Gfx* krushaPrintStyledText(Gfx*, s16, s16, s16, char*, u32);
extern void mirrorSetEnabled(s32);
extern s32 mirrorEnabled(void);

/* Global flags occupy the first 64 bits of the native global block. Vanilla
 * uses through 0x2B; 0x23 is the existing Speed option and 0x24 Krusha OFF.
 * Zero is intentionally the default for both new options. */
static s32 options_loaded;
static s32 tag_enabled;
static u32 options_shadow_flag;
s32 gameOptionsMode(void) { return StorySkip ? 2 : tag_enabled; }

void gameOptionsTick(void) {
    if (CurrentMap == 80 && !options_loaded) {
        StorySkip = checkFlag(0x23, 1);
        tag_enabled = checkFlag(0x2C, 1) != 0;
        mirrorSetEnabled(checkFlag(0x2D, 1));
        options_loaded = 1;
    }
}

static void setTagMode(s32 value) {
    tag_enabled = value != 0;
    StorySkip = value == 2;
    setFlag(0x23, StorySkip, 1);
    setFlag(0x2C, tag_enabled, 1);
    SaveToGlobal();
}

/* Retain the original item IDs, including the Z-only high-score reset.
 * Display and navigate them as rows; the rest of the menu stays native. */
static const u8 rows[6] = {4, 0, 1, 5, 3, 2};

void krushaOptionsInit(void* actor, s32 input) {
    void* data = *(void**)((u8*)actor + 0x174);
    extern void krushaMenuAddSprite(void*, const void*, s32, s32, f32, u8, s32);
    ((u8*)data)[0x17] = 4;
    /* The player behind this 2D page is hidden, but native lighting still
     * queues its ground decal. Mirror winding merely backface-culls that
     * stray shadow. Skip lighting for this hidden actor in either mode. */
    options_shadow_flag = 0;
    if (CurrentMap == 80 && Player) {
        u32* properties = (u32*)((u8*)Player + 0x60);
        options_shadow_flag = *properties & 0x2000;
        *properties |= 0x2000;
    }
    krushaMenuAddSprite(data, (void*)0x80720D14, 35, 210, .75f, 2, 0);
}

void krushaOptionsInput(void* actor, s32 input) {
    u8* data = *(u8**)((u8*)actor + 0x174);
    s32 old = *(u16*)0x80033670;
    *(s8*)0x800338FC = 6;
    if (CurrentMap == 80 && Player)
        *(u32*)((u8*)Player + 0x60) |= 0x2000;
    if (*(f32*)data == 0.0f && *(f32*)(data + 4) == 0.0f) {
        s32 selected = data[0x17], row = 0, changed = 0;
        while (row < 5 && rows[row] != selected) row++;
        if ((input & 0x30) && !(old & 0x30)) {
            row = (row + ((input & 0x10) ? 5 : 1)) % 6;
            data[0x17] = rows[row];
            playSound(0x2C9, 0x7FFF, 63.0f, 1.25f, 0, 0);
        } else if (((input & 0xC) && !(old & 0xC)) || (input & 1)) {
            s32 direction = (input & 4) ? -1 : 1;
            switch (selected) {
                case 0: *(u8*)0x807444C0 ^= 1; changed = 1; break;
                case 1: setTagMode((gameOptionsMode() + direction + 3) % 3); changed = 1; break;
                case 3: *(u8*)0x80744530 ^= 1; changed = 1; break;
                case 4: krushaSetEnabled(!krushaEnabled()); changed = 1; break;
                case 5:
                    mirrorSetEnabled(!mirrorEnabled());
                    setFlag(0x2D, mirrorEnabled(), 1); SaveToGlobal(); changed = 1; break;
            }
            if (changed) playSound(0x74, 0x7FFF, 63.0f, 1.0f, 0, 0);
        }
    }
    /* Keep B/back, native option serialization, Z/high-scores, transition
     * cleanup and C-up/down camera preference. Suppress old carousel/toggles. */
    vanillaOptionsInput(actor, input & ~(0x3D));
    /* The native transition changes page12 and initializes its successor
     * before returning. Restore only our bit after Options has left; never
     * retain an actor pointer across a menu or adventure load. */
    if (data[0x12] != 9 && CurrentMap == 80 && Player) {
        u32* properties = (u32*)((u8*)Player + 0x60);
        *properties = (*properties & ~0x2000) | options_shadow_flag;
    }
}

Gfx* krushaOptionsDraw(void* actor, Gfx* dl) {
    void* data = *(void**)((u8*)actor + 0x174);
    char** strings = *(char***)0x80033F28;
    char* labels[6] = {"WIDESCREEN", "TAG-ANYWHERE", strings[44], strings[45], "KRUSHA", "MIRROR MODE"};
    char* values[6] = {
        *(u8*)0x807444C0 ? "ON" : "OFF",
        gameOptionsMode() == 2 ? "SPEED MODE" : gameOptionsMode() ? "ON" : "OFF",
        "PRESS Z", strings[52 + *(u8*)0x80744530],
        krushaEnabled() ? "ON" : "OFF", mirrorEnabled() ? "ON" : "OFF"
    };
    f32 x, y;
    *(s8*)0x800338FC = 6;
    *(u32*)0x807FBB60 &= ~0x10;
    /* Hide the native up/down control sprite; rows include their own cursor. */
    *(s16*)0x80033674 = 0;
    krushaMenuTransform(data, 160.0f, 20.0f, &x, &y, 5, 0, 1.5f);
    dl = krushaPrintStyledText(dl, 1, 640, y * 4.0f, strings[41], 0x81);
    for (s32 row = 0; row < 6; row++) {
        s32 item = rows[row];
        krushaMenuTransform(data, 46.0f, 64.0f + 23.0f * row, &x, &y, 5, 0, 1.5f);
        dl = krushaPrintStyledText(dl, 0, x * 4, y * 4, labels[item], 1);
        dl = krushaPrintStyledText(dl, 0, (x + 156.0f) * 4, y * 4, values[item], 1);
        if (((u8*)data)[0x17] == item)
            dl = krushaPrintStyledText(dl, 0, (x - 17.0f) * 4, y * 4, ">", 1);
    }
    return dl;
}
