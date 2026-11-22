#include "../include/mirror_world_prints.h"
#include "../include/common.h"
#include "../include/recruitment_assets.generated.h"
#include "../include/recruitment_keys.generated.h"

/* Kept after the existing objects in link order so the established resident
 * code/data addresses stay unchanged. Native Model2 streaming stores only
 * the file index returned here, then assumes table25 when reloading. */
volatile u32 krushaModel2TextureTrace[4];

static void restorePrintToken(s32* table, s32* index) {
    if (*index >= MIRROR_EXTRA_BANK && *index < MIRROR_EXTRA_BANK + MIRROR_EXTRA_COUNT) {
        *index += MIRROR_EXTRA_TOKEN - MIRROR_EXTRA_BANK;
        *table = 25;
    } else if (*index >= MIRROR_WORLD_BANK && *index < MIRROR_WORLD_BANK + MIRROR_WORLD_COUNT) {
        *index += MIRROR_WORLD_TOKEN - MIRROR_WORLD_BANK;
        *table = 25;
    }
}

void krushaModel2TextureIdentity(void* texture,s32* table,s32* index) {
    void (*native)(void*,s32*,s32*)=(void*)0x8066B7AC;
    native(texture,table,index);
    krushaModel2TextureTrace[0]++;
    if (*table == 29) {
        restorePrintToken(table, index);
        return;
    }
    if (*table!=27) return;
    if (*index>=RECRUITMENT_TEXTURE_BASE && *index<RECRUITMENT_TEXTURE_BASE+RECRUITMENT_TEXTURE_COUNT) {
        *table=25;*index+=RECRUITMENT_TEXTURE_TOKEN-RECRUITMENT_TEXTURE_BASE;
    } else if (*index>=RECRUITMENT_KEY_PALETTE && *index<RECRUITMENT_KEY_PALETTE+RECRUITMENT_KEY_COUNT) {
        *table=25;*index+=RECRUITMENT_KEY_PALETTE_TOKEN-RECRUITMENT_KEY_PALETTE;
        krushaModel2TextureTrace[3]++;
    } else if (*index==68) {
        *table=25;*index=7410;
        krushaModel2TextureTrace[1]++;
    } else if (*index==85 || *index==86) {
        *table=25;*index+=7349;
        krushaModel2TextureTrace[2]++;
    }
    /* Native ownership/refcounts are untouched: only these two callers'
     * temporary reload tokens change. All other textures pass through. */
}

/* A map chunk unloads its image pointers and keeps only the index for the
 * next table-25 lookup. Preserve the display-list token on that round trip.
 * Native release still uses its own reference record for the real allocation. */
void mirrorMapTextureIdentity(void* texture, s32* table, s32* index) {
    ((void (*)(void*, s32*, s32*))0x8066B7AC)(texture, table, index);
    if (*table != 29) return;
    if (*index >= 75 && *index < 87) {
        *table = 25;
        *index = 8100 + (*index - 75);
    } else {
        restorePrintToken(table, index);
    }
}
