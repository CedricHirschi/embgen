---
description: Generate code from a YAML config with embgen
---

Run embgen against a YAML file. Prefer an explicit domain subcommand over `auto` (`jsonrpc` and `nanopb` both detect `methods`).

```bash
uv run embgen <domain> <config.yml> -o generated/ --h --py --md
```

If the user did not name a config, use a matching file under `test/configs/<domain>/`. Write to `generated/` (gitignored). Show the written filenames. If output is wrong, switch to `.cursor/skills/debug-generation/SKILL.md`.
