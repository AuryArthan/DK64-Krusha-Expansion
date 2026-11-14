#ifndef KRUSHA_RECRUITMENT_H
#define KRUSHA_RECRUITMENT_H

/* Read-only file queries never select a file or grant progress. Invalid file
 * IDs return zero. Mutators accept ONLY the active Adventure file with the
 * Krusha option enabled; return1 for a change and0 for a rejected/repeated
 * operation. R04 stores the quest; later milestones connect world objects. */
unsigned int krushaRecruitmentKeys(unsigned int file);
unsigned int krushaRecruitmentLocks(unsigned int file);
int krushaRecruitmentRecruited(unsigned int file);
int krushaRecruitmentIntroSeen(unsigned int file);
int krushaRecruitmentCollectKey(unsigned int file, unsigned int owner);
int krushaRecruitmentOpenLock(unsigned int file, unsigned int owner);
int krushaRecruitmentMarkIntro(unsigned int file);
/* Availability is read-only and never treats a frontend Speed preview as a
 * saved grant. The active Adventure tick/spawn owns the once-only bypass. */
int krushaAvailable(unsigned int file);
int krushaRecruitmentSpeedGrant(unsigned int file,int speed);
int krushaNextCharacter(int current,int direction);
int krushaRecruitmentContext(void);
int krushaRecruitmentPlayable(void);
int krushaOriginalKongUnlocked(unsigned int kong);
void krushaRecruitmentTick(void);

#endif
