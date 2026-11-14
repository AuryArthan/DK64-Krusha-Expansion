#ifndef KRUSHA_PROGRESS_H
#define KRUSHA_PROGRESS_H

/* Recruitment format, retaining the M1 physical allocation and item IDs.
 * Original per-level pickup indexes and the first 800 permanent bits stay native.
 * Native record sizes/CRC/recovery derive from the enlarged layout count. */
#define KRUSHA_SAVE_BITS 512
#define KRUSHA_SAVE_SIGNATURE "K14.0"
#define KRUSHA_PICKUP_SLOTS 384
#define KRUSHA_BANANA_OBJECTS 231
#define KRUSHA_COIN_FIRST 231
#define KRUSHA_COIN_OBJECTS 99
#define KRUSHA_FED_BIT 384
#define KRUSHA_GB_BIT 433
#define KRUSHA_BLUEPRINT_BIT 473
#define KRUSHA_MEDAL_BIT 481
#define KRUSHA_WALLET_BIT 488
#define KRUSHA_KEYS_BIT 496
#define KRUSHA_LOCKS_BIT 501
#define KRUSHA_RECRUITED_BIT 506
#define KRUSHA_GUN_BIT 507
#define KRUSHA_SHOUT_BIT 508
#define KRUSHA_INTRO_BIT 509

unsigned int krushaProgressActiveFile(void);
void krushaProgressQuestWrite(unsigned int file, unsigned int value);
void krushaProgressRequestSave(void);

int krushaProgressRead(unsigned int file, unsigned int bit, unsigned int width);
void krushaProgressWrite(unsigned int file, unsigned int bit, unsigned int width, unsigned int value);
int krushaProgressBananas(unsigned int file, unsigned int level);
int krushaProgressGoldenBananas(unsigned int file, unsigned int level);
int krushaProgressFullSet(void);

#endif
