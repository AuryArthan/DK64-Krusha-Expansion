#include "../include/common.h"
#include "../include/krusha_recruitment.h"
#include "../include/krusha_progress.h"
#include "../include/recruitment_keys.generated.h"

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
    if (type!=RECRUITMENT_KEY_TYPE) return -1;
    short (*setupId)(short)=(void*)0x8063D990;
    int i=keyIndex(CurrentMap,setupId(runtime_id));
    unsigned int file=krushaProgressActiveFile();
    if (i<0 || !krushaRecruitmentKeyCollectible(file,recruitmentKeys[i].owner,Character,player)) return 0;
    if (!krushaRecruitmentCollectKey(file,recruitmentKeys[i].owner)) return 0;
    /* Brief native pickup chime, no GB/key music or player action. */
    playSound(0x263,0x7FFF,63.0f,1.0f,0,0);
    return 1;
}
/* Native3D props already have five ownership bits, including DK bit8.
 * Assign only our manifest identity at the existing constructor callsite.
 * Its renderer then performs the same100-alpha wrong-owner fade as vanilla,
 * and the generic native contact path also respects the ownership bit.
 * No global ID spoofing, per-frame setup scan or custom translucent pass. */
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
    return type==RECRUITMENT_KEY_TYPE;
}
