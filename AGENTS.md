# embgen

YAML-in, generated code out. A domain is a plugin: Pydantic schema, Jinja2 templates, and a `DomainGenerator`. One YAML file is the source of truth for C headers, Python, Markdown, and other formats.

Python 3.11+, packaged with `uv`, tasks via `just`.

## Layout

```
src/embgen/
  cli.py            CLI (argparse + Rich)
  generator.py      CodeGenerator orchestration
  discovery.py      find domains, auto-detect from YAML keys
  templates.py      Jinja2 env, template name parsing
  models.py         BaseConfig, Enum, TemplateInfo, MultifileGroup
  scaffold.py       `embgen new` boilerplate
  domains/
    commands/       command protocols (`commands` key)
    registers/      register maps (`regmap` key), OpenTitan regtool on .hjson
    registers_shallow/  packed/multireg maps (`regmap_shallow` key)
    jsonrpc/        JSON-RPC methods (`methods` key)
    nanopb/         NanoPB methods (`methods` key)
    testing/        fixture domain for multifile / discovery tests
test/
  configs/<domain>/ sample YAML
  test_*.py
docs/               MkDocs Material
```

Do not treat `generated/` or `reports/` as source. They are gitignored.

## Commands

```bash
uv sync
just test          # pytest + coverage HTML in reports/
just lint          # ruff format + ruff check --fix + ty
just format
just check
just typecheck     # excludes docs/ and both regtool trees
just serve         # mkdocs live preview
```

Generate:

```bash
uv run embgen commands test/configs/commands/simple.yml -o generated/ --h --py --md
uv run embgen auto config.yml -o generated/ --h
uv run embgen new mydomain --builtin
```

CI (`.github/workflows/test.yml`) runs `just test` on Ubuntu.

## How generation works

1. CLI loads YAML, picks a domain (`embgen <domain>` or `embgen auto`).
2. `CodeGenerator` calls `validate()` then `render()` per selected template.
3. Output name is `config.output_filename` (`file` or lowercase `name`).
4. `post_generate()` copies static support files (e.g. `commands_base.py`).

Template filenames are the CLI flags:

| File | Flag | Output |
| --- | --- | --- |
| `template.h.j2` | `--h` | `<name>.h` |
| `template.py.j2` | `--py` | `<name>.py` |
| `template.c_multi.h.j2` + `template.c_multi.c.j2` | `--c-multi` | both files |
| `template.sv_multi.sv.1.j2` | `--sv-multi` | `<name>_1.sv` |

Jinja env: `trim_blocks=True`, `lstrip_blocks=True`, filter `regex_replace`. Non-`.j2`/`.jinja` files in `templates/` are not discovered; copy them from `post_generate()`.

## Conventions

- New built-in domains live in `src/embgen/domains/<name>/` and export `generator` from `__init__.py`.
- Config models subclass `embgen.models.BaseConfig` (`name`, optional `file`).
- `detect()` must be unique. `jsonrpc` and `nanopb` both key off `methods`; `embgen auto` returns the first match in dict order. Prefer an explicit subcommand, or a more specific `detect()`.
- Public Python uses Google docstrings. Match nearby style in domain `generator.py` files (those are terse).
- Tests are class-grouped pytest (`Test*`, `test_*`) under `test/`. Put YAML fixtures in `test/configs/<domain>/`.
- Docs: MkDocs Material, Google-style docstrings for mkdocstrings, mermaid via superfences.

## Do not

- Edit `src/embgen/domains/*/regtool/` unless the user asked to change the vendored OpenTitan tools. `ty` already excludes them.
- Reformat or "clean up" generated output in `generated/`.
- Add dependencies without updating `pyproject.toml` (runtime vs `dependency-groups.dev` / `docs`).
- Invent a new domain layout. Use `embgen new` or copy `commands/`.

## Cursor extras

Project skills in `.cursor/skills/`: `add-domain`, `add-template`, `debug-generation`, `registers-regtool`.

Slash commands in `.cursor/commands/`: `/test`, `/lint`, `/new-domain`, `/generate`, `/debug-generation`.

After Python edits, `.cursor/hooks.json` runs `ruff format` via `.venv` (hook command uses the Windows `py` launcher). Skip list includes `regtool/` and `generated/`.
