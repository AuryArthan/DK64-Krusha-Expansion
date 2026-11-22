#include "../include/common.h"

extern Gfx* widescreenImage(Gfx*, u16, s32, s32, s32, s32, s16, s16,
                             f32, f32, s32, f32);

/* The first logo is copied into a cleared 320x240 CPU framebuffer.
 * The build supplies the asset width. Sample texel centres in the wide
 * rendition, and retain the exact one-to-one copy in the standard rendition. */
void krushaBootLogoCopy(u16* framebuffer, const u16* image, s32 width) {
    s32 displayed = ScreenRatio ? (3 * width + 2) / 4 : width;
    u16* row = framebuffer + 320 * ((240 - 48) / 2) + (320 - displayed) / 2;
    for (s32 y = 0; y < 48; y++, row += 320, image += width) {
        for (s32 x = 0; x < displayed; x++)
            row[x] = image[displayed == width ? x : (4 * x + 2) / 3];
    }
}

/* The bundled SDK uses old SetOtherMode/matrix bit fields with F3DEX2
 * opcodes. Use the verified native command words for those operations. */
static Gfx* command(Gfx* dl, u32 a, u32 b) {
    dl->words.w0 = a; dl->words.w1 = b; return dl + 1;
}

/* Called only by the original credit actor through widescreenLogo. Its
 * timing/fade and texture-cache lifetime remain native. No persistent heap
 * ownership or new per-frame allocations outside the native text renderer. */
Gfx* krushaIntroCredits(Gfx* dl) {
    void* texture = ((void*(*)(u16))0x8068C12C)(176);
    char* (*text)(s32, s32, s32) = (void*)0x8070E750;
    Gfx* (*print)(Gfx*, s16, s16, f32, char*) = (void*)0x806ABB98;
    s32 fade = *(u8*)0x800339D0 * 15;
    s32 scale = *(u8*)0x8074450C;
    if (scale < 1 || scale > 2) scale = 1;
    s32 left = (*(s16*)0x80744490 - 100 * scale) / 2;
    s32 top = 62 * scale;
    if (fade > 255) fade = 255;
    gDPPipeSync(dl++);
    gSPDisplayList(dl++, (void*)0x01000118);
    /* DK64's exact F3DEX2 matrix command. The bundled SDK's gSPMatrix macro
     * has the older flag layout (also see widescreen.c/searchlight). */
    dl->words.w0 = 0xDA380007;
    dl->words.w1 = 0x020000C0;
    dl++;
    dl = command(dl, 0xE200001C, 0x00504240);
    gDPSetCombineMode(dl++, G_CC_MODULATERGBA_PRIM, G_CC_MODULATERGBA_PRIM);
    gDPSetPrimColor(dl++, 0, 0, fade, fade, fade, 255);
    dl = command(dl, 0xE3001201, 0); /* point sampling */
    dl = command(dl, 0xE3000C00, 0); /* non-perspective rectangles */
    /* Each tile is at most 1024 bytes, safely inside 4KiB TMEM. Rectangle
     * ends are exclusive; load-tile ends inclusive. No source over-read. */
    for (s32 y = 0; y < 80; y += 16) {
        for (s32 x = 0; x < 100; x += 32) {
            s32 end = x + 32 < 100 ? x + 32 : 100;
            gDPLoadTextureTile(dl++, texture, G_IM_FMT_RGBA, G_IM_SIZ_16b,
                100, 80, x, y, end - 1, y + 15, 0,
                G_TX_CLAMP, G_TX_CLAMP, G_TX_NOMASK, G_TX_NOMASK, G_TX_NOLOD, G_TX_NOLOD);
            gSPTextureRectangle(dl++, (left + x * scale) * 4, (top + y * scale) * 4,
                (left + end * scale) * 4, (top + (y + 16) * scale) * 4, G_TX_RENDERTILE,
                x * 32, y * 32, 1024 / scale, 1024 / scale);
        }
    }
    gDPPipeSync(dl++);
    dl = command(dl, 0xE3001201, 0x2000);
    dl = command(dl, 0xE3000C00, 0x80000);
    gDPSetPrimColor(dl++, 0, 0, 255, 255, 255, fade);
    gDPSetCombineLERP(dl++, 0, 0, 0, TEXEL0, TEXEL0, 0, PRIMITIVE, 0,
                              0, 0, 0, TEXEL0, TEXEL0, 0, PRIMITIVE, 0);
    s16 center = *(s16*)0x80744490 * 2;
    dl = print(dl, center, 174 * 4 * scale, .38f * scale, text(13, 0, 1));
    /* Font 1 has comma/period glyphs but no semicolon. Compose it here,
     * rather than changing the shared font or silently drawing a blank. */
    char line[128];
    char* source = text(13, 1, 1);
    s32 mark = -1;
    s32 length = 0;
    while (length < sizeof(line) - 1 && source[length]) {
        line[length] = source[length];
        if (line[length] == ';') {
            mark = length;
            line[length] = ',';
        }
        length++;
    }
    line[length] = 0;
    dl = print(dl, center, 187 * 4 * scale, .38f * scale, line);
    if (mark >= 0) {
        s32 (*width)(s16, char*) = (void*)0x806FBD5C;
        s32 total = width(1, line);
        line[mark] = 0;
        s32 prefix = width(1, line);
        s32 comma = width(1, ",");
        s16 x = center + (2 * prefix + comma - total) * .76f * scale;
        /* Same native font/color; lift a period eight unscaled font units. */
        dl = print(dl, x, (187 * 4 - 12) * scale, .38f * scale, ".");
    }
    return dl;
}

/* Keep native fade and entrance offset, at the original vanilla title anchor.
 * The small expansion banner occupies the former Tag-Anywhere inset. The normal image projection already corrects widescreen. */
Gfx* krushaIntroTitle(Gfx* dl, u8 alpha, f32 offset) {
    dl = command(dl, 0xE200001C, 0x00504240);
    gDPSetPrimColor(dl++, 0, 0, 255, 255, 255, alpha);
    gDPSetCombineLERP(dl++, 0, 0, 0, TEXEL0, TEXEL0, 0, PRIMITIVE, 0,
                              0, 0, 0, TEXEL0, TEXEL0, 0, PRIMITIVE, 0);
    dl = command(dl, 0xE3001201, 0);
    return widescreenImage(dl, 44, 0, 2, 224, 144,
        *(s16*)0x80744490 / 2, *(s16*)0x80744494 / 2 - 20 + offset,
        1.0f, 1.0f, 0, 0.0f);
}
