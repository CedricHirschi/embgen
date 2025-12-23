# embgen

**embgen** is a unified code generator for embedded systems that generates code from YAML definitions.

## Features

- **Plugin-based architecture** — Add new domains by creating a single directory
- **Auto-discovery** — CLI automatically discovers available domains
- **Auto-detection** — Automatically detect domain from YAML content
- **Multiple output formats** — Generate C headers, Python, Markdown documentation, and more
- **Template-based** — Uses Jinja2 templates for flexible output customization
- **Extensible** — Create custom domains for your specific code generation needs

## Quick Start

### Installation

```bash
# Using uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Generate Code

```bash
# Generate C header from a commands definition
embgen commands config.yml -o output/ --h

# Generate multiple formats at once
embgen commands config.yml -o output/ --h --py --md

# Auto-detect the domain type
embgen auto config.yml -o output/ --h
```

## Built-in Domains

embgen ships with two built-in domains:

| Domain                            | Description                  | Output Formats             |
| --------------------------------- | ---------------------------- | -------------------------- |
| [Commands](domains/commands.md)   | Command protocol definitions | C Header, Python, Markdown |
| [Registers](domains/registers.md) | Hardware register maps       | C Header, Python, Markdown |

## Documentation

- [CLI Usage](usage/cli.md) — Complete command-line reference
- [Python API](usage/python-api.md) — Using embgen as a library
- [Built-in Domains](domains/index.md) — Commands and Registers documentation
- [Creating Domains](extending/index.md) — How to create custom domains
- [Architecture](architecture.md) — Internal design and module structure
