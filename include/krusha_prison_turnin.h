#ifndef KRUSHA_PRISON_TURNIN_H
#define KRUSHA_PRISON_TURNIN_H
/* Pure bounded choreography; the same controller is exercised on the host.
 * FINAL_READY means the fifth-lock/recruited word has committed atomically. */
enum { PRISON_SELECT, PRISON_KEY_FLY, PRISON_KEY_TURN, PRISON_LOCK_OPEN,
       PRISON_LOCK_COMMIT, PRISON_FINAL_READY, PRISON_TURN_DONE };
enum { PRISON_FLY_FRAMES=48, PRISON_TURN_FRAMES=30, PRISON_OPEN_FRAMES=30 };
/* phase, owner, age, committed this visit, pending, initial keys,
 * last committed owner, last committed lock mask. */
extern volatile unsigned int krushaPrisonTurnTrace[8];
unsigned int krushaPrisonPendingKeys(unsigned int file);
void krushaPrisonTurnBegin(unsigned int file);
int krushaPrisonTurnTick(void);
#endif
