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

/* Keep the steering in the native walking step, before terrain and fence tests. */
static void steer(actorData* actor, int bearing, int turn, int routeBearing) {
    int reverse=actor->hSpeed<0 ? 2048 : 0;
    int heading=actor->next_facing_angle+reverse;
    int delta=((heading-bearing+2048)&4095)-2048;
    if (delta<=-turn || delta>=turn) return;
    int left=((heading-routeBearing)&4095)>=2048;
    actor->next_facing_angle=(bearing+(left ? -turn : turn)+reverse)&4095;
    if (actor->control_state==1 || actor->control_state==35)
        actor->facing_angle=actor->next_facing_angle;
}

static s16 obstacleBearing(f32 x,f32 z) {
    s16 (*angle)(f32,f32,f32,f32)=(void*)0x80665DE0;
    return angle(x,z,0,0);
}

typedef struct {
    s16 x,z,minY,maxY;
    u8 edges[8];
} BuildingFootprint;

/* The first four normals follow the world axes and the last four are diagonals.
 * Each heading points inward; the steering step turns away from it. */
static const struct {s8 x,z; s16 bearing;} normals[] = {
    {1,0,3072},{-1,0,1024},{0,1,2048},{0,-1,0},
    {1,-1,3584},{-1,1,1536},{-1,-1,512},{1,1,2560}
};
/* Factory block tower has seven outside faces. Caves setup object 60 includes
 * Candy's porch and walls at Big Klump's torso height. Distances are X/Z
 * projections from the building center; zero means the face is unused. */
static const BuildingFootprint tower={2416,1297,1000,1065,{100,100,100,100,160,160,120,0}};
static const BuildingFootprint shop={3282,2177,80,160,{63,61,70,69,77,93,114,99}};

static void steerPastBuilding(actorData* actor, const BuildingFootprint* building) {
    if (actor->yPos<building->minY || actor->yPos>building->maxY) return;
    f32 x=actor->xPos-building->x, z=actor->zPos-building->z;
    f32 clearance=-1000;
    int bearing=0;
    for (int i=0;i<8;i++) {
        if (!building->edges[i]) continue;
        f32 gap=normals[i].x*x+normals[i].z*z-building->edges[i];
        if (i>=4)
            gap*=0.70710678f;
        if (gap>46) return;
        if (gap>clearance) {clearance=gap;bearing=normals[i].bearing;}
    }
    /* Use the center to pick a consistent route along successive faces,
     * including when Krusha waits directly opposite a long flat wall. */
    int turn=1024+(int)((26-clearance)*28);
    if (turn>1600) turn=1600;
    steer(actor,bearing,turn,obstacleBearing(-x,-z));
}

void m5SteerPastScenery(actorData* actor) {
    if (actor->hSpeed==0) return;
    if (CurrentMap==26 || CurrentMap==72) {
        steerPastBuilding(actor,CurrentMap==26 ? &tower : &shop);
        return;
    }
    for (int i=0;i<sizeof(m5Trunks)/sizeof(m5Trunks[0]);i++) {
        if (m5Trunks[i].map!=CurrentMap) continue;
        f32 height=actor->yPos-m5Trunks[i].y;
        if (height < -25 || height > 105) continue;
        f32 x=m5Trunks[i].x-actor->xPos, z=m5Trunks[i].z-actor->zPos;
        f32 distance2=x*x+z*z;
        if (distance2>46*46) continue;
        int bearing=obstacleBearing(x,z);
        steer(actor,bearing,1328-(int)(distance2*0.45f),bearing);
        return;
    }
}
