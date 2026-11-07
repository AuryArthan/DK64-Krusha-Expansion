#ifndef M3_PROGRESS_H
#define M3_PROGRESS_H
void m3ProgressTick(void);
void m3RestoreMoves(unsigned int file, int refill);
int m3SavedMoves(unsigned int file, int type);
void m3FindPurchase(void* menu, void* progress, int first);
void m3ShopInstrument(void);
const char* m3ShopDialogue(const unsigned char* text,unsigned short length);
const void* m3FaceIcon(void);
const void* m3ShoutIcon(void);
#endif
