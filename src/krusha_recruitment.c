#include "../include/krusha_progress.h"
#include "../include/krusha_recruitment.h"

/* Keep the state machine independent of actor pointers and native save
 * internals. Native adapters live in krusha_progress.c. This also lets the
 * real state machine run under a host fixture for every key/lock order. */
extern int DetectAdventure(void);
extern int krushaEnabled(void);

unsigned int krushaRecruitmentKeys(unsigned int file) {
    return file<3 ? krushaProgressRead(file,KRUSHA_KEYS_BIT,5) : 0;
}
unsigned int krushaRecruitmentLocks(unsigned int file) {
    return file<3 ? krushaProgressRead(file,KRUSHA_LOCKS_BIT,5)&krushaRecruitmentKeys(file) : 0;
}
int krushaRecruitmentRecruited(unsigned int file) {
    return file<3 && krushaRecruitmentLocks(file)==31 &&
        krushaProgressRead(file,KRUSHA_RECRUITED_BIT,1);
}
int krushaRecruitmentIntroSeen(unsigned int file) {
    return file<3 && krushaProgressRead(file,KRUSHA_INTRO_BIT,1);
}
static int writable(unsigned int file) {
    return file<3 && DetectAdventure() && krushaEnabled() &&
        file==krushaProgressActiveFile();
}
static int commit(unsigned int file,unsigned int keys,unsigned int locks) {
    locks &= keys;
    krushaProgressQuestWrite(file,keys|(locks<<5)|((locks==31)<<10));
    krushaProgressRequestSave();
    return 1;
}
int krushaRecruitmentCollectKey(unsigned int file,unsigned int owner) {
    unsigned int keys;
    if (!writable(file) || owner>=5) return 0;
    keys=krushaRecruitmentKeys(file);
    if (keys&(1u<<owner)) return 0;
    return commit(file,keys|(1u<<owner),krushaRecruitmentLocks(file));
}
int krushaRecruitmentOpenLock(unsigned int file,unsigned int owner) {
    unsigned int keys,locks,mask;
    if (!writable(file) || owner>=5) return 0;
    keys=krushaRecruitmentKeys(file);locks=krushaRecruitmentLocks(file);mask=1u<<owner;
    if (!(keys&mask) || (locks&mask)) return 0;
    return commit(file,keys,locks|mask);
}
int krushaRecruitmentMarkIntro(unsigned int file) {
    if (!writable(file) || krushaRecruitmentIntroSeen(file)) return 0;
    krushaProgressWrite(file,KRUSHA_INTRO_BIT,1,1);
    krushaProgressRequestSave();
    return 1;
}
