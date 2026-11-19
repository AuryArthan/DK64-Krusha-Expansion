/* Host adapter for the ACTUAL production recruitment state machine.
 * Compile together with src/krusha_recruitment.c. No emulator/code patches. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../include/krusha_progress.h"
#include "../include/krusha_recruitment.h"
static unsigned char bits[3][512];
static unsigned int active, saves, words, single_writes;
static int adventure=1, enabled=1;
static int context=1,scene,speed;
signed char StorySkip;
static unsigned int originals=31;
int DetectAdventure(void){return adventure;}
int krushaEnabled(void){return enabled;}
int krushaRecruitmentContext(void){return context&&adventure;}
int krushaRecruitmentPlayable(void){return krushaRecruitmentContext()&&!scene&&krushaAvailable(active);}
int krushaOriginalKongUnlocked(unsigned int kong){assert(kong<5);return kong==0||speed||(originals&(1u<<kong));}
unsigned int krushaProgressActiveFile(void){return active;}
int krushaProgressRead(unsigned int file,unsigned int bit,unsigned int width){
    unsigned int i,value=0;assert(file<3 && bit+width<=512);
    for(i=0;i<width;i++)value|=bits[file][bit+i]<<i;
    return value;
}
void krushaProgressWrite(unsigned int file,unsigned int bit,unsigned int width,unsigned int value){
    unsigned int i;assert(file<3 && bit+width<=512);single_writes++;
    for(i=0;i<width;i++)bits[file][bit+i]=(value>>i)&1;
}
void krushaProgressQuestWrite(unsigned int file,unsigned int value){
    unsigned int i;assert(file<3 && value<2048);words++;
    for(i=0;i<11;i++)bits[file][496+i]=(value>>i)&1;
}
void krushaProgressRequestSave(void){saves++;}
static unsigned int orders[120][5],count;
static unsigned long interleavings;
static void permute(unsigned int depth,unsigned int mask,unsigned int *order){
    unsigned int i;if(depth==5){memcpy(orders[count++],order,5*sizeof(*order));return;}
    for(i=0;i<5;i++)if(!(mask&(1u<<i))){order[depth]=i;permute(depth+1,mask|(1u<<i),order);}
}
static void reset(void){
    unsigned int f,i;memset(bits,0,sizeof(bits));saves=words=single_writes=0;
    for(f=0;f<3;f++)for(i=0;i<512;i++)if(i<496||i>509)bits[f][i]=(i+f)&1;
    for(f=0;f<3;f++){bits[f][507]=f&1;bits[f][508]=(f+1)&1;}
}
static void mixed_orders(unsigned int keys,unsigned int locks,unsigned int depth){
    unsigned int k,before_saves=saves,before_words=words;
    unsigned char saved[512];memcpy(saved,bits[active],sizeof(saved));
    assert(krushaRecruitmentKeys(active)==keys&&krushaRecruitmentLocks(active)==locks);
    assert(krushaRecruitmentRecruited(active)==(depth==10));
    if(depth==10){interleavings++;return;}
    for(k=0;k<5;k++){
        if(!(keys&(1u<<k))){
            assert(!krushaRecruitmentOpenLock(active,k)&&saves==before_saves);
            assert(krushaRecruitmentCollectKey(active,k));
            assert(saves==before_saves+1&&words==before_words+1);
            mixed_orders(keys|(1u<<k),locks,depth+1);
        }else if(!(locks&(1u<<k))){
            assert(krushaRecruitmentOpenLock(active,k));
            assert(saves==before_saves+1&&words==before_words+1);
            mixed_orders(keys,locks|(1u<<k),depth+1);
        }else continue;
        memcpy(bits[active],saved,sizeof(saved));saves=before_saves;words=before_words;
    }
}
static void availability_tests(void){
    unsigned int f,mode,mask;int current,dir;unsigned long cases=0;
    for(f=0;f<3;f++)for(mode=0;mode<64;mode++)for(mask=0;mask<32;mask++){
        int roster[6],n=0,k;reset();active=f;
        enabled=mode&1;speed=(mode>>1)&1;adventure=(mode>>2)&1;
        context=(mode>>3)&1;scene=(mode>>4)&1;originals=mask;
        if(mode&32){for(k=496;k<=506;k++)bits[f][k]=1;}
        for(k=0;k<6;k++)if(k==5?krushaRecruitmentPlayable():krushaOriginalKongUnlocked(k))roster[n++]=k;
        assert(n>0);
        for(current=0;current<6;current++)for(dir=-1;dir<=1;dir+=2){
            int expected=dir>0?roster[0]:roster[n-1];
            if(dir>0){for(k=0;k<n;k++)if(roster[k]>current){expected=roster[k];break;}}
            else{for(k=n-1;k>=0;k--)if(roster[k]<current){expected=roster[k];break;}}
            assert(krushaNextCharacter(current,dir)==expected);cases++;
        }
        assert(krushaAvailable(f)==(enabled&&!!(mode&32)));
        assert(!krushaAvailable(3)&&!krushaAvailable(255));
        assert(!saves&&!words&&!single_writes);
        assert(krushaNextCharacter(6,1)==6&&krushaNextCharacter(-1,-1)==-1&&krushaNextCharacter(2,0)==2);
    }
    for(f=0;f<3;f++)for(mode=0;mode<16;mode++){
        unsigned char old[3][512];unsigned int g,i;
        reset();active=f;enabled=mode&1;speed=(mode>>1)&1;adventure=(mode>>2)&1;context=(mode>>3)&1;
        bits[f][496]=1;bits[f][501]=1;bits[f][509]=1;memcpy(old,bits,sizeof(bits));
        assert(!krushaRecruitmentSpeedGrant((f+1)%3,1));
        assert(!krushaRecruitmentSpeedGrant(3,1));
        if(enabled&&speed&&adventure&&context){
            assert(krushaRecruitmentSpeedGrant(f,speed));assert(krushaRecruitmentRecruited(f));
            assert(saves==1&&words==1&&!single_writes);
            for(i=0;i<100;i++)assert(!krushaRecruitmentSpeedGrant(f,speed));
            assert(saves==1&&words==1);assert(krushaAvailable(f));
            speed=0;assert(!krushaRecruitmentSpeedGrant(f,speed)&&krushaAvailable(f));
            enabled=0;assert(!krushaAvailable(f));enabled=1;assert(krushaAvailable(f));
        }else{assert(!krushaRecruitmentSpeedGrant(f,speed));assert(!memcmp(old,bits,sizeof(bits)));}
        for(g=0;g<3;g++)for(i=0;i<512;i++)if(g!=f||i<496||i>506)assert(bits[g][i]==old[g][i]);
    }
    printf("PASS: %lu R05 roster cases, read-only availability, scene/option guards, once-only Speed grant and persistence semantics\n",cases);
}

static void key_eligibility_tests(void) {
    unsigned int f,mode,owner,character,player;unsigned long cases=0;
    for(f=0;f<3;f++)for(mode=0;mode<256;mode++)for(owner=0;owner<7;owner++) {
        unsigned char old[3][512];int expected;
        reset();active=f;enabled=mode&1;adventure=(mode>>1)&1;
        context=(mode>>2)&1;speed=StorySkip=!!(mode&128);originals=(mode&8)?31:0;
        if(mode&16)bits[f][496+(owner<5?owner:0)]=1;
        if(mode&32){unsigned int k;for(k=496;k<=506;k++)bits[f][k]=1;}
        if(mode&64)active=(f+1)%3;
        memcpy(old,bits,sizeof(bits));
        expected=owner<5 && !speed && active==f && enabled && adventure && context &&
            (owner==0 || originals) && !(mode&16) && !(mode&32);
        assert(krushaRecruitmentKeyVisible(f,owner)==expected);
        assert(!krushaRecruitmentKeyVisible(3,owner));
        for(character=0;character<7;character++)for(player=0;player<2;player++) {
            assert(krushaRecruitmentKeyCollectible(f,owner,character,player)==
                (expected && character==owner && !player));cases++;
        }
        assert(!memcmp(old,bits,sizeof(bits))&&!saves&&!words&&!single_writes);
    }
    enabled=adventure=context=1;speed=StorySkip=0;originals=31;active=0;reset();
    printf("PASS: %lu R09 actual key eligibility cases, native DK availability, hidden original owners, wrong owner/player/file, option/context/collected/recruited guards; read-only\n",cases);
}

int main(void){
    unsigned int f,i,j,k,order[5],before,keys,locks;
    unsigned char original[3][512];permute(0,0,order);assert(count==120);
    for(f=0;f<3;f++)for(i=0;i<120;i++)for(j=0;j<120;j++){
        reset();active=f;memcpy(original,bits,sizeof(bits));
        assert(!krushaRecruitmentRecruited(f)&&!krushaRecruitmentKeys(f)&&!krushaRecruitmentLocks(f));
        for(k=0;k<5;k++)assert(!krushaRecruitmentOpenLock(f,k));
        assert(!saves&&!words);
        assert(krushaRecruitmentMarkIntro(f)&&!krushaRecruitmentMarkIntro(f));
        keys=locks=0;
        for(k=0;k<5;k++){
            assert(krushaRecruitmentCollectKey(f,orders[i][k]));keys|=1u<<orders[i][k];
            assert(krushaRecruitmentKeys(f)==keys&&!krushaRecruitmentRecruited(f));
            before=saves;assert(!krushaRecruitmentCollectKey(f,orders[i][k])&&saves==before);
        }
        for(k=0;k<5;k++){
            assert(krushaRecruitmentOpenLock(f,orders[j][k]));locks|=1u<<orders[j][k];
            assert(krushaRecruitmentLocks(f)==locks);
            assert(krushaRecruitmentRecruited(f)==(k==4));
            before=saves;assert(!krushaRecruitmentOpenLock(f,orders[j][k])&&saves==before);
        }
        assert(saves==11&&words==10&&single_writes==1);
        for(k=0;k<3;k++)for(before=0;before<512;before++)
            if(k!=f||before<496||before>509||before==507||before==508)assert(bits[k][before]==original[k][before]);
    }
    reset();active=0;
    for(i=0;i<8;i++){
        adventure=i&1;enabled=(i>>1)&1;active=(i>>2)&1;
        if(adventure&&enabled&&active==0)continue;
        assert(!krushaRecruitmentCollectKey(0,0));assert(!krushaRecruitmentOpenLock(0,0));assert(!krushaRecruitmentMarkIntro(0));
    }
    adventure=enabled=1;active=0;
    for(f=3;f<8;f++){
        assert(!krushaRecruitmentKeys(f)&&!krushaRecruitmentLocks(f)&&!krushaRecruitmentRecruited(f)&&!krushaRecruitmentIntroSeen(f));
        assert(!krushaRecruitmentCollectKey(f,0)&&!krushaRecruitmentOpenLock(f,0)&&!krushaRecruitmentMarkIntro(f));
    }
    for(i=5;i<10;i++)assert(!krushaRecruitmentCollectKey(0,i)&&!krushaRecruitmentOpenLock(0,i));
    assert(!saves&&!words&&!single_writes);
    /* Malformed fixtures do not claim recruitment or unopened/absent keys. */
    bits[0][506]=1;bits[0][501]=1;
    assert(!krushaRecruitmentRecruited(0)&&!krushaRecruitmentLocks(0));
    for(f=0;f<3;f++){reset();active=f;mixed_orders(0,0,0);}
    assert(interleavings==340200);
    availability_tests();
    key_eligibility_tests();
    puts("PASS: 340,200 valid interleaved quest histories and 43,200 preservation cases across three files; guards, idempotence, final commit, neighbors and malformed reads");
    return 0;
}
