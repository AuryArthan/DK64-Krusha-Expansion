#ifndef KRUSHA_PRISON_TURNIN_H
#define KRUSHA_PRISON_TURNIN_H
/* Pure bounded choreography; the same controller is exercised on the host.
 * FINAL_READY means the fifth-lock/recruited word has committed atomically. */
enum { PRISON_SELECT, PRISON_KEY_FLY, PRISON_KEY_TURN, PRISON_LOCK_OPEN,
       PRISON_LOCK_COMMIT, PRISON_FINAL_READY, PRISON_TURN_DONE };
enum {
    PRISON_FLY_BASE_FRAMES = 48,
    /* Flight speed relative to the original (1.15 × 1.10). */
    PRISON_FLY_SPEED_NUM = 253, PRISON_FLY_SPEED_DEN = 200,
    /* Enter the turn on the first whole tick at or beyond the lock. */
    PRISON_FLY_FRAMES = (PRISON_FLY_SPEED_DEN * PRISON_FLY_BASE_FRAMES + PRISON_FLY_SPEED_NUM - 1) / PRISON_FLY_SPEED_NUM,
    PRISON_TURN_FRAMES = 30, PRISON_OPEN_FRAMES = 30
};
/* phase, owner, age, committed this visit, pending, initial keys,
 * last committed owner, last committed lock mask. */
extern volatile unsigned int krushaPrisonTurnTrace[8];
unsigned int krushaPrisonPendingKeys(unsigned int file);
void krushaPrisonTurnBegin(unsigned int file);
int krushaPrisonTurnTick(void);
#endif
