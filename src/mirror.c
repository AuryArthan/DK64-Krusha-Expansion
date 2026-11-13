#include "../include/common.h"

/* Alternate geometry is immutable ROM data; native loading, sharing and
 * reference-counted release own it. We never retain or edit a freed asset. */
s32 mirrorModeEnabled = 0;
s32 mirrorEnabled(void) { return mirrorModeEnabled; }

typedef struct { u32 address, normal, mirrored; } MirrorPatch;
static const MirrorPatch patches[] = {
    {0x806EA25C, 0x256CFFD3, 0x256C002D}, /* C-left orbit */
    {0x806EA2C8, 0x256C002D, 0x256CFFD3}, /* C-right orbit */
    {0x80657F2C, 0x0044082A, 0x0082082A}, /* mirrored chunk bounds */
    {0x80657F7C, 0x00C2082A, 0x0046082A},
    {0x8068BD0C, 0x46068201, 0x46103201}, /* sky projection */
    {0x80706A54, 0x03384023, 0x03194023}, /* sky scroll */
    {0x8065DFBC, 0x35CE0602, 0x35CE0206}, /* generated projected decals */
    {0x8065DFC4, 0x240F0406, 0x240F0604},
};

void mirrorReadController(void* raw) {
    ((void (*)(void*))0x80007454)(raw);
    if (!mirrorModeEnabled || CurrentMap == 80 || (TBVoidByte & 3) ||
        CutsceneActive == 3 || CutsceneActive == 4 ||
        (Player && ((u8*)Player)[0x154] == 0x42)) return;
    /* OSContPad is six bytes, unlike the four-byte adventure input copy.
     * Saturate the otherwise unrepresentable negation of -128. */
    for (s32 i = 0; i < 4; i++) {
        s8* x = (s8*)raw + i * 6 + 2;
        *x = *x == -128 ? 127 : -*x;
    }
}

void mirrorSetEnabled(s32 value) {
    mirrorModeEnabled = value != 0;
    for (u32 i = 0; i < sizeof(patches)/sizeof(patches[0]); i++) {
        u32 address = patches[i].address;
        *(volatile u32*)address = mirrorModeEnabled ? patches[i].mirrored : patches[i].normal;
        osWritebackDCache((void*)address, 4); osInvalICache((void*)address, 4);
    }
    *(volatile u32*)0x807599B0 = mirrorModeEnabled ? 0xBFB47AE1 : 0x3FB47AE1;
    /* Native osContGetReadData call; preserve its existing NOP delay slot. */
    *(volatile u32*)0x8060AC60 = 0x0C000000 | (((u32)mirrorReadController & 0x0FFFFFFF) >> 2);
    osWritebackDCache((void*)0x8060AC60, 4); osInvalICache((void*)0x8060AC60, 4);
}

s32 mirrorFileIndex(s32 format, s32 table, s32 index) {
    /* Options can change while the main-menu actors are already loaded.
     * Keep this entire scene native; adventure loads the selected bank. */
    if (!mirrorModeEnabled || CurrentMap == 80 || index < 0) return -1;
    if (table == 1 && index < 221) return index;
    if (table == 4 && index < 695) return 221 + index;
    if (table == 5 && index < 236) return 916 + index;
    if (table == 27 && index < 131 && (format == 4 || format == 5)) return 1152 + index;
    return -1;
}

extern void* vanillaBarrelFile(s32, s32, u8, u8);
void* mirrorFile(s32 format, s32 index, u8 synchronous, u8 unique) {
    ((void (*)(s32))0x8066B5F4)(28);
    u32** caches = (u32**)0x807F95A8;
    if (!caches[28]) {
        /* Table28 is uncompressed. Only model2 geometry shares a cache;
         * maps and actors keep their native independent allocations. */
        u32* cache = dk_malloc(1284 * 4);
        if (cache) {
            for (s32 i = 0; i < 1284; i++) cache[i] = 0;
            caches[28] = cache;
        }
    }
    u32* saved = caches[28];
    if (format != 4) caches[28] = 0;
    void* result = vanillaBarrelFile(28, index, synchronous, unique);
    caches[28] = saved;
    return result;
}
