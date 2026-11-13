#include "../include/common.h"
#include "../include/recruitment_assets.generated.h"

/* Kept after the existing objects in link order so the established resident
 * code/data addresses stay unchanged. Native Model2 streaming stores only
 * the file index returned here, then assumes table25 when reloading. */
volatile u32 krushaModel2TextureTrace[4];

void krushaModel2TextureIdentity(void* texture,s32* table,s32* index) {
    void (*native)(void*,s32*,s32*)=(void*)0x8066B7AC;
    native(texture,table,index);
    krushaModel2TextureTrace[0]++;
    if (*table!=27) return;
    if (*index>=RECRUITMENT_TEXTURE_BASE && *index<RECRUITMENT_TEXTURE_BASE+RECRUITMENT_TEXTURE_COUNT) {
        *table=25;*index+=RECRUITMENT_TEXTURE_TOKEN-RECRUITMENT_TEXTURE_BASE;
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
