#include "../include/common.h"

enum { K_ROOL_DEFEATED = 0x1B0 };
typedef u8 (*SpawnerTest)(void*);
static SpawnerTest const nativeInRange = (SpawnerTest)0x80689F80;

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

static u8 rewardInRange(void* node) {
    /* Chunky's final punch sets this permanent flag on the Adventure file. */
    return DetectAdventure() && nativeInRange(node) && checkFlag(K_ROOL_DEFEATED, 0);
}

void completionCrateSetup(void* setup) {
    void (*nativeSetup)(void*) = (void*)0x80688FC0;
    nativeSetup(setup);
    if (CurrentMap != 34) return;
    for (u8* node = *(u8**)0x807FC400; node; node = *(u8**)(node + 0x68)) {
        s16 kind = *(s16*)node;
        s16 id = *(s16*)(node + 0x5A);
        if ((id == 620 && kind == 2) || (id == 621 && kind == 113))
            *(SpawnerTest*)(node + 0x5C) = rewardInRange;
    }
}
