---
name: registers-regtool
description: Work on embgen registers or registers_shallow OpenTitan hjson/regtool generation. Use when editing register YAML, hjson templates, post_generate subprocess, regtool_layout, or vendor copies under domains/*/regtool/.
---

# Registers and regtool

Two domains:

| Domain | YAML key | Notes |
| --- | --- | --- |
| `registers` | `regmap` | Expands `numbers:` into individual regs + `RegisterGroup` |
| `registers_shallow` | `regmap_shallow` | Keeps multiregs; `regtool_layout.py` builds the hjson view |

Both can emit `.hjson` then shell out to vendored OpenTitan `regtool.py`.

## Do not touch vendor trees by default

`src/embgen/domains/registers/regtool/` and `.../registers_shallow/regtool/` are third-party. `ty` excludes them. Change wrapper code first:

- `domains/registers/generator.py`
- `domains/registers_shallow/generator.py`
- `domains/registers_shallow/regtool_layout.py`
- `templates/template.hjson.j2`

## hjson post_generate

After `--hjson`, `post_generate` runs (cwd = domain `regtool/`):

```text
python regtool.py -r -t <output_dir> <output>/<name>.hjson
```

If that subprocess fails, generated RTL/headers will be missing even though the `.hjson` exists. Run the same command manually with `uv run python`.

Support files: `registers_base.py` copies when `--py` ran and `copy_support_files` is true. The generator also looks for `reg_common.h` / `.c` on `--h`; those files are not in the tree today, so nothing is copied.

## YAML gotchas

- Addresses: hex or int. `validate()` may expand numbered registers (`registers`) or attach `HjsonEntry` rows (`registers_shallow`).
- Bitfields: `offset` + `width`. Templates expect them sorted by offset (done in `render()` / layout).
- Access strings (`rw`, `ro`, `wo`, …) must stay aligned with both the Python models and hjson enums.

## Tests

Configs: `test/configs/registers/` and `test/configs/registers_shallow/`. Prefer those over inventing a full SoC map.

When changing hjson layout, assert the hjson (and, if cheap, that `regtool.py` exits 0). Do not vendor huge `topgen` golden RTL unless the user asked.
