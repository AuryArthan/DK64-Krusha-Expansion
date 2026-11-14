#include "../include/common.h"
#include "../include/krusha_progress.h"
#include "../include/krusha_recruitment.h"
#include "../include/krusha_identity.h"

extern void vanillaFileSummaryInit(void* actor, s32 input);
extern Gfx* vanillaFileSummaryDraw(void* actor, Gfx* dl);
extern s32 vanillaCompletionPercentage(void);
extern void krushaMenuAddSprite(void*, const void*, s32, s32, f32, u8, s32);
extern s32 krushaMenuTransform(void*, f32, f32, f32*, f32*, s32, s8, f32);

/* Native 32x64 two-tile RGBA16 portrait descriptor, using the approved art.
 * The existing custom texture loader owns/free-caches table-27 files normally.
 * Unique sprite ID avoids collision with the native portrait cache. */
typedef struct FaceSprite {
    u32 id;
    u8 across, down, flags, codec;
    u32 rgba;
    u8 unkC, table;
    u16 width, height, frames;
    u16 images[2];
} FaceSprite;

static const FaceSprite krusha_face = {
    0x4B525553, 2, 1, 0, 2, 0xFFFFFFFF, 0, 1, 32, 64, 1, {7001, 7002},
};

const void* krushaProgressFace(void) { return &krusha_face; }

/* Native scale slot5 overlaps erase-confirmation state at80033FAC. Keep all
 * three sixth-face values resident; native arrays remain strictly five-wide. */
f32 krushaFilePortraitTransform[3] = {-200.0f, -200.0f, 1.0f};
s32 krushaFilePortraitUnlocked;
u8 krushaFilePortraitShade = KRUSHA_IDENTITY_GRAY;

s32 krushaCompletionPercentage(void) {
    /* Native weights, truncation and the 201-GB/exact-100 special cases stay
     * native. Its call to the totals collector now includes all six. */
    s32 ordinary = vanillaCompletionPercentage();
    /* Planned225 GBs contribute90%;40 native medals8%,20 fairies4%,
     * ten crowns5%,eight keys2%,two company coins1%: native maximum110.
     * Reserve111 for the complete permanent-category predicate. */
    return krushaProgressFullSet() ? 111 : ordinary;
}

void krushaFileSummaryInit(void* actor, s32 input) {
    int level, total = 0;
    u8* data = *(u8**)((u8*)actor + 0x174);
    vanillaFileSummaryInit(actor, input);
    /* Native init loads the selected file, including our sixth RAM record. */
    krushaFilePortraitUnlocked = krushaAvailable(krushaProgressActiveFile());
    krushaFilePortraitShade = krushaFilePortraitUnlocked ? 255 : KRUSHA_IDENTITY_GRAY;
    for (level = 0; level < 8; level++) total += MovesBase[5].gb_count[level];
    *(s32*)0x8003380C += total; /* Earned totals remain credited when OFF. */
    if (krushaEnabled()) {
        /* Do not grow native position/scale or unlock/color arrays. The
         * sixth sprite callback reads its separate resident transform. */
        const void* face = krushaFilePortraitUnlocked ?
            (const void*)&krusha_face : (const void*)0x807211D0;
        krushaMenuAddSprite(data, face, 5, 5, 0.8f, 2, 15);
    }
}

Gfx* krushaFileSummaryDraw(void* actor, Gfx* dl) {
    u8* data = *(u8**)((u8*)actor + 0x174);
    dl = vanillaFileSummaryDraw(actor, dl);
    if (krushaEnabled()) {
        for (int i = 0; i < 6; i++) {
            f32 x, y, scale = 2.5f;
            krushaMenuTransform(data, 48.0f + 45.0f * i, 85.0f,
                               &x, &y, 4, 0, 1.5f);
            /* The selected-file snapshot comes from native init, never a
             * stale Adventure actor or a prospective Speed grant. */
            if (i == 5 ? krushaFilePortraitUnlocked :
                *(u8*)(0x80033804 + i)) scale *= 0.85f;
            if (i == 5) {
                krushaFilePortraitTransform[0] = x * 4.0f - 32.0f;
                krushaFilePortraitTransform[1] = y * 4.0f - 100.0f;
                krushaFilePortraitTransform[2] = scale * 1.333f;
            } else {
                ((f32*)0x80033F68)[i] = x * 4.0f - 32.0f;
                ((f32*)0x80033F80)[i] = y * 4.0f - 100.0f;
                ((f32*)0x80033F98)[i] = scale * 1.333f;
            }
        }
    }
    return dl;
}
