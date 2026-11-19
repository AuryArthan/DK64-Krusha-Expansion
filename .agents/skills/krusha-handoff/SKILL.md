---
name: krusha-handoff
description: Find and modify DK64 Krusha Expansion gameplay, placement data, or recruitment progression and select a matching build, save profile and regression check.
---

Read the [developer handoff](../../../codex_handoff/README.md) for ownership of runtime, ROM-build and save changes. The [first collectible edit](../../../CONTRIBUTING.md) is a reproducible path from editable data to a verified output ROM.

For a position change, look up the stable marker label in the campaign or recruitment-key data. Preserve its save slot, object ID and owner. For progress changes, follow the save header and recruitment transaction through to the caller, especially when the fifth lock opens or a player revisits with previously turned-in keys. For a graphics bug, reproduce its specific renderer, screen mode and transition.

Choose the [test](../../../docs/testing.md) that exercises the affected path. The release fingerprint identifies an exact baseline. A deliberate gameplay edit should pass the applicable structural and gameplay checks with its own new hash. Use a disposable profile for test progress, and verify the ROM identity before loading emulator states. Report which checks used a real gameplay event, a host simulation or a staged setup.
