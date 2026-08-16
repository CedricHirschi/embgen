---
name: add-domain
description: Add a new embgen domain (Pydantic models, DomainGenerator, templates, tests, docs). Use when creating a built-in or user domain, running embgen new, or adding a plugin under src/embgen/domains/.
---

# Add a domain

## Prefer the scaffold

```bash
uv run embgen new <name> --builtin          # src/embgen/domains/<name>/
uv run embgen new <name> --location ./domains
```

Then replace the placeholders. Do not invent a different package shape.

## Required pieces

| File | Must |
| --- | --- |
| `__init__.py` | `from .generator import XGenerator` then `generator = XGenerator()` |
| `models.py` | Subclass `embgen.models.BaseConfig`; add domain fields |
| `generator.py` | `name`, `description`, `detect`, `validate`, `render`; optional `post_generate` |
| `templates/template.<ext>.j2` | At least one discovered template |

`name` is the CLI subcommand. `detect()` must not collide with existing keys:

| Key | Domain |
| --- | --- |
| `commands` | commands |
| `regmap` | registers |
| `regmap_shallow` | registers_shallow |
| `methods` | jsonrpc **and** nanopb (collision) |

Use a unique top-level YAML key, or `data.get("domain") == "<name>"` plus a structural check.

## Implement

1. Fields on the config model. Validators for IDs, addresses, duplicates.
2. `validate()`: `cast(BaseConfig, MyConfig.model_validate(data))`. Expand numbered/multireg entries here if needed (see `registers` / `registers_shallow`).
3. `render()`: pass sorted collections and `generated_on=datetime.now().strftime("%Y-%m-%d %H:%M:%S")` if sibling domains do.
4. `post_generate()`: copy static support files only for generated extensions, honor `copy_support_files`.
5. Keep `templates_path` as `Path(__file__).parent / "templates"` in `generator.py` (what `embgen new` emits). The ABC default also resolves to `domains/<name>/templates`.

## Finish

- Tests in `test/test_<name>.py` plus YAML in `test/configs/<name>/`.
- Docs page `docs/domains/<name>.md` and a `mkdocs.yml` nav entry.
- Run `just test` and `just lint`.
- If this is a user domain, document `EMBGEN_DOMAINS_DIR` / `--domains-dir` instead of `--builtin`.

Reference: `docs/extending/index.md`, `models.md`, `generators.md`.
