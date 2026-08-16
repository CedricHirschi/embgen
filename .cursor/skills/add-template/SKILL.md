---
name: add-template
description: Add a Jinja2 output format or multifile group to an embgen domain. Use when adding --h/--py/--md flags, template.h.j2, multifile templates, or a new generated language.
---

# Add a template

## Name it so discovery works

`embgen.templates.parse_template_name` / `discover_templates` only see `*.j2` and `*.jinja`.

| Filename | CLI | Output |
| --- | --- | --- |
| `template.rs.j2` | `--rs` | `<output_filename>.rs` |
| `template.c_multi.h.j2` + `template.c_multi.c.j2` | `--c-multi` | `.h` and `.c` |
| `template.sv_multi.sv.1.j2` | `--sv-multi` | `<name>_1.sv` |

`FILE_TYPES` in `templates.py` supplies the help text. Add an entry when you introduce a new extension, or the flag help will say "Unknown".

Partial/include files: `discover_templates()` does **not** skip `_` prefixes. A file named `_macros.h.j2` becomes the `--h` template. Use a non-conflicting name or a non-`.j2` static file.

## Context

Whatever `DomainGenerator.render()` passes is what the template sees. Match the existing `template.render(...)` kwargs for that domain. If you need a new variable, add it in `render()` and use it in **all** templates that should stay consistent (or keep it optional with `default`).

Common kwargs in this repo: `name`, `file`, `support_file`, `generated_on`, plus the domain collection (`commands`, `regmap`, `methods`, `config`).

Jinja env already has `trim_blocks`, `lstrip_blocks`, and `regex_replace`.

## Static companions

Files that are not Jinja (e.g. `commands_base.py`) are copied in `post_generate()`. Gate on `generated_extensions` (`"py" in generated_extensions`) and `config.copy_support_files`.

## Tests and docs

1. Render through `CodeGenerator.generate_from_file` into a temp dir; snapshot or substring-check the output.
2. CLI: `run_cli` in `test_cli.py` or a domain test with `--<ext>`.
3. Update `docs/domains/<domain>.md` and `docs/usage/cli.md` format tables.

Do not check generated files into git (`generated/` is ignored).
