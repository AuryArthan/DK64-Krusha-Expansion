#include "../include/common.h"
#include "../include/krusha_progress.h"
#include "../include/m5_campaign.h"

extern void m4NativeDamage(void*,void*);
extern s32 m4NativePlayerDamage(u8,s8);
extern s32 m4EncounterFindPickup(s16);

#define ENCOUNTER_TRIGGER 250
#define ENCOUNTER_HITS 8

s32 m4EncounterPickupID=-1;
volatile u32 m4EncounterTrace[16]={0};
volatile u32 m4EncounterHurtTrace[12]={0};
static s32 previous_map=-1;
static u32 previous_frame,pending_at;
static u8 pending,dropped;
static u32 hit_ids[ENCOUNTER_HITS];
static u8 hits;
static struct {u8* pointer;u16 id;} grenades[24];
static void* hurt_source;
static u32 hurt_frame;
static u32 hurt_uid;
static s16 hurt_action;

static int valid(void* p,u32 size) {return (u32)p>=0x80000000 && (u32)p<=0x80800000-size;}
static u32 frame(void) {return *(u32*)0x8076A064;}
static int won(void) {const M5Area* area=m5Area(CurrentMap);return !area || krushaProgressRead(*(u8*)0x807467C8,KRUSHA_GB_BIT+area->world*5,1);}

/* Adventure player damage is a separate native path: its hurt initializers
 * normally request one slice regardless of actor+136. Associate an accepted
 * action with a live, owned grenade before its native node can be deleted.
 * Never dereference that source later or change its identity. */
void m4EncounterActionResult(s16 action,void* source,u8 player,u8 accepted) {
    if (!accepted || player) return;
    hurt_source=0;
    if (!m5Area(CurrentMap) || !krushaEnabled() || !DetectAdventure() || !valid(source,0x180)) return;
    if (*(u32*)((u8*)source+0x58)!=50) return;
    u8* node=*(u8**)0x807FC400;
    for (int n=0;node && n<512;n++,node=*(u8**)(node+0x68)) {
        if (*(void**)(node+0x44)!=source) continue;
        for (int i=0;i<24;i++) if (grenades[i].pointer==node && grenades[i].id==*(u16*)(node+0x5A)) {
            hurt_source=source;hurt_frame=frame();
            hurt_uid=*(u32*)((u8*)source+0x54);hurt_action=action;
            m4EncounterHurtTrace[0]++;m4EncounterHurtTrace[1]=action;
            m4EncounterHurtTrace[2]=(u32)source;
            return;
        }
        return;
    }
}

s32 m4EncounterPlayerDamage(u8 player,s8 amount) {
    if (!player && amount<0) {
        u8* cc=*(u8**)0x807FC924;
        u32 gap=frame()-hurt_frame;
        m4EncounterHurtTrace[3]++;
        if (amount==-1 && hurt_source && gap<=4 && m5Area(CurrentMap) &&
            krushaEnabled() && DetectAdventure() && valid(cc,0x2B4) &&
            *(s16*)(cc+0x29C)==hurt_action && *(u32*)(cc+0x2A4)==hurt_uid &&
            (!*(void**)(cc+0x2A0) || *(void**)(cc+0x2A0)==hurt_source)) {
            amount=-2;m4EncounterHurtTrace[4]++;
        }
        m4EncounterHurtTrace[5]=(s32)amount;m4EncounterHurtTrace[6]=gap;
        m4EncounterHurtTrace[7]=valid(cc,0x2B4) ? *(u32*)(cc+0x2A0) : 0;
        m4EncounterHurtTrace[8]=valid(cc,0x2B4) ? (s32)*(s16*)(cc+0x29C) : 0;
        m4EncounterHurtTrace[9]=valid(cc,0x2B4) ? *(u32*)(cc+0x2A4) : 0;
        m4EncounterHurtTrace[10]=hurt_uid;m4EncounterHurtTrace[11]=hurt_action;
        hurt_source=0;
    }
    return m4NativePlayerDamage(player,amount);
}

int m4EncounterKlump(void* pointer) {
    u8* actor=pointer;
    if (!m5Area(CurrentMap) || !valid(actor,0x180) || *(u32*)(actor+0x58)!=187) return 0;
    /* Klump has an extra module at+178. The common enemy AI at+174 owns
     * the reliable spawner link; do not copy Kasplat's module offsets. */
    u8* ai=*(u8**)(actor+0x174);
    if (!valid(ai,0x38)) return 0;
    u8* spawner=*(u8**)ai;
    return valid(spawner,0x48) && spawner[0]==9 && spawner[19]==ENCOUNTER_TRIGGER &&
        *(void**)(spawner+0x18)==actor;
}

void m4EncounterShout(void) {
    if (!m5Area(CurrentMap) || !krushaEnabled() || !Player || won() || pending || dropped) return;
    const M5Area* area=m5Area(CurrentMap);
    f32 dx=Player->xPos-area->pad[0],dz=Player->zPos-area->pad[2],dy=Player->yPos-area->pad[1];
    if (dx*dx+dz*dz>70*70 || dy < -20 || dy>35) return;
    s32 existing=m4EncounterFindPickup(-1);
    if (existing>=0) {m4EncounterPickupID=existing;dropped=1;return;}

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
    if (!krushaEnabled() || type!=171 || seen || hits>=ENCOUNTER_HITS || *(s16*)(actor+0x134)<=0) {
        /* One native explosion can test several collision shapes. Preserve
         * the accepted hurt/death result on its second contact; clearing it
         * here would leave a zero-health Klump alive after the eighth hit. */
        context[0x200]=hits>=ENCOUNTER_HITS ? 9 : (type==171 && seen ? 4 : 0);
        return;
    }
    hit_ids[hits++]=uid;
    *(s16*)(actor+0x134)=ENCOUNTER_HITS-hits;
    context[0x200]=hits==ENCOUNTER_HITS ? 9 : 4;
    m4EncounterTrace[1]=hits;m4EncounterTrace[2]=ENCOUNTER_HITS-hits;
}

void m4EncounterKlumpUpdate(void) {
    u8* actor=*(u8**)0x807FBB40;
    void (*native)(void)=(void*)0x806AEE84;
    if (!m4EncounterKlump(actor)) {native();return;}
    if (!krushaEnabled() || !DetectAdventure() || won()) {
        /* This is a character-spawner actor, not a free-standing effect.
         * Deleting it here leaves spawner state5/6 pointing at freed memory
         * if its GB is collected before the death animation finishes. The
         * native manager80727958 owns state40 retirement: unlink movement
         * box, finish model cleanup, delete actor and advance spawner state. */
        actor[0x154]=0x40;
        actor[0x155]=0;
        return;
    }
    u8* context=(void*)0x807FBB70;
    /* Shouts use the spawner's native instrument-immunity bit. Other instant
     * kill flags (shockwave/slam) must not bypass the eight-projectile fight. */
    context[0x15]=0;
    if (hits<ENCOUNTER_HITS && context[0x200]==9) context[0x200]=0;
    native();
    m4EncounterTrace[8]=*(u16*)(actor+0x136);
    m4EncounterTrace[9]=*(u16*)(actor+0x134);
}

void m4EncounterThrow(s16 type,s16 model,f32 scale,s16 angle,f32 forward,f32 vertical,void* parent) {
    void (*native)(s16,s16,f32,s16,f32,f32,void*)=(void*)0x8069084C;
    if (!m4EncounterKlump(parent)) {native(type,model,scale,angle,forward,vertical,parent);return;}
    /* Native Klump aims along its body yaw but releases at its right hand.
     * At this scale that lateral offset is conspicuous. Aim the middle round
     * from the actual release point to the player, retaining native speeds. */
    f32 x=*(f32*)0x807FC7B0,y=*(f32*)0x807FC7B4,z=*(f32*)0x807FC7B8;
    s16 (*toward)(f32,f32,f32,f32)=(void*)0x80665DE0;
    void (*origin)(f32,f32,f32)=(void*)0x806907F0;
    if (Player) angle=toward(Player->xPos,Player->zPos,x,z);
    for (int n=-1;n<=1;n++) {
        origin(x,y,z);
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
    if (dropped || won() || hits!=ENCOUNTER_HITS) return 1;
    u8* actor=enemy;
    f32 x=*(f32*)(actor+0x7C),y=*(f32*)(actor+0x80)+30,z=*(f32*)(actor+0x84);
    int (*floor)(f32,f32,f32*)=(void*)0x80667110;
    if (floor(x,z,&y)) y+=4;
    int (*spawn)(s16,f32,f32,f32,f32,u8)=(void*)0x80632630;
    void (*collect)(s16,s16,s16,u8,u8,u8)=(void*)0x806F50C8;
    m4EncounterPickupID=spawn(9,x,y,z,0,0);
    if (m4EncounterPickupID>=0) {
        collect(m4EncounterPickupID,9,0,1,0,0);
        playSong(20,1.0f); /* Native short GB-appearance cue, once per drop. */
        dropped=1;m4EncounterTrace[4]++;m4EncounterTrace[5]=m4EncounterPickupID;
    }
    return 1;
}

void m4EncounterGrenadeUpdate(void) {
    u8* actor=*(u8**)0x807FBB40;
    void (*native)(void)=(void*)0x80693EC0;
    if (m5Area(CurrentMap) && krushaEnabled() && DetectAdventure()) {
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
        hurt_source=0;
        for (int i=0;i<24;i++) grenades[i].pointer=0;
    }
    previous_map=CurrentMap;previous_frame=frame();
    if (hurt_source && frame()-hurt_frame>4) hurt_source=0;
    if (!m5Area(CurrentMap) || !krushaEnabled() || !DetectAdventure()) return;
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
        /* Apply the requested additional8% exactly. The packed spawner size
         * is integral; rounding80 to74 would be only7.5%. Native collision
         * and shadow helpers use these same animation scales. */
        u8* animation=*(u8**)(actor+4);
        for (int axis=0;axis<3;axis++) *(f32*)(animation+0x34+axis*4)*=0.92f;
        *(u16*)(record+0x46)|=0x44; /* native: force loaded, instrument immune */
        *(s16*)(actor+0x134)=ENCOUNTER_HITS;
        *(s16*)(actor+0x136)=2 * *(s16*)(0x8074D0C4+187*4+2);
        pending=0;hits=0;m4EncounterTrace[0]++;m4EncounterTrace[2]=ENCOUNTER_HITS;
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
