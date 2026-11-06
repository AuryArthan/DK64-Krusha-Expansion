#include "../include/common.h"
#include "../include/krusha_progress.h"

extern int saveNativePackedRead(int type, u8 character, u8 level, u8 file);
extern void saveNativePackedWrite(int type, u8 character, u8 level, u8 file, u32 value);
extern void saveNativeLoadGame(u8 file, int refill);

static const char format_signature[] = "K07.1";

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
    *(const char**)0x807467C0 = format_signature;
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

/* Provisional logical registry: twenty potential bunches per main world,
 * followed by 128 potential coins, then 116 unassigned slots. These describe
 * no XYZ positions and spawn nothing. Later annotations supply the actual
 * registry/weights, within 384 separate colored pickups across the campaign.
 * Totals derive from collected flags, avoiding redundant saved CB counters. */
int krushaProgressBananas(unsigned int file, unsigned int level) {
    int i, result = 0;
    if (level >= 7) return 0;
    for (i = 0; i < 20; i++) result += 5 * krushaProgressRead(file, level * 20 + i, 1);
    return result;
}

int krushaProgressGoldenBananas(unsigned int file, unsigned int level) {
    int i, result = 0;
    if (level >= 8) return 0;
    for (i = 0; i < 5; i++) result += krushaProgressRead(file, KRUSHA_GB_BIT + level * 5 + i, 1);
    return result;
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
        default: return 0;
    }
}

static void storeLiveProgress(u8 file) {
    int level, fed;
    krushaProgressWrite(file, KRUSHA_WALLET_BIT, 8, MovesBase[5].coins > 255 ? 255 : MovesBase[5].coins);
    for (level = 0; level < 7; level++) {
        fed = MovesBase[5].tns_cb_count[level];
        if (fed < 0) fed = 0;
        if (fed > 100) fed = 100;
        krushaProgressWrite(file, KRUSHA_FED_BIT + level * 7, 7, fed);
    }
    /* Gun/shout/story bits are independent saved ownership. The baseline's
     * automatic weapon grant / cleared instrument bits must not overwrite them. */
}

void krushaSavePackedWrite(int type, u8 character, u8 level, u8 file, u32 value) {
    if (character == 5 && type >= 1 && type <= 11) {
        if (type == 9) krushaProgressWrite(file, KRUSHA_WALLET_BIT, 8, value > 255 ? 255 : value);
        else if (type == 2 && level < 7) krushaProgressWrite(file, KRUSHA_FED_BIT + level * 7, 7, value > 100 ? 100 : value);
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
    void (*nativeZero)(void*, int) = (void*)0x800051C0;
    saveNativeLoadGame(file, refill);
    /* Clear all 94 bytes, including unused level entries and stale stock. */
    nativeZero(&MovesBase[5], sizeof(KongBase));
    MovesBase[5].coins = krushaSavePackedRead(9, 5, 0, file);
    MovesBase[5].simian_slam = MovesBase[0].simian_slam;
    MovesBase[5].ammo_belt = MovesBase[0].ammo_belt;
    for (level = 0; level < 8; level++) {
        MovesBase[5].cb_count[level] = krushaSavePackedRead(1, 5, level, file);
        MovesBase[5].tns_cb_count[level] = krushaSavePackedRead(2, 5, level, file);
        MovesBase[5].gb_count[level] = krushaProgressGoldenBananas(file, level);
        if (level < 7) *(s16*)(0x807FC930 + level * 2) += MovesBase[5].tns_cb_count[level];
    }
}
