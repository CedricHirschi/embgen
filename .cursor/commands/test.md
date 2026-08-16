---
description: Run embgen unit tests (just test)
---

Run the test suite from the repo root:

```bash
just test
```

If `just` is missing, use `uv run pytest`.

Summarize failures (file, test name, assertion). Do not "fix" vendored `regtool/` code unless the failing test is specifically about that tree and the user asked. After a domain or template change, say which `test/configs/` fixtures were exercised.
