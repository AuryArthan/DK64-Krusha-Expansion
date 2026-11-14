#include "../include/common.h"
#include "../include/krusha_progress.h"
#include "../include/m3_progress.h"

extern int saveNativePackedRead(int type, u8 character, u8 level, u8 file);
extern void saveNativePackedWrite(int type, u8 character, u8 level, u8 file, u32 value);
extern void saveNativeLoadGame(u8 file, int refill);
extern void saveNativeCollectTotals(void);

const char krushaSaveFormatSignature[] = KRUSHA_SAVE_SIGNATURE;

/* The native writer compares its desired snapshot to a RAM shadow of EEPROM.
 * Mupen states restore that shadow without restoring battery storage. Refresh
 * only the writer's LOCAL comparison snapshot if the device has moved on.
 * Never replace live progress, packed working RAM, or the native shadow here.
 * Footer reads are cheap in the normal case; a mismatch causes one full read.
 * Keep the native SI arbitration, 15 ms pacing, CRCs and incremental writes.
 */
u32 krushaSaveSyncTrace[4] = {0x4B535931, 0, 0, 0}; /* calls, rebases, read errors */
static u8 save_device_snapshot[2048] = {1};

void* krushaSaveCompareSnapshot(void* dest, void* src, int size) {
    void (*delay)(float) = (void*)0x8060B84C;
    volatile u8* controller_busy = (void*)0x807ECD08;
    volatile u8* eeprom_busy = (void*)0x807467C4;
    OSMesgQueue* queue = (void*)0x807ECCF0;
    u8 footer[8];
    int i, byte, offset, mismatch = 0, error = 0;
    int bytes = (((*(volatile u16*)0x807ECEA0 + 0x6B7) & ~63) + 0x27) & ~7;
    bytes >>= 3;
    dk_memcpy(dest, src, size);
    /* This hook has a single guarded USA callsite in the native IO thread. */
    if (src != (void*)0x807ED6A8 || size != 2048 ||
        *(volatile int*)0x807EDEAC != 2 || bytes != 492 ||
        *(volatile u8*)0x80744460) return dest;
    krushaSaveSyncTrace[1]++;
    while (*controller_busy) delay(1.0f);
    *eeprom_busy = 1;
    for (i = 0; i < 5 && !error; i++) {
        offset = (i < 4 ? (i + 1) * bytes - 4 : bytes * 4 + 60) & ~7;
        error = osEepromRead(queue, offset >> 3, footer);
        delay(15.0f);
        if (error) break;
        for (byte = 0; byte < 8; byte++)
            if (footer[byte] != ((u8*)dest)[offset + byte]) mismatch = 1;
        if (*(volatile u8*)0x80744460) error = -1;
    }
    if (mismatch && !error) {
        for (i = 0; i < 256 && !error; i++) {
            error = osEepromRead(queue, i, &save_device_snapshot[i * 8]);
            delay(15.0f);
            if (*(volatile u8*)0x80744460) error = -1;
        }
        if (!error) {
            dk_memcpy(dest, save_device_snapshot, 2048);
            krushaSaveSyncTrace[2]++;
        }
    }
    if (error) krushaSaveSyncTrace[3]++;
    *eeprom_busy = 0;
    return dest;
}

static u16 recordBits(void) {
    u32 count = *(volatile u16*)0x807ECEA0;
    return (((count + 0x6B7) & ~63) + 0x27) & ~7;
}

/* Installed in compressed native code before EEPROM startup, not per-frame. */
void krushaSaveLayoutInit(void) {
    volatile s16* counts = (volatile s16*)0x807F6150;
    int total = KRUSHA_SAVE_BITS;
    int i;
    for (i = 0; i < 8; i++) total += counts[i];
    *(volatile s16*)0x807ECEA0 = total;
    *(const char**)0x807467C0 = krushaSaveFormatSignature;
}

static u16 extensionBit(u8 file, u16 local) {
    int (*slotForFile)(int) = (void*)0x8060B9D0;
    return slotForFile(file) * recordBits() + 800 +
        *(volatile u16*)0x807ECEA0 - KRUSHA_SAVE_BITS + local;
}

int krushaProgressRead(unsigned int file, unsigned int bit, unsigned int width) {
    int (*readBits)(u16, u8) = (void*)0x8060BBE0;
    if (file >= 4 || !width || width > 8 || bit + width > KRUSHA_SAVE_BITS) return 0;
    return readBits(extensionBit(file, bit), width);
}

void krushaProgressWrite(unsigned int file, unsigned int bit, unsigned int width, unsigned int value) {
    void (*writeBits)(u32, u16, u8) = (void*)0x8060BB18;
    if (file >= 4 || !width || width > 8 || bit + width > KRUSHA_SAVE_BITS) return;
    writeBits(value, extensionBit(file, bit), width);
}

unsigned int krushaProgressActiveFile(void) { return *(volatile u8*)0x807467C8; }

/* Keys496..500, locks501..505 and recruited506 occupy bits20..30 of
 * ONE native packed word in every492-byte record. The native bit writer
 * performs one aligned store: the IO thread cannot snapshot half a final
 * lock/recruit update. Ownership507/508 and intro509 remain untouched. */
void krushaProgressQuestWrite(unsigned int file, unsigned int value) {
    void (*writeBits)(u32,u16,u8) = (void*)0x8060BB18;
    u16 bit;
    if (file>=3 || recordBits()!=3936) return;
    bit=extensionBit(file,KRUSHA_KEYS_BIT);
    if ((bit&31)!=20) return;
    writeBits(value&0x7FF,bit,11);
}

void krushaProgressRequestSave(void) { ((void (*)(void))0x8060DEC8)(); }

/* Preserve K07.2 identities and weights. Each world now counts only the
 * first3 bunches, first2 balloons and first15 singles (50 CB). Retired flags
 * remain stored, never reassigned; existing100-CB saves naturally read50. */
typedef struct BananaBudget {
    u16 first;
    u8 bunches;
    u8 balloons;
    u8 singles;
} BananaBudget;

static const BananaBudget banana_budget[7] = {
    {0, 10, 3, 20}, {33, 9, 3, 25}, {70, 10, 3, 20},
    {103, 10, 3, 20}, {136, 10, 2, 30}, {178, 10, 3, 20},
    {211, 11, 4, 5},
};

int krushaProgressBananas(unsigned int file, unsigned int level) {
    int i, weight, result = 0;
    const BananaBudget* budget;
    if (level >= 7) return 0;
    budget = &banana_budget[level];
    for (i = 0; i < budget->bunches + budget->balloons + budget->singles; i++) {
        if (i < budget->bunches && i >= 3) continue;
        if (i >= budget->bunches && i < budget->bunches+budget->balloons && i-budget->bunches >= 2) continue;
        if (i >= budget->bunches+budget->balloons && i-budget->bunches-budget->balloons >= 15) continue;
        weight = i < budget->bunches ? 5 : i < budget->bunches + budget->balloons ? 10 : 1;
        result += weight * krushaProgressRead(file, budget->first + i, 1);
    }
    /* Castle originally reserved only five singles. Ten genuinely unused
     * slots finish its50-CB set; retired flags are never reinterpreted. */
    if (level==6) for (i=330;i<340;i++) result+=krushaProgressRead(file,i,1);
    return result;
}

/* Called only from the native rainbow-coin award branch, after its original
 * five wallets were credited. OFF/recruitment deliberately do not gate credit.
 * Keep native collection/once-only flags, FTT, sounds and original five intact. */
void krushaRainbowCredit(void) {
    void (*nativeFirstTime)(void) = (void*)0x806F5498;
    if (DetectAdventure()) {
        int coins = MovesBase[5].coins + 5;
        MovesBase[5].coins = coins > 255 ? 255 : coins;
    }
    nativeFirstTime();
}

int krushaProgressGoldenBananas(unsigned int file, unsigned int level) {
    int i, result = 0;
    if (level >= 8) return 0;
    for (i = 0; i < 5; i++) if (i==0 || i==1 || i==4)
        result += krushaProgressRead(file, KRUSHA_GB_BIT + level * 5 + i, 1);
    return result;
}

/* All aggregate readers see earned sixth progress even when it is hidden. */
void krushaCollectTotals(void) {
    volatile s16* totals = (volatile s16*)0x807FC828;
    unsigned int file = *(volatile u8*)0x807467C8;
    int level;
    saveNativeCollectTotals();
    for (level = 0; level < 8; level++) {
        totals[0] += MovesBase[5].gb_count[level];
        totals[7] += krushaProgressRead(file, KRUSHA_GB_BIT + level * 5 + 4, 1);
    }
}

int krushaProgressFullSet(void) {
    volatile s16* totals = (volatile s16*)0x807FC828;
    /* Native counters cover owned GBs; medal/fairy/crown/key/company-coin and
     * returned-blueprint aggregates come from permanent flags. No coin-wallet
     * or all-CB requirement. The Rareware GB's own permanent flag is required. */
    return totals[0] == 225 && totals[1] == 10 && totals[2] == 8 &&
           totals[3] == 40 && totals[4] == 1 && totals[5] == 20 &&
           totals[6] == 1 && totals[7] == 48 && checkFlag(0x12D, 0);
}

int krushaSavePackedRead(int type, u8 character, u8 level, u8 file) {
    int fed, total;
    if (character != 5 || type < 1 || type > 11) return saveNativePackedRead(type, character, level, file);
    switch (type) {
        case 1:
        case 2:
            if (level >= 7) return 0;
            fed = krushaProgressRead(file, KRUSHA_FED_BIT + level * 7, 7);
            total = krushaProgressBananas(file, level);
            if (fed > total) fed = total;
            return type == 1 ? total - fed : fed;
        case 3: return krushaProgressGoldenBananas(file, level);
        case 5: /* Shared upgrade levels come from the existing team. */
        case 7: return saveNativePackedRead(type, 0, level, file);
        case 9: return krushaProgressRead(file, KRUSHA_WALLET_BIT, 8);
        case 6: case 8: return m3SavedMoves(file,type);
        default: return 0;
    }
}

static void storeLiveProgress(u8 file) {
    int level, fed;
    krushaProgressWrite(file, KRUSHA_WALLET_BIT, 8, MovesBase[5].coins > 255 ? 255 : MovesBase[5].coins);
    for (level = 0; level < 7; level++) {
        fed = MovesBase[5].tns_cb_count[level];
        if (fed < 0) fed = 0;
        if (fed > 50) fed = 50;
        krushaProgressWrite(file, KRUSHA_FED_BIT + level * 7, 7, fed);
    }
    /* Gun/shout/story bits are independent saved ownership. The baseline's
     * automatic weapon grant / cleared instrument bits must not overwrite them. */
}

void krushaSavePackedWrite(int type, u8 character, u8 level, u8 file, u32 value) {
    if (character == 5 && type >= 1 && type <= 11) {
        if (type == 9) krushaProgressWrite(file, KRUSHA_WALLET_BIT, 8, value > 255 ? 255 : value);
        else if (type == 2 && level < 7) krushaProgressWrite(file, KRUSHA_FED_BIT + level * 7, 7, value > 50 ? 50 : value);
        return;
    }
    /* The native save routine writes its sequence field after its gameplay
     * gates, before it queues the EEPROM writer. Add the sixth live record
     * synchronously here; keep the original five-character loops intact. */
    if (type == 16) storeLiveProgress(file);
    saveNativePackedWrite(type, character, level, file, value);
}

void krushaSaveLoadGame(u8 file, int refill) {
    int level;
    int old_file=*(u8*)0x807467C8;
    int energy=MovesBase[5].instrument_energy;
    void (*nativeZero)(void*, int) = (void*)0x800051C0;
    saveNativeLoadGame(file, refill);
    /* Clear all 94 bytes, including unused level entries and stale stock. */
    nativeZero(&MovesBase[5], sizeof(KongBase));
    MovesBase[5].coins = krushaSavePackedRead(9, 5, 0, file);
    MovesBase[5].simian_slam = MovesBase[0].simian_slam;
    MovesBase[5].ammo_belt = MovesBase[0].ammo_belt;
    m3RestoreMoves(file,refill);
    if (!refill && old_file==file && (MovesBase[5].instrument_bitfield&1)) {
        int bits=MovesBase[5].instrument_bitfield,capacity=5;
        while (bits) { capacity+=5;bits>>=1; }
        MovesBase[5].instrument_energy=energy<0 ? 0 : energy>capacity ? capacity : energy;
    }
    for (level = 0; level < 8; level++) {
        MovesBase[5].cb_count[level] = krushaSavePackedRead(1, 5, level, file);
        MovesBase[5].tns_cb_count[level] = krushaSavePackedRead(2, 5, level, file);
        MovesBase[5].gb_count[level] = krushaProgressGoldenBananas(file, level);
        if (level < 7) *(s16*)(0x807FC930 + level * 2) += MovesBase[5].tns_cb_count[level];
    }
}

/* Only Cranky's native medal-status/Jetpac count callsite uses this adapter.
 * Aggregate collection already adds these bits itself; do not hook the general
 * countSetFlags function or those totals would be credited twice. */
int krushaShopMedals(int base, int width, int type) {
    int (*native)(int,int,int) = (void*)0x80731AA8;
    int count = native(base,width,type);
    return count;
}

extern int saveNativeTotalGBs(void);
extern void saveNativeHUDGBs(u8 player);
int krushaTotalGBs(void) {
    int total = saveNativeTotalGBs();
    if (DetectAdventure())
        for (int level = 0; level < 8; level++) total += MovesBase[5].gb_count[level];
    return total;
}
void krushaHUDGBs(u8 player) {
    saveNativeHUDGBs(player);
    if (player == 0 && DetectAdventure() && HUD) {
        for (int level = 0; level < 8; level++) HUD[9].hud_count += MovesBase[5].gb_count[level];
    }
}
