/* Exercise the actual production R13 controller and existing transactions. */
#define main existing_state_main
#include "krusha-recruitment-state-test.c"
#undef main
#include "../include/krusha_prison_turnin.h"
static unsigned int population(unsigned int value) {
    unsigned int n=0;for (;value;value>>=1)n+=value&1;return n;
}
static void initialize(unsigned int file,unsigned int keys,unsigned int locks) {
    reset();active=file;enabled=adventure=context=1;scene=speed=StorySkip=0;
    for (unsigned int i=0;i<5;i++) {bits[file][496+i]=(keys>>i)&1;bits[file][501+i]=(locks>>i)&1;}
    bits[file][506]=(locks==31);
}
static void finish(unsigned int file,unsigned int keys,unsigned int initial) {
    unsigned char preserved[3][512];memcpy(preserved,bits,sizeof(bits));
    unsigned int guard=0,previous=krushaRecruitmentLocks(file);
    while (krushaPrisonTurnTrace[0]<PRISON_FINAL_READY) {
        unsigned int phase=krushaPrisonTurnTrace[0],pending=keys&~previous;
        krushaPrisonTurnTick();assert(++guard<700);
        unsigned int now=krushaRecruitmentLocks(file);
        if (now!=previous) {
            unsigned int owner=0;while (!(pending&(1u<<owner)))owner++;
            assert(phase==PRISON_LOCK_COMMIT);
            assert(now==(previous|(1u<<owner)));
            previous=now;
        }
        assert(krushaRecruitmentKeys(file)==keys);
        assert(krushaRecruitmentRecruited(file)==(now==31));
        for(unsigned int f=0;f<3;f++)for(unsigned int bit=0;bit<512;bit++)
            if(f!=file || bit<496 || bit>506)assert(bits[f][bit]==preserved[f][bit]);
    }
    unsigned int expected=population(keys&~initial);
    assert(population(krushaRecruitmentLocks(file)^initial)==expected);
    assert(krushaPrisonTurnTrace[0]==(keys==31 && initial!=31?PRISON_FINAL_READY:PRISON_TURN_DONE));
}
int main(void) {
    existing_state_main();unsigned int cases=0,boundaries=0;
    for(unsigned int file=0;file<3;file++)for(unsigned int keys=0;keys<32;keys++)
        for(unsigned int locks=0;locks<32;locks++)if(!(locks&~keys)) {
            initialize(file,keys,locks);krushaPrisonTurnBegin(file);finish(file,keys,locks);
            unsigned int count=saves,mask=krushaRecruitmentLocks(file);
            for(unsigned int i=0;i<100;i++)assert(krushaPrisonTurnTick());
            assert(saves==count);krushaPrisonTurnBegin(file);finish(file,keys,mask);
            assert(saves==count);cases++;
        }
    /* Restart the animation controller at every native frame. Committed
     * locks persist; precommit motion can replay without losing the key. */
    for(unsigned int cut=0;cut<600;cut++) {
        initialize(0,31,0);krushaPrisonTurnBegin(0);
        for(unsigned int i=0;i<cut;i++)krushaPrisonTurnTick();
        unsigned int locks=krushaRecruitmentLocks(0),count=saves;
        krushaPrisonTurnBegin(0);finish(0,31,locks);
        assert(saves==5 && count<=5);boundaries++;
    }
    printf("PASS: %u R13 file/mask cases, %u interruption frames, ordered single commits, replay idempotency, held-key preservation and atomic final recruitment\n",cases,boundaries);
    return 0;
}
