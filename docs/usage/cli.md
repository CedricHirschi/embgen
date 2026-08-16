# CLI Usage

embgen provides a command-line interface for generating code from YAML configuration files.

## Basic Syntax

```bash
embgen [OPTIONS] COMMAND [ARGS]
```

`-o` / `--output` defaults to `./generated` relative to the current working directory. Format flags still have to be listed (`--h`, `--py`, …).

## Global Options

| Option               | Description                                 |
| -------------------- | ------------------------------------------- |
| `--help`, `-h`       | Show help message                           |
| `-d`, `--debug`      | Enable debug output with timing information |
| `-s`, `--silent`     | Suppress all but warning and error messages |
| `--domains-dir PATH` | Load additional domains from this directory |

## Commands

### Domain Subcommands

Each domain is a subcommand. Built-in names:

```bash
embgen commands INPUT [FLAGS]              # Command protocols
embgen registers INPUT [FLAGS]             # Register maps (`regmap`)
embgen registers_shallow INPUT [FLAGS]     # Register maps (`regmap_shallow`)
embgen jsonrpc INPUT [FLAGS]               # JSON-RPC methods
embgen nanopb INPUT [FLAGS]                # NanoPB / protobuf methods
embgen testing INPUT [FLAGS]               # Test-suite domain only
```

### Auto-detect Domain

Use `auto` to let embgen detect the domain from the YAML content:

```bash
embgen auto INPUT -o OUTPUT [FLAGS]
```

### Create New Domain

Use `new` to scaffold a new domain:

```bash
embgen new DOMAIN_NAME [OPTIONS]
```

| Option            | Description                                              |
| ----------------- | -------------------------------------------------------- |
| `--location PATH` | Directory where the domain folder will be created (default: current directory) |
| `--builtin`       | Create the domain in embgen's built-in domains directory |

## Domain-Specific Options

### Common Options

All domain subcommands share these options:

| Option                | Description                          |
| --------------------- | ------------------------------------ |
| `INPUT`               | Path to the YAML configuration file  |
| `-o`, `--output PATH` | Output directory for generated files |
| `--json-schema`       | Output a JSON Schema file for the domain's configuration model |

### Output Format Flags

Each domain defines its own output format flags based on available templates:

=== "Commands"

    | Flag   | Output                                             |
    | ------ | -------------------------------------------------- |
    | `--h`  | C header (`<file>.h`)                              |
    | `--py` | Python module (`<file>.py` + `<file>_base.py`)     |
    | `--md` | Markdown documentation (`<file>.md`)               |

=== "Registers"

    | Flag        | Output                                                      |
    | ----------- | ----------------------------------------------------------- |
    | `--h`       | C header (`<file>.h`)                                       |
    | `--py`      | Python module (`<file>.py` + `registers_base.py`)           |
    | `--md`      | Markdown documentation                                      |
    | `--hjson`   | Hjson, then OpenTitan `regtool.py`                          |
    | `--c-multi` | `<file>_impl.h`, `<file>_base.h`, `<file>_base.c`           |

=== "Registers (shallow)"

    | Flag      | Output                                            |
    | --------- | ------------------------------------------------- |
    | `--h`     | C header                                          |
    | `--py`    | Python module + `registers_base.py`               |
    | `--md`    | Markdown                                          |
    | `--hjson` | Hjson, then `regtool.py` (`*_reg_pkg.sv`, `*_reg_top.sv`) |

=== "JSON-RPC"

    | Flag   | Output   |
    | ------ | -------- |
    | `--py` | Python   |
    | `--md` | Markdown |

=== "NanoPB"

    | Flag        | Output            |
    | ----------- | ----------------- |
    | `--proto`   | `.proto`          |
    | `--options` | NanoPB `.options` |
    | `--py`      | Python            |
    | `--md`      | Markdown          |

## Examples

### Generate C Header Only

```bash
embgen commands mycommands.yml -o generated/ --h
```

### Generate Multiple Formats

```bash
embgen commands mycommands.yml -o generated/ --h --py --md
```

### Generate with Debug Output

```bash
embgen -d commands mycommands.yml -o generated/ --h
```

This shows timing information:

```log
[12:34:56] INFO     Loading YAML file from mycommands.yml
[12:34:56] INFO     Generating C Header... done after 0.02s
[12:34:56] INFO     Generation complete in 0.05s
```

### Auto-detect Domain Type

```bash
embgen auto config.yml -o generated/ --h
```

embgen examines the YAML structure to determine the appropriate domain:

- `commands` → Commands
- `regmap` → Registers
- `regmap_shallow` → Registers (shallow)
- `methods` → JSON-RPC **or** NanoPB (same key; use an explicit subcommand)
- `items` (without `commands`/`regmap`) → testing

### Use Custom Domains

```bash
# Load domains from a custom directory
embgen --domains-dir ./my_domains mydom config.yml -o output/ --h
```

### Create a New Domain

```bash
# Create in the current directory
embgen new mydomain

# Create in a custom location
embgen new mydomain --location ./domains

# Create as a built-in domain
embgen new mydomain --builtin
```

## Environment Variables

| Variable             | Description                                |
| -------------------- | ------------------------------------------ |
| `EMBGEN_DOMAINS_DIR` | Additional directory to search for domains |

This allows you to set up custom domains without specifying `--domains-dir` every time:

```bash
export EMBGEN_DOMAINS_DIR=/path/to/my/domains
embgen mydom config.yml -o output/ --h
```

## Exit Codes

| Code | Meaning                                                           |
| ---- | ----------------------------------------------------------------- |
| `0`  | Success                                                           |
| `1`  | Error (invalid arguments, file not found, validation error, etc.) |

## Error Handling

### File Not Found

```bash
$ embgen commands nonexistent.yml -o output/ --h
ERROR    Generation failed: Input file .../nonexistent.yml does not exist
```

### No Output Format Specified

```bash
$ embgen commands config.yml -o output/
ERROR    No output formats specified. Use -h to see available formats.
```

### Invalid YAML

```bash
$ embgen commands invalid.yml -o output/ --h
Error: Failed to load YAML file
```

### Auto-detect Failure

```bash
$ embgen auto unknown.yml -o output/ --h
Error: Could not auto-detect domain. Available: [...]
```
