#include "../include/common.h"
#include "../include/krusha_recruitment.h"
#include "../include/krusha_progress.h"
#include "../include/recruitment_keys.generated.h"

static int keyType(int type) {
    for (int i=0;i<RECRUITMENT_KEY_COUNT;i++)
        if (recruitmentKeys[i].type==type) return i;
    return -1;
}
static u32 key_sound_frame;
static u8 key_sound_pending;
void krushaRecruitmentMusicLoad(u32 source,void* dest,u32* size,u32 mode,u32 a,u32 b,void* scratch) {
    if (CurrentMap!=34 || ObjectModel2Timer-key_sound_frame>=60) key_sound_pending=0;
    if (key_sound_pending) {
        for (int i=0;i<4;i++) if (((void**)0x8076BF38)[i]==dest && ((u8*)0x80770560)[i]==145) {
            extern void* krushaBarrelFile(s32,s32,u8,u8);
            key_sound_pending=0;
            void* data=krushaBarrelFile(27,RECRUITMENT_KEY_SOUND_ASSET,1,0);
            if (data && RECRUITMENT_KEY_SOUND_BYTES<=((u32*)0x807452B0)[i]) {
                dk_memcpy(dest,data,RECRUITMENT_KEY_SOUND_BYTES);
                ((void(*)(void*,s32,s32))0x8066B434)(data,0,0);
                *size=RECRUITMENT_KEY_SOUND_BYTES;
                return;
            }
            if (data) ((void(*)(void*,s32,s32))0x8066B434)(data,0,0);
        }
    }
    ((void(*)(u32,void*,u32*,u32,u32,u32,void*))0x8060B140)(source,dest,size,mode,a,b,scratch);
}
int krushaRecruitmentKeyModel(int type,int mirror) {
    int i=keyType(type);
    return i<0 ? -1 : mirror ? recruitmentKeys[i].mirror : recruitmentKeys[i].model;
}
/* Reuse the existing model2 presentation traversal; native subtype74 supplies
 * the same spin as GBs. Pickup identity and saved ownership remain private.
 * No new actor, sprite, per-frame allocation, or setup reconstruction. */
int krushaRecruitmentKeyPresent(void* prop) {
    u8* object=prop;
    int i=keyType(*(s16*)(object+0x84));
    if (i<0 || CurrentMap!=recruitmentKeys[i].map ||
        *(s16*)(object+0x8A)!=recruitmentKeys[i].object_id) return 0;
    if (*(s16*)(object+0x86)!=1) return 1;
    u8* model=*(u8**)(object+0x20);
    if (model) *(s16*)(model+0xB4)=krushaRecruitmentKeyVisible(
        krushaProgressActiveFile(),recruitmentKeys[i].owner) ? 0x74 : 0;
    return 1;
}

static int keyIndex(int map,int object_id) {
    for (int i=0;i<sizeof(recruitmentKeys)/sizeof(recruitmentKeys[0]);i++)
        if (recruitmentKeys[i].map==map && recruitmentKeys[i].object_id==object_id) return i;
    return -1;
}
int krushaRecruitmentKeyHidden(int map,int object_id) {
    int i=keyIndex(map,object_id);
    return i<0 ? -1 : !krushaRecruitmentKeyVisible(krushaProgressActiveFile(),recruitmentKeys[i].owner);
}
/* The native range/action/suction path owns physical contact and despawn.
 * Runtime IDs are resolved before matching our exact map+setup ID. This path
 * cannot call native boss-key flags, inventory awards, or victory actions. */
int krushaRecruitmentKeyContact(short runtime_id,unsigned char player,unsigned short type) {
    if (keyType(type)<0) return -1;
    short (*setupId)(short)=(void*)0x8063D990;
    int i=keyIndex(CurrentMap,setupId(runtime_id));
    unsigned int file=krushaProgressActiveFile();
    if (i<0 || recruitmentKeys[i].type!=type || !krushaRecruitmentKeyCollectible(file,recruitmentKeys[i].owner,Character,player)) return 0;
    if (!krushaRecruitmentCollectKey(file,recruitmentKeys[i].owner)) return 0;
    /* Native rainbow-coin one-shot, with a private transposed sequence.
     * Stop only this short jingle so consecutive key pickups retrigger it.
     * Its ordinary ROM sequence and other pickups remain unchanged. */
    ((void(*)(s32,u8))0x80602B60)(145,1);
    key_sound_frame=ObjectModel2Timer;key_sound_pending=1;
    playSong(145,1.0f);
    return 1;
}
/* Native3D props already have five ownership bits, including DK bit8.
 * Assign only our manifest identity at the existing constructor callsite.
 * The generic contact path respects these bits. The material adapter below
 * also enforces visible100-alpha ghosting; the native fog-alpha shortcut
 * alone was insufficient on the tested renderer. No identity spoofing. */
void krushaRecruitmentKeyOwner(short map,short object_id,unsigned char* flags) {
    void (*nativeOwner)(short,short,unsigned char*)=(void*)0x80632E74;
    nativeOwner(map,object_id,flags);
    int i=keyIndex(map,object_id);
    static const u8 owner_bits[5]={8,2,0x10,4,1};
    if (i>=0) *flags|=owner_bits[recruitmentKeys[i].owner];
}
int krushaRecruitmentKeyEffect(short type) {
    /* The cue/save already occurred at the once-only physical acceptance.
     * Explicitly bypass the native key's action0x41 boss-reward controller. */
    return keyType(type)>=0;
}

/* Only the world model2 renderer's material call is redirected. Every other
 * prop takes the original function unchanged. Keys use primitive alpha rather
 * than fog alpha; this is visible even on renderers that optimize disabled fog.
 * Geometry remains immutable and native buffers own these three draw commands. */
Gfx* krushaRecruitmentKeyAlpha(Gfx* dl,s16 alpha,u8 extra,void* model_ptr) {
    Gfx* (*native)(Gfx*,s16,u8)=(void*)0x8065D008;
    u8* model=model_ptr;
    if (CurrentMap!=34 || !model || *(s16*)(model+0xB6)<0)
        return native(dl,alpha,extra);
    s16 (*indexOf)(s16)=(void*)0x80659470;
    int index=indexOf(*(s16*)(model+0xB6));
    ModelTwoData* props=ObjectModel2Pointer;
    if (index<0 || index>=ObjectModel2Count_Dupe ||
        *(void**)((u8*)&props[index]+0x20)!=model_ptr)
        return native(dl,alpha,extra);
    int i=keyIndex(CurrentMap,props[index].object_id);
    if (i<0 || props[index].object_type!=recruitmentKeys[i].type)
        return native(dl,alpha,extra);
    void (*distanceAlpha)(float,float,float,float,s16,s16*)=(void*)0x8065CE4C;
    s16 distance=255;
    distanceAlpha(*(f32*)model,*(f32*)(model+4),*(f32*)(model+8),
                  (f32)*(s16*)(model+0xC0),props[index].object_type,&distance);
    u8* changes=*(u8**)0x807FC924;
    u8 viewport=*(u8*)0x807FC929;
    u8* actor=changes && viewport<4 ? *(u8**)(changes+viewport*0x2F0+4) : 0;
    int own=actor && *(u32*)(actor+0x58)==recruitmentKeys[i].owner+2;
    alpha=own ? 255 : 100;
    if (alpha>distance) alpha=distance;
    if (alpha<0 || !krushaRecruitmentKeyVisible(krushaProgressActiveFile(),recruitmentKeys[i].owner)) alpha=0;
    dl=native(dl,alpha,extra);
    gDPPipeSync(dl++);
    gDPSetPrimColor(dl++,0,255,255,255,255,alpha);
    dl->words.w0=0xE200001C;
    /* Keep the native fade depth/coverage flags: these props are submitted
     * before some opaque geometry. Dropping Z_UPD lets later terrain punch
     * through the key. Both blender cycles use incoming primitive alpha. */
    dl->words.w1=alpha==255 ? 0x0C192230 : 0x00504270;
    return dl+1;
}
