#ifndef KRUSHA_PRISON_SCENE_H
#define KRUSHA_PRISON_SCENE_H
void krushaPrisonSceneInstall(void);
void krushaPrisonScenePrepare(unsigned int file);
void krushaPrisonSceneBegin(unsigned int file);
void krushaPrisonSceneReset(void);
void krushaPrisonTinyAnimation(void* actor,int script);
int krushaPrisonSceneTick(void);
void krushaPrisonSceneInput(unsigned int held);
int krushaPrisonDisplayOwned(void* actor);
void krushaPrisonKeyBones(void* actor);
#endif
