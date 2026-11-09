#ifndef M5_CAMPAIGN_H
#define M5_CAMPAIGN_H
#include "common.h"
typedef struct {u16 map,gate_id,pad_id,reward_id;u8 world,trigger;f32 pad[3],boss[3],cage[3];} M5Area;
typedef struct {u16 map;u8 world,spawner_id;} M5Kasplat;
const M5Area* m5Area(s32 map);
const M5Kasplat* m5Kasplat(s32 map);
s32 m5FileAlias(s32 table,s32 map);
#endif
