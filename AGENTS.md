# Working on Krusha Expansion

Start with the [project handoff](codex_handoff/README.md) and [contributor walkthrough](CONTRIBUTING.md). Use your own Git author identity. The [handoff skill](.agents/skills/krusha-handoff/SKILL.md) routes placement, recruitment and presentation work to the relevant source and tests.

Each ROM build has its own emulator-state profile. Check the hash with `./tools/play-krusha.sh --info` before using a state. Use an isolated test profile to protect player progress. Generate offline HTML for a guide with `/usr/bin/python3 tools/render-docs.py PATH.md` when requested.
