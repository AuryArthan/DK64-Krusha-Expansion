#include "../include/common.h"
#include "../include/krusha_progress.h"

extern void krushaCollectTotals(void);
typedef u8 (*SpawnerTest)(void*);
static SpawnerTest const nativeInRange = (SpawnerTest)0x80689F80;
static u32 next_check;
static u8 unlocked;

f32 islesRambiSwimDepth(f32 nativeDepth, const playerData* actor) {
    if (CurrentMap != 34 || actor->characterID != 8 || actor->control_state != 0x4E)
        return nativeDepth;

    /* Rambi's vanilla model is about 33.5 world units tall. Add a
     * quarter of that in deep water, tapering to the native depth on shore. */
    f32 available = actor->waterSurface - actor->floor;
    if (available <= nativeDepth) return nativeDepth;
    f32 lowered = nativeDepth + 8.4f;
    return available < lowered ? available : lowered;
}

void completionCrateEntrySong(s32 song, f32 volume) {
    playSong(song, volume);
    /* The legacy CurrentActorPointer label refers to the last spawn. */
    const u8* crate = *(const u8**)0x807FBB40;
    if (CurrentMap == 34 && *(const u32*)(crate + 0x58) == 18)
        playSound(748, 0x7FFF, 63.0f, 1.0f, 0, 0);
}

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
