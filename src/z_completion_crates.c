#include "../include/common.h"
#include "../include/krusha_progress.h"

extern void krushaCollectTotals(void);
typedef u8 (*SpawnerTest)(void*);
static SpawnerTest const nativeInRange = (SpawnerTest)0x80689F80;
static u32 next_check;
static u8 unlocked;

static u8 rewardInRange(void* node) {
    if (!DetectAdventure() || !nativeInRange(node)) return 0;
    /* Refresh on approach, then at most once per second in the endgame.
     * A final pickup on the Isles can unlock both crates during this visit. */
    if (!unlocked && MovesBase[5].gb_count[7] == 3 &&
        ObjectModel2Timer >= next_check) {
        next_check = ObjectModel2Timer + 30;
        krushaCollectTotals();
        unlocked = krushaProgressFullSet();
    }
    return unlocked;
}

void completionCrateSetup(void* setup) {
    void (*nativeSetup)(void*) = (void*)0x80688FC0;
    nativeSetup(setup);
    if (CurrentMap != 34) return;
    next_check = unlocked = 0;
    for (u8* node = *(u8**)0x807FC400; node; node = *(u8**)(node + 0x68)) {
        s16 kind = *(s16*)node;
        s16 id = *(s16*)(node + 0x5A);
        if ((id == 620 && kind == 2) || (id == 621 && kind == 113))
            *(SpawnerTest*)(node + 0x5C) = rewardInRange;
    }
}
