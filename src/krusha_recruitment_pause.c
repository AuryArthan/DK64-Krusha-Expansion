#include "../include/common.h"
#include "../include/krusha_progress.h"
#include "../include/krusha_recruitment.h"

/* Native totals have eight categories. Keep the ninth mapping owned here,
 * never in the adjacent native counters. Input still uses the native count
 * and angular spacing, so left/right, page changes and cleanup stay native. */
static s8 categories[9];
static u8 count;
/* Selected category, held mask, total, five rendered alphas, draw count. */
volatile u32 krushaColoredKeysPauseTrace[9];
/* Native16-frame turns; advance owner each8 frames.80 keeps both
 * the five-owner cycle and the16-frame rotation continuous at wrap. */
static const struct {
    u32 id; u8 across,down,flags,codec; u32 rgba;
    u8 animated,table; u16 width,height,frames,image[80];
} key_icon={0x4B524B00,1,1,0,2,0xFFFFFFFF,0,1,44,44,80,{
    7250,8000,8001,8002,8003,8004,8005,8006,
    8022,8023,8024,8025,8026,8027,8028,8029,
    7252,8030,8031,8032,8033,8034,8035,8036,
    8052,8053,8054,8055,8056,8057,8058,8059,
    7254,8060,8061,8062,8063,8064,8065,8066,
    8007,8008,8009,8010,8011,8012,8013,8014,
    7251,8015,8016,8017,8018,8019,8020,8021,
    8037,8038,8039,8040,8041,8042,8043,8044,
    7253,8045,8046,8047,8048,8049,8050,8051,
    8067,8068,8069,8070,8071,8072,8073,8074}};

extern void widescreenPauseSprite(void*,void*,s32,s32,f32,u8,s32);
extern Gfx* widescreenPauseFraction(s16,s16,s16,s16,Gfx*,s8,f32);
extern Gfx* widescreenImage(Gfx*,u16,s32,s32,s32,s32,s16,s16,f32,f32,s32,f32);

int krushaPauseTotalsCategory(void) {
    u8 selected=*(u8*)0x807FC80C;
    return selected<count ? categories[selected] : -1;
}

void krushaPauseTotalsBuild(void* menu) {
    u8* data=menu;
    count=0;
    for (int i=0;i<8;i++)
        if (((s16*)0x807FC828)[i]>0) categories[count++]=i;
    if (krushaEnabled() && DetectAdventure()) categories[count++]=8;
    /* Native hides detail tabs before the first GB. Defensive empty-page
     * support also avoids a division by zero if a state enters it early. */
    if (!count) categories[count++]=0;
    *(u8*)0x807FC83C=count;
    s16 spacing=4096/count;
    *(s16*)0x807FC83A=spacing;
    if (*(u8*)0x807FC80C>=count) *(u8*)0x807FC80C=0;
    for (int i=0;i<count;i++) {
        int kind=categories[i];
        void* sprite=kind==8 ? (void*)&key_icon : ((void**)0x807505D8)[kind];
        widescreenPauseSprite(menu,sprite,i*spacing,0,kind==5?1:kind==8?.525f:.75f,2,kind==5?8:5);
    }
    *(s16*)(data+0x10)=spacing**(u8*)0x807FC80C;
    widescreenPauseSprite(menu,(void*)0x80720C34,160,120,.75f,2,0);
}

Gfx* krushaPauseTotalsDraw(Gfx* dl,void* menu) {
    f32* data=menu;
    int kind=krushaPauseTotalsCategory();
    if (kind<0 || kind>8) return dl;
    char** labels=*(char***)0x807FC7E0;
    Gfx*(*text)(Gfx*,s16,s16,f32,char*)=(void*)0x806ABB98;
    dl=text(dl,640,116,.5f,kind==8?"COLORED KEYS":labels[18+kind]);
    dl=text(dl,640,60,.65f,labels[6]);
    f32 fade=data[0]>data[1]?data[0]:data[1];
    f32 scale=(1-fade)*.65f;
    if (scale<.01f) scale=.01f;
    s16 value,maximum;
    if (kind==8) {
        u32 keys=krushaRecruitmentKeys(krushaProgressActiveFile());
        value=0;maximum=5;
        u32 opacity=fade>=1?0:fade<=0?255:(1-fade)*255;
        krushaColoredKeysPauseTrace[0]=kind;
        krushaColoredKeysPauseTrace[1]=keys;
        for (int i=0;i<5;i++) {
            int collected=(keys>>i)&1;
            int frame=(ObjectModel2Timer>>1)&15;
            int image=frame ? 8000+i*15+frame-1 : 7250+i;
            value+=collected;
            u32 alpha=collected?opacity:opacity*72/255;
            krushaColoredKeysPauseTrace[3+i]=alpha;
            gDPPipeSync(dl++);
            gDPSetPrimColor(dl++,0,0,255,255,255,alpha);
            dl=widescreenImage(dl,image,0,2,44,44,(112+i*24)*4,860,1.8f,1.8f,180,0);
        }
        gDPPipeSync(dl++);
        gDPSetPrimColor(dl++,0,0,255,255,255,255);
        krushaColoredKeysPauseTrace[2]=value;
        krushaColoredKeysPauseTrace[8]++;
        return dl; /* The five keys replace only this category's fraction. */
    } else {
        value=((s16*)0x807FC828)[kind];
        maximum=((s16*)0x8075056C)[kind];
    }
    return widescreenPauseFraction(640,828,value,maximum,dl,1,scale);
}
