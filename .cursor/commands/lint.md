---
description: Format, lint, and typecheck (just lint)
---

Run from the repo root:

```bash
just lint
```

That is `ruff format`, `ruff check --fix`, then `ty check --exclude docs` (regtool trees are already excluded in `pyproject.toml`).

Fix issues you introduced. Do not mass-reformat `src/embgen/domains/*/regtool/`.
