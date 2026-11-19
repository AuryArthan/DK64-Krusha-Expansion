; Displaced prologues from the unmodified USA 1.0 executable. These
; trampolines preserve the original arguments and original return address.
widescreenNativeOrtho:
    ADDIU sp, sp, -0x68
    MTC1 a1, f12
    J 0x80006DEC
    NOP

widescreenNativePerspective:
    ADDIU sp, sp, -0x68
    MTC1 a2, f12
    J 0x80006058
    NOP

widescreenNativeHUDCounter:
    ADDIU sp, sp, -0x78
    SW ra, 0x24(sp)
    J 0x806F9D94
    NOP

widescreenNativeHUDGroup:
    ADDIU sp, sp, -0x90
    SW a0, 0x90(sp)
    J 0x806FA1AC
    NOP

krushaNativeGBHUDInit:
    ADDIU sp, sp, -0x78
    LUI t6, 0x8075
    J 0x806F9B6C
    NOP

widescreenNativeHUDIcon:
    ADDIU sp, sp, -0xB0
    SW ra, 0x1C(sp)
    J 0x8071BE0C
    NOP

widescreenNativeHealth:
    ADDIU sp, sp, -0x100
    SW ra, 0x8C(sp)
    J 0x807085D8
    NOP

widescreenNativePauseSprite:
    ADDIU sp, sp, -0x48
    SW ra, 0x1C(sp)
    J 0x806AB4F4
    NOP

widescreenNativePauseCounter:
    ADDIU sp, sp, -0x58
    LW t6, 0x74(sp)
    J 0x806AB810
    NOP

widescreenNativePauseFraction:
    ADDIU sp, sp, -0xF0
    SW ra, 0x3C(sp)
    J 0x806AA0A4
    NOP

widescreenNativeCounter:
    ADDIU sp, sp, -0x78
    SW s0, 0x1C(sp)
    J 0x8068DC5C
    NOP

widescreenNativeText:
    ADDIU sp, sp, -0x80
    SW fp, 0x38(sp)
    J 0x806FD498
    NOP

widescreenNativeLogo:
    ADDIU sp, sp, -0xE8
    SW s0, 0x20(sp)
    J 0x80032934
    NOP

widescreenNativeQueue:
    LUI a3, 0x8075
    ADDIU a3, a3, 0x01E0
    J 0x8068C358
    NOP

widescreenNativeSpriteRect:
    LUI t2, 0x8075
    LW t2, 0x50D0(t2)
    J 0x8070F304
    NOP

widescreenNativeCameraMask:
    ADDIU sp, sp, -0x40
    MOVE v0, a0
    J 0x806FF14C
    NOP

widescreenNativeSniperMask:
    ADDIU sp, sp, -0x78
    LUI t8, 0x8080
    J 0x806FF764
    NOP

widescreenNativeShutterMask:
    ADDIU sp, sp, -0x40
    SW ra, 0x34(sp)
    J 0x806FFB34
    NOP

vanillaBuildActorBones:
    ADDIU sp, sp, -0x18
    SW ra, 0x14(sp)
    J 0x80614A6C
    NOP

vanillaCharacterScript:
    LW v0, 4(a0)
    MTC1 r0, f4
    J 0x80614EC4
    NOP

m4NativeCollectEffect:
    .word 0x00047400
    .word 0x000E7C03
    J 0x806F79E8
    NOP

m4NativeDamage:
    LH t6, 0x134(a0)
    LH t7, 0x136(a1)
    J 0x80675DD8
    NOP

m4NativePlayerDamage:
    ANDI t6, a0, 0xFF
    SLL t8, t6, 2
    J 0x806C997C
    NOP

vanillaSetAction:
    ANDI t8, a2, 0xFF
    LUI a3, 0x8080
    J 0x806EB0C8
    NOP

vanillaScriptCondition:
    ADDIU sp, sp, -0x78
    SW ra, 0x24(sp)
    J 0x8063EA1C
    NOP

vanillaModelPickupAllowed:
    ADDIU sp, sp, -0x18
    ANDI t6, a2, 0xFFFF
    J 0x806F664C
    NOP

vanillaFindPurchase:
    ADDIU sp, sp, -0x30
    SW s3, 0x20(sp)
    J 0x80025FBC
    NOP

m3NativeShopPurchase:
    ADDIU sp, sp, -0x20
    SW a0, 0x20(sp)
    J 0x80025E0C
    NOP

m3NativeShopControl:
    ADDIU sp, sp, -0x20
    MOVE a3, a0
    J 0x80027030
    NOP

.definelabel m3NativePurchaseText, 0x8070E750
.definelabel m3NativeShopAnimation, 0x80614E78

m3NativeKasplatInit:
    LUI v0, 0x8080
    LW v0, 0xBB40(v0)
    J 0x806B1DDC
    NOP

m3NativeEnemyDrop:
    ADDIU sp, sp, -0x40
    LUI t6, 0x8080
    J 0x806A5C68
    NOP

m3NativeBlueprint:
    ADDIU sp, sp, -0x18
    SW ra, 0x14(sp)
    J 0x806A6114
    NOP

vanillaAmmoCollectible:
    SW a2, 0x8(sp)
    ANDI t6, a2, 0xFF
    J 0x806F5454
    NOP

vanillaBananaBalloon:
    LUI a1, 0x8080
    LW a1, 0xBB40(a1)
    J 0x806A7608
    NOP

vanillaCrystalAbility:
    SLL t6, a0, 16
    SRA t7, t6, 16
    J 0x806F6E60
    NOP

vanillaBarrelEligibility:
    LUI t6, 0x8080
    LW t6, 0xC924(t6)
    J 0x8068077C
    NOP

vanillaBarrelFile:
    ADDIU sp, sp, -0x58
    SW ra, 0x2C(sp)
    J 0x8066B100
    NOP

vanillaBarrelSpawn:
    ADDIU sp, sp, -0x40
    SW s7, 0x34(sp)
    J 0x80682E40
    NOP

vanillaBarrelLayout:
    ADDIU sp, sp, -0x78
    LUI v0, 0x8080
    J 0x80682ABC
    NOP

vanillaBarrelControl:
    ADDIU sp, sp, -0x50
    SW ra, 0x24(sp)
    J 0x806836D8
    NOP

vanillaBarrelName:
    ADDIU sp, sp, -0x18
    SLL v1, a1, 2
    J 0x80683A88
    NOP

vanillaBarrelAnimation:
    ADDIU sp, sp, -0x18
    SW ra, 0x14(sp)
    J 0x80682DFC
    NOP

vanillaOptionsInput:
    ADDIU sp, sp, -0x30
    SW ra, 0x24(sp)
    J 0x8002D8B4
    NOP

vanillaInstrumentInput:
    LUI v0, 0x8080
    LBU v0, 0xC929(v0)
    J 0x806E52D8
    NOP

vanillaBuildCameraMatrices:
    ADDIU sp, sp, -0xC0
    SW ra, 0x9C(sp)
    J 0x805FCA9C
    NOP

; Native water-tint renderer; retain all depth, map and smoothing logic.
widescreenNativeWater:
    ADDIU sp, sp, -0xD8
    LUI a1, 0x8077
    J 0x80701CA8
    NOP

; Native synchronous dialogue-to-glyph formatter.
vanillaDialogueLine:
    ADDIU sp, sp, -0x98
    SW s0, 0x28(sp)
    J 0x8070DEDC
    NOP

; Preserve the first two native instructions, then resume the original body.
saveNativePackedRead:
    ADDIU sp, sp, -0x28
    SW ra, 0x1C(sp)
    J 0x8060C6C0
    NOP

saveNativePackedWrite:
    ADDIU sp, sp, -0x28
    SW ra, 0x1C(sp)
    J 0x8060C650
    NOP

saveNativeLoadGame:
    ADDIU sp, sp, -0x48
    SW s0, 0x18(sp)
    J 0x8060DC44
    NOP

vanillaRecruitmentPlayerSpawn:
    ADDIU sp, sp, -0x30
    SW s0, 0x14(sp)
    J 0x806C8514
    NOP

saveNativeCollectTotals:
    ADDIU sp, sp, -0x28
    LUI v0, 0x8080
    J 0x806ABE44
    NOP

vanillaCompletionPercentage:
    ADDIU sp, sp, -0x28
    SW ra, 0x14(sp)
    J 0x8003230C
    NOP

vanillaFileSummaryInit:
    ADDIU sp, sp, -0x80
    SW ra, 0x4C(sp)
    J 0x800297C0
    NOP

vanillaFileSummaryDraw:
    ADDIU sp, sp, -0xF0
    SDC1 f20, 0x38(sp)
    J 0x800291D4
    NOP

; Mode15's position/scale and lock-color arrays belong to five faces. Slot5
; scale would overlap erase state. Only Krusha consumes resident values here.
; The patched J's delay slot retains native LUI t8,8003 at80031474.
krushaFilePortraitLayout:
    LW t2, 0x8(t1)
    LUI at, 0x40A0 ; float5.0 index, compared as raw bits
    BNE t2, at, @@native
    NOP
    LUI at, hi(krushaFilePortraitTransform)
    ADDIU at, at, lo(krushaFilePortraitTransform)
    LW t2, 0(at)
    LW t3, 4(at)
    LW t4, 8(at)
    SW t2, 0x340(s0)
    SW t3, 0x344(s0)
    SW t4, 0x360(s0)
    SW t4, 0x364(s0)
    LUI t2, 0xC348
    SW t2, 0(at)
    SW t2, 4(at)
    LUI at, hi(krushaFilePortraitShade)
    LBU t2, lo(krushaFilePortraitShade)(at)
    SB t2, 0x36A(s0)
    SB t2, 0x36B(s0)
    SB t2, 0x36C(s0)
    J 0x80031510
    NOP
@@native:
    LWC1 f18, 0x8(t1)
    J 0x80031478
    NOP

; Native pause builder and sprite updater prologues.
vanillaPauseBuild:
    ADDIU sp, sp, -0x90
    LUI t6, 0x8075
    J 0x806AA30C
    NOP
vanillaPauseSprite:
    ADDIU sp, sp, -0x58
    SW ra, 0x1C(sp)
    J 0x806AC084
    NOP

; Replace page*5 with page*current character count. Original delay-slot
; floating multiply at806A9B18 still executes before entering this branch.
krushaPauseRingStride:
    LUI at, hi(krushaPauseCount)
    LW at, lo(krushaPauseCount)(at)
    MULT t9, at
    MFLO s4
    J 0x806A9B20
    NOP

vanillaSnideBoard:
    ADDIU sp, sp, -0x50
    LUI v0, 0x8080
    J 0x80024EF8
    NOP
vanillaSnideDraw:
    ADDIU sp, sp, -0x190
    SW s0, 0x18(sp)
    J 0x800252B4
    NOP

; Keep the expanded six-face ring vertically clear of headings/GB counters.
; Native delay-slot X-anchor adjustment at806A9B7C executes before this hook.
krushaPauseRingY:
    LUI at, hi(krushaPauseCount)
    LW at, lo(krushaPauseCount)(at)
    ADDIU at, at, -6
    BNEZ at, @@native
    NOP
    LUI at, 0x3F40
    MTC1 at, f8
    MUL.S f8, f20, f8
    MUL.S f8, f0, f8
    J 0x806A9B80
    NOP
@@native:
    MUL.S f8, f0, f20
    J 0x806A9B80
    NOP

saveNativeTotalGBs:
    LUI a0, 0x8080
    LUI a3, 0x8080
    J 0x806FB420
    NOP
saveNativeHUDGBs:
    ANDI t6, a0, 0xFF
    SLL t7, t6, 2
    J 0x806F8280
    NOP

; M2 HUD icon selector: preserve native argument/frame prologue.
m2NativeHUDSprite:
    ADDIU sp, sp, -0x20
    SW ra, 0x14(sp)
    J 0x806FACF0
    NOP

; Scoped actor collision table dispatch, unchanged for all ordinary actors.
m3TnsQuota:
    ; 806BE498 has summed the original five fed counters in v1. a0 is
    ; level*2; t1 is the native quota. Include earned sixth credit even OFF.
    ; No player/owner swap, no change to the original quota or boss choice.
    LUI at, 0x8080
    ADDU at, at, a0
    LHU at, 0xCB4C(at)
    ADDU v1, v1, at
    SLT at, v1, t1
    BEQZ at, @@stop
    LUI t2, 0x8080
    J 0x806BE4BC
    NOP
@@stop:
    J 0x806BE4A8
    NOP

m3BlueprintOwner:
    ; s2 is the actual candidate actor, s3 its native collect definition,
    ; s8 the player. Override only the registered gray actor's owner.
    LUI at, hi(m3CollectingBlueprint)
    SW zero, lo(m3CollectingBlueprint)(at)
    LUI at, hi(m4CollectingBonus)
    SW zero, lo(m4CollectingBonus)(at)
    LUI at, hi(m4DroppedBonus)
    LW at, lo(m4DroppedBonus)(at)
    BNE at, s2, @@blueprint
    NOP
    LW v0, 0x54(s2)
    LUI at, hi(m4DroppedBonusID)
    LW at, lo(m4DroppedBonusID)(at)
    BNE v0, at, @@blueprint
    NOP
    LI v0, 1
    LUI at, hi(m4CollectingBonus)
    SW v0, lo(m4CollectingBonus)(at)
    LI v0, 7
    J 0x806F74A4
    NOP
@@blueprint:
    LUI at, hi(m3DroppedBlueprint)
    LW at, lo(m3DroppedBlueprint)(at)
    BNE at, s2, @@ordinary
    NOP
    LW v0, 0x54(s2)
    LUI at, hi(m3DroppedBlueprintID)
    LW at, lo(m3DroppedBlueprintID)(at)
    BNE v0, at, @@ordinary
    NOP
    LI v0, 1
    LUI at, hi(m3CollectingBlueprint)
    SW v0, lo(m3CollectingBlueprint)(at)
    LI v0, 7
    J 0x806F74A4
    NOP
@@ordinary:
    LH v0, 0xC(s3)
    BNEZ v0, @@owned
    NOP
    LH t2, 0x10(s3)
    J 0x806F74B4
    NOP
@@owned:
    J 0x806F74A4
    NOP

m2NativeActorCollision:
    ADDIU sp, sp, -0x30
    SW ra, 0x2C(sp)
    J 0x80675818
    NOP

; Native world-model2 caller retains its current model in s0. Its original
; a0/a1/a2 and return address stay intact; only provide the fourth argument.
krushaRecruitmentKeyAlphaCall:
    MOVE a3, s0
    J krushaRecruitmentKeyAlpha
    NOP

; The shared native crate handler allows every Kong to activate Rambi.
; For the Isles reward, v0 is the player actor type and t2 is ACTOR_DK (2).
; Non-Rambi actors retain the previously calculated native eligibility in a1.
islesRambiOwner:
    BNE v1, at, @@resume
    NOP
    LUI at, hi(CurrentMap)
    LW at, lo(CurrentMap)(at)
    XORI at, at, 34
    BNEZ at, @@allow
    NOP
    BNE v0, t2, @@resume
    NOP
@@allow:
    ADDIU a1, zero, 1
@@resume:
    J 0x8067ED34
    NOP

; On the Isles we play this same SFX at entry. The cue call from the
; original Jungle Japes crate still uses its native timing and arguments.
islesRambiEmergenceSound:
    LUI t0, hi(CurrentMap)
    LW t0, lo(CurrentMap)(t0)
    ADDIU t1, zero, 34
    BEQ t0, t1, @@return
    NOP
    J playSound
    NOP
@@return:
    JR ra
    NOP

; Skip the first-use dialogue on the Isles without setting the native flag.
islesAnimalFirstUseText:
    LUI t0, hi(CurrentMap)
    LW t0, lo(CurrentMap)(t0)
    ADDIU t1, zero, 34
    BEQ t0, t1, @@return
    NOP
    J 0x806ED508
    NOP
@@return:
    JR ra
    NOP

; The player update reaches this block only for the two animal forms.
; Continue straight to the manual reversion check on the Isles.
islesAnimalZone:
    LUI t9, hi(CurrentMap)
    LW t9, lo(CurrentMap)(t9)
    ADDIU at, zero, 34
    BEQ t9, at, @@manual
    ANDI t9, t8, 0x0800
    BEQZ t9, @@manual
    NOP
    J 0x806CB58C
    NOP
@@manual:
    J 0x806CB5AC
    NOP

; Native surface solver's depth local is at sp+0x2c. Its return address
; is already saved in the native frame, so this can call the depth helper.
islesRambiSwimDepthHook:
    LWC1 f12, 0x2C(sp)
    JAL islesRambiSwimDepth
    LW a1, 0(s0)
    SWC1 f0, 0x2C(sp)
    LW t6, 0(s0)
    J 0x806D85B8
    ADDIU at, zero, 0x4E
