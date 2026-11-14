#include "../include/common.h"
#include "../include/krusha_recruitment.h"
#include "../include/krusha_progress.h"
#include "../include/m3_progress.h"
#include "../include/recruitment_room.generated.h"

extern s32 krushaPrisonVisitBusy(void);
extern void vanillaRecruitmentPlayerSpawn(s32,u8);

/* Read-only diagnostics: magic, changed Speed grants, spawn fallbacks. */
volatile u32 krushaRecruitmentTrace[3]={0x52513035,0,0};

int krushaRecruitmentContext(void) {
    /* DetectAdventure also accepts a copied mode during transitions. Require
     * the actual Adventure mode and exclude the frontend explicitly. */
    return DetectAdventure() && Gamemode==6 && CurrentMap!=80;
}
int krushaRecruitmentPlayable(void) {
    return krushaRecruitmentContext() && CurrentMap!=RECRUITMENT_ROOM_MAP &&
        !krushaPrisonVisitBusy() && krushaAvailable(krushaProgressActiveFile());
}
int krushaOriginalKongUnlocked(unsigned int kong) {
    static const u16 flags[5]={385,6,70,66,117};
    if (kong>=5) return 0;
    return kong==0 || StorySkip || checkFlag(flags[kong],0);
}
void krushaRecruitmentTick(void) {
    if (!krushaRecruitmentContext() || !krushaEnabled() ||
        krushaProgressActiveFile()>=3 || !StorySkip) return;
    /* Existing Speed ownership precedes the once-only native save request.
     * This safe helper performs no player/actor scan before initial spawn. */
    m3SpeedOwnership();
    if (krushaRecruitmentSpeedGrant(krushaProgressActiveFile(),StorySkip))
        krushaRecruitmentTrace[1]++;
}
void krushaRecruitmentPlayerSpawn(s32 exit,u8 player) {
    if (!player && krushaRecruitmentContext()) {
        krushaRecruitmentTick();
        /* A real native DK spawn, not a Krusha actor with a borrowed ID.
         * Animals and every non-Adventure/multiplayer path remain native. */
        if (Character==5 && !krushaRecruitmentPlayable()) {
            Character=0;
            krushaRecruitmentTrace[2]++;
        }
    }
    vanillaRecruitmentPlayerSpawn(exit,player);
}
