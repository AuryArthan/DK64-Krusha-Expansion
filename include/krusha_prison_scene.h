#ifndef KRUSHA_PRISON_SCENE_H
#define KRUSHA_PRISON_SCENE_H
void krushaPrisonSceneInstall(void);
void krushaPrisonSceneBegin(unsigned int file);
void krushaPrisonSceneReset(void);
int krushaPrisonSceneTick(void);
void krushaPrisonSceneInput(unsigned int pressed);
int krushaPrisonDisplayOwned(void* actor);
#endif
