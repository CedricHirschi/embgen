# CLI Usage

embgen provides a command-line interface for generating code from YAML configuration files.

## Basic Syntax

```bash
embgen [OPTIONS] COMMAND INPUT -o OUTPUT [FORMAT_FLAGS]
```

## Global Options

| Option               | Description                                 |
| -------------------- | ------------------------------------------- |
| `--help`, `-h`       | Show help message                           |
| `-d`, `--debug`      | Enable debug output with timing information |
| `--domains-dir PATH` | Load additional domains from this directory |

## Commands

### Domain Subcommands

Each domain is exposed as a subcommand. The built-in domains are:

```bash
embgen commands INPUT -o OUTPUT [FLAGS]   # Generate from command definitions
embgen registers INPUT -o OUTPUT [FLAGS]  # Generate from register maps
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
| `--location PATH` | Directory where the domain folder will be created        |
| `--builtin`       | Create the domain in embgen's built-in domains directory |

## Domain-Specific Options

### Common Options

All domain subcommands share these options:

| Option                | Description                          |
| --------------------- | ------------------------------------ |
| `INPUT`               | Path to the YAML configuration file  |
| `-o`, `--output PATH` | Output directory for generated files |

### Output Format Flags

Each domain defines its own output format flags based on available templates:

=== "Commands"

    | Flag   | Output                                             |
    | ------ | -------------------------------------------------- |
    | `--h`  | C header file (`commands.h`)                       |
    | `--py` | Python module (`commands.py` + `commands_base.py`) |
    | `--md` | Markdown documentation (`commands.md`)             |

=== "Registers"

    | Flag   | Output                                         |
    | ------ | ---------------------------------------------- |
    | `--h`  | C header file (`<name>.h` + `reg_common.h/.c`) |
    | `--py` | Python module (`<name>.py`)                    |
    | `--md` | Markdown documentation (`<name>.md`)           |

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

- Files with a `commands` key → Commands domain
- Files with a `regmap` key → Registers domain

### Use Custom Domains

```bash
# Load domains from a custom directory
embgen --domains-dir ./my_domains mydom config.yml -o output/ --h
```

### Create a New Domain

```bash
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
Error: Could not auto-detect domain. Abailable: [...]
```
