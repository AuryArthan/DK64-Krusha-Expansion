#pragma GCC optimize("Os","no-strict-aliasing")
#include "../include/krusha_prison_turnin.h"
#include "../include/krusha_recruitment.h"

volatile unsigned int krushaPrisonTurnTrace[8];
static unsigned int turn_file;
unsigned int krushaPrisonPendingKeys(unsigned int file) {
    return krushaRecruitmentKeys(file)&~krushaRecruitmentLocks(file)&31;
}
void krushaPrisonTurnBegin(unsigned int file) {
    turn_file=file;
    for (unsigned int i=0;i<8;i++) krushaPrisonTurnTrace[i]=0;
    krushaPrisonTurnTrace[5]=krushaRecruitmentKeys(file);
}
int krushaPrisonTurnTick(void) {
    volatile unsigned int* t=krushaPrisonTurnTrace;
    unsigned int phase=t[0];
    if (phase>=PRISON_FINAL_READY) return 1;
    if (phase==PRISON_SELECT) {
        unsigned int pending=krushaPrisonPendingKeys(turn_file),owner=0;
        t[4]=pending;
        if (!pending) {t[0]=PRISON_TURN_DONE;return 1;}
        while (!(pending&(1u<<owner))) owner++;
        t[1]=owner;t[0]=PRISON_KEY_FLY;t[2]=0;
    } else if (phase==PRISON_LOCK_COMMIT) {
        /* No animation or button can spend a key twice. The durable helper
         * checks the active file, option, held key and saved opened mask. */
        if (!krushaRecruitmentOpenLock(turn_file,t[1])) {
            t[0]=PRISON_TURN_DONE;return 1;
        }
        t[3]++;t[6]=t[1];t[7]=krushaRecruitmentLocks(turn_file);
        /* The durable helper writes the fifth lock AND recruitment in one
         * eleven-bit transaction. Only now hand the scene its release lines. */
        if (t[7]==31) {t[0]=PRISON_FINAL_READY;t[2]=0;return 1;}
        t[0]=PRISON_SELECT;t[2]=0;
    } else {
        unsigned int duration=phase==PRISON_KEY_FLY?PRISON_FLY_FRAMES:
            phase==PRISON_KEY_TURN?PRISON_TURN_FRAMES:PRISON_OPEN_FRAMES;
        if (++t[2]>=duration) {
            t[2]=0;
            t[0]=phase+1;
        }
    }
    return 0;
}
