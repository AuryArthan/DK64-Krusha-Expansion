#include "../include/common.h"
#include "../include/krusha_progress.h"

extern void m4NativeDamage(void*,void*);
extern void krushaNativeActorDelete(void*);

#define ENCOUNTER_TRIGGER 250
#define PAD_X 1835.0f
#define PAD_Y 286.0f
#define PAD_Z 1490.0f

s32 m4EncounterPickupID=-1;
volatile u32 m4EncounterTrace[16]={0};
static s32 previous_map=-1;
static u32 previous_frame,pending_at;
static u8 pending,dropped;
static u32 hit_ids[5];
static u8 hits;
static struct {u8* pointer;u16 id;} grenades[24];

static int valid(void* p,u32 size) {return (u32)p>=0x80000000 && (u32)p<=0x80800000-size;}
static u32 frame(void) {return *(u32*)0x8076A064;}
static int won(void) {return krushaProgressRead(*(u8*)0x807467C8,KRUSHA_GB_BIT,1);}

int m4EncounterKlump(void* pointer) {
    u8* actor=pointer;
    if (CurrentMap!=7 || !valid(actor,0x180) || *(u32*)(actor+0x58)!=187) return 0;
    /* Klump has an extra module at+178. The common enemy AI at+174 owns
     * the reliable spawner link; do not copy Kasplat's module offsets. */
    u8* ai=*(u8**)(actor+0x174);
    if (!valid(ai,0x38)) return 0;
    u8* spawner=*(u8**)ai;
    return valid(spawner,0x48) && spawner[0]==9 && spawner[19]==ENCOUNTER_TRIGGER &&
        *(void**)(spawner+0x18)==actor;
}

void m4EncounterShout(void) {
    if (CurrentMap!=7 || !krushaEnabled() || !Player || won() || pending || dropped) return;
    f32 dx=Player->xPos-PAD_X,dz=Player->zPos-PAD_Z,dy=Player->yPos-PAD_Y;
    if (dx*dx+dz*dz>70*70 || dy < -20 || dy>35) return;
    u8* spawners=*(u8**)0x807FDC8C;
    int count=*(u16*)0x807FDC88;
    if (count>256 || !valid(spawners,count*0x48)) return;
    for (int i=0;i<count;i++) if (spawners[i*0x48+19]==ENCOUNTER_TRIGGER) {
        if (spawners[i*0x48+0x42]==5 || spawners[i*0x48+0x42]==6) return;
        pending=1;pending_at=frame();m4EncounterTrace[10]++;
        return;
    }
}

void m4EncounterDamage(void* target,void* source) {
    if (!m4EncounterKlump(target)) {m4NativeDamage(target,source);return;}
    u8* actor=target;
    u8* context=(void*)0x807FBB70;
    u32 type=valid(source,0x180) ? *(u32*)((u8*)source+0x58) : 0;
    u32 uid=valid(source,0x180) ? *(u32*)((u8*)source+0x54) : 0;
    m4EncounterTrace[6]=type;m4EncounterTrace[7]=context[0x200];
    int seen=0;
    for (int i=0;i<hits;i++) if (hit_ids[i]==uid) seen=1;
    m4EncounterTrace[13]=uid;m4EncounterTrace[14]=seen;m4EncounterTrace[15]++;
    if (!krushaEnabled() || type!=171 || seen || hits>=5 || *(s16*)(actor+0x134)<=0) {
        /* One native explosion can test several collision shapes. Preserve
         * the accepted hurt/death result on its second contact; clearing it
         * here would leave a zero-health Klump alive after the fifth hit. */
        context[0x200]=hits>=5 ? 9 : (type==171 && seen ? 4 : 0);
        return;
    }
    hit_ids[hits++]=uid;
    *(s16*)(actor+0x134)=5-hits;
    context[0x200]=hits==5 ? 9 : 4;
    m4EncounterTrace[1]=hits;m4EncounterTrace[2]=5-hits;
}

void m4EncounterKlumpUpdate(void) {
    u8* actor=*(u8**)0x807FBB40;
    void (*native)(void)=(void*)0x806AEE84;
    if (!m4EncounterKlump(actor)) {native();return;}
    if (!krushaEnabled() || !DetectAdventure() || won()) {krushaNativeActorDelete(actor);return;}
    u8* context=(void*)0x807FBB70;
    /* Shouts use the spawner's native instrument-immunity bit. Other instant
     * kill flags (shockwave/slam) must not bypass the five-projectile fight. */
    context[0x15]=0;
    if (hits<5 && context[0x200]==9) context[0x200]=0;
    native();
    m4EncounterTrace[8]=*(u16*)(actor+0x136);
    m4EncounterTrace[9]=*(u16*)(actor+0x134);
}

void m4EncounterThrow(s16 type,s16 model,f32 scale,s16 angle,f32 forward,f32 vertical,void* parent) {
    void (*native)(s16,s16,f32,s16,f32,f32,void*)=(void*)0x8069084C;
    if (!m4EncounterKlump(parent)) {native(type,model,scale,angle,forward,vertical,parent);return;}
    for (int n=-1;n<=1;n++) {
        native(type,model,scale,(angle+n*170)&4095,forward,vertical,parent);
        u8* node=*(u8**)0x807FC400;
        if (node) {
            for (int i=0;i<24;i++) if (!grenades[i].pointer) {
                grenades[i].pointer=node;grenades[i].id=*(u16*)(node+0x5A);break;
            }
        }
    }
    m4EncounterTrace[3]++;
}

int m4EncounterDrop(void* enemy) {
    if (!m4EncounterKlump(enemy)) return 0;
    if (dropped || won() || hits!=5) return 1;
    u8* actor=enemy;
    f32 x=*(f32*)(actor+0x7C),y=*(f32*)(actor+0x80)+30,z=*(f32*)(actor+0x84);
    int (*floor)(f32,f32,f32*)=(void*)0x80667110;
    if (floor(x,z,&y)) y+=4;
    int (*spawn)(s16,f32,f32,f32,f32,u8)=(void*)0x80632630;
    void (*collect)(s16,s16,s16,u8,u8,u8)=(void*)0x806F50C8;
    m4EncounterPickupID=spawn(9,x,y,z,0,0);
    if (m4EncounterPickupID>=0) {
        collect(m4EncounterPickupID,9,0,1,0,0);
        dropped=1;m4EncounterTrace[4]++;m4EncounterTrace[5]=m4EncounterPickupID;
    }
    return 1;
}

void m4EncounterGrenadeUpdate(void) {
    u8* actor=*(u8**)0x807FBB40;
    void (*native)(void)=(void*)0x80693EC0;
    if (CurrentMap==7 && krushaEnabled() && DetectAdventure()) {
        u8* node=*(u8**)0x807FC400;
        for (int n=0;node && n<512;n++,node=*(u8**)(node+0x68)) {
            if (*(void**)(node+0x44)!=actor) continue;
            for (int i=0;i<24;i++) if (grenades[i].pointer==node && grenades[i].id==*(u16*)(node+0x5A))
                *(s16*)(actor+0x136)=2 * *(s16*)(0x8074D0C4+50*4+2);
            break;
        }
    }
    native();
}

void m4EncounterTick(void) {
    if (CurrentMap!=previous_map || frame()<previous_frame) {
        pending=dropped=hits=0;m4EncounterPickupID=-1;
        for (int i=0;i<24;i++) grenades[i].pointer=0;
    }
    previous_map=CurrentMap;previous_frame=frame();
    if (CurrentMap!=7 || !krushaEnabled() || !DetectAdventure()) return;
    /* Resolve queued native grenade nodes by pointer AND native spawner ID;
     * never follow a freed parent or retain an unvalidated actor address. */
    for (int i=0;i<24;i++) if (grenades[i].pointer) {
        u8* node=*(u8**)0x807FC400;int found=0;
        for (int j=0;node && j<512;j++,node=*(u8**)(node+0x68)) {
            if (node!=grenades[i].pointer || *(u16*)(node+0x5A)!=grenades[i].id) continue;
            found=1;u8* a=*(u8**)(node+0x44);
            if (a && *(u32*)(a+0x58)==50) {
                s16 native_damage=*(s16*)(0x8074D0C4+50*4+2);
                *(s16*)(a+0x136)=native_damage*2;
            }
            break;
        }
        if (!found) grenades[i].pointer=0;
    }
    if (!pending || won() || !Player || Player->control_state==0x67 || frame()-pending_at<3) return;
    u8* spawners=*(u8**)0x807FDC8C;int count=*(u16*)0x807FDC88;
    if (count>256 || !valid(spawners,count*0x48)) return;
    for (int i=0;i<count;i++) {
        u8* record=spawners+i*0x48;
        if (record[19]!=ENCOUNTER_TRIGGER) continue;
        if (record[0x42]==5 || record[0x42]==6) {pending=0;return;}
        if (!spawnActor(187,0xEE)) return;
        u8* actor=*(u8**)0x807FBB44;
        void (*init)(void*,void*)=(void*)0x80726744;
        init(actor,record);
        *(u16*)(record+0x46)|=0x44; /* native: force loaded, instrument immune */
        *(s16*)(actor+0x134)=5;
        *(s16*)(actor+0x136)=2 * *(s16*)(0x8074D0C4+187*4+2);
        pending=0;hits=0;m4EncounterTrace[0]++;m4EncounterTrace[2]=5;
        m4EncounterTrace[11]=*(u32*)(actor+0x54);
        m4EncounterTrace[12]=frame();return;
    }
}

void m4EncounterInstall(void) {
    void (**functions)(void)=(void*)0x8074C0A0;
    functions[187]=m4EncounterKlumpUpdate;
    functions[50]=m4EncounterGrenadeUpdate;
    osWritebackDCache(functions+187,4);
    osWritebackDCache(functions+50,4);
}
