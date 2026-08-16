---
name: debug-generation
description: Diagnose missing, wrong, or empty embgen output. Use when templates do not run, CLI flags are missing, YAML fails validation, auto-detect picks the wrong domain, or generated C/Python/Markdown looks wrong.
---

# Debug generation

Work from the pipeline. Do not start by rewriting templates.

## 1. Which domain ran?

```bash
uv run embgen auto config.yml -o generated/ --h -d
```

`-d` / `--debug` prints timing. Explicit subcommands beat `auto`.

`detect_domain()` returns the **first** generator whose `detect()` is true. `jsonrpc` and `nanopb` both look for `methods`. If the wrong one fires, use `embgen jsonrpc` / `embgen nanopb`, or tighten `detect()`.

Discovery skips packages without `__init__.py`, names starting with `_`, and import failures (swallowed). If a new domain is invisible, import it by hand:

```bash
uv run python -c "from embgen.discovery import discover_domains; print(sorted(discover_domains()))"
```

User domains: `--domains-dir` or `EMBGEN_DOMAINS_DIR`. Same `name` overrides a built-in.

## 2. Did validation accept the YAML?

Failures are Pydantic `ValidationError`. Reproduce:

```python
from pathlib import Path
from embgen.generator import CodeGenerator
from embgen.discovery import discover_domains

g = CodeGenerator(discover_domains()["commands"], Path("generated"))
g.validate(g.parse_yaml(Path("config.yml")))
```

Check `test/configs/<domain>/` for a known-good shape.

## 3. Was the template discovered?

`discover_templates(path)` keys off filename, not content. Wrong name means no CLI flag.

Multifile: every file in the group must share `<group>_multi`. `--c-multi` will not pick up a stray `template.h.j2`.

## 4. Render vs post_generate

Wrong **content** → `render()` kwargs or the `.j2` file. Sort order is applied in `render()` for most domains.

File **missing** that is not a template → `post_generate()` (support files, `regtool.py` after `.hjson`).

Registers `.hjson` runs `regtool.py -r -t <output> <file.hjson>` with `cwd` set to that domain's `regtool/` folder. If RTL/headers from hjson are missing, use the `registers-regtool` skill.

## 5. Output path

`BaseConfig.output_filename` is `file` or `name.lower()`. Support copies use `support_output_filename` (`file_base` unless `support_file` is set).

Write repros under `generated/` or a temp dir. Do not commit them.
