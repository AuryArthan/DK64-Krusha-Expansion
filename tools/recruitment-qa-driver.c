/* Compiled ONLY with DK64_RECRUITMENT_QA=1. Never part of a playable candidate.
 * Calls production helpers in the native game thread. RAM commands provide
 * explicit quest-state test preconditions, not physical key/lock proof. */
#include "../include/common.h"
#include "../include/krusha_recruitment.h"
volatile u32 recruitmentQAMailbox[8]={0x52513034,0,0,0,0,0,0,0};
void recruitmentQATick(void) {
    u32 op=recruitmentQAMailbox[1],file=recruitmentQAMailbox[2],arg=recruitmentQAMailbox[3];
    int result=0;
    if (!op || op==0xFFFFFFFF) return;
    if (op==1) result=krushaRecruitmentCollectKey(file,arg);
    else if (op==2) result=krushaRecruitmentOpenLock(file,arg);
    else if (op==3) result=krushaRecruitmentMarkIntro(file);
    recruitmentQAMailbox[4]=result;
    recruitmentQAMailbox[5]=krushaRecruitmentKeys(file)|(krushaRecruitmentLocks(file)<<5)|
        (krushaRecruitmentRecruited(file)<<10)|(krushaRecruitmentIntroSeen(file)<<11);
    recruitmentQAMailbox[6]++;
    recruitmentQAMailbox[1]=0xFFFFFFFF;
}
