---
description: Scaffold or implement a new embgen domain
---

Follow the project skill `.cursor/skills/add-domain/SKILL.md`.

Default: built-in domain via `uv run embgen new <name> --builtin`, then fill models, `detect()`, templates, tests under `test/test_<name>.py` and `test/configs/<name>/`, plus a docs page if it is user-facing.

Ask for the domain name and whether it is `--builtin` or `--location` only if those were not given.
