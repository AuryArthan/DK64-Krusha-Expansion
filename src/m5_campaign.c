#include "../include/m5_campaign.h"
#include "../include/krusha_progress.h"
#include "../include/m5_campaign.generated.h"
const M5Area* m5Area(s32 map) {
    for (int i=0;i<8;i++) if (m5Areas[i].map==map) return &m5Areas[i];
    return 0;
}
const M5Kasplat* m5Kasplat(s32 map) {
    for (int i=0;i<8;i++) if (m5Kasplats[i].map==map) return &m5Kasplats[i];
    return 0;
}
s32 m5FileAlias(s32 table,s32 map) {
    if (table!=10 && table!=16) return -1;
    if (table==16 && (!krushaEnabled() || !DetectAdventure())) return -1;
    for (int i=0;i<sizeof(m5Files)/sizeof(m5Files[0]);i++)
        if (m5Files[i].table==table && m5Files[i].map==map) return m5Files[i].index;
    return -1;
}
/* Earned blueprint time remains earned with Krusha hidden, like team GB credit. */
s32 m5HelmMinutes(void) {
    int (*nativeCount)(int,int,int)=(void*)0x80731AA8;
    int minutes=10+nativeCount(0x1FD,40,0);
    for (int i=0;i<8;i++) minutes+=krushaProgressRead(*(u8*)0x807467C8,KRUSHA_GB_BIT+i*5+4,1);
    return minutes;
}
