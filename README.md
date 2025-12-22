# embgen - Embedded Code Generator

A unified code generator for embedded systems that generates code from YAML definitions.

## Features

- **Plugin-based architecture**: Add new domains by creating a single directory
- **Auto-discovery**: CLI automatically discovers available domains
- **Auto-detection**: Automatically detect domain from YAML content
- **Multiple output formats**: Generate C headers, Python, Markdown documentation, and more
- **Template-based**: Uses Jinja2 templates for flexible output customization

## Supported Domains

### Commands
Generate command protocol code from YAML command definitions.
- C header with command IDs, argument structures, and enumerations
- Python dataclasses with serialization support
- Markdown documentation

### Registers
Generate register map code from YAML register definitions.
- C header with addresses, bitfield macros, and accessor functions
- Python classes with hardware abstraction
- Markdown documentation with bit layouts

## Installation

```bash
# Using uv
uv sync

# Or with pip
pip install -e .
```

## Usage

### Commands Domain

```bash
# Generate C header and Markdown documentation
embgen commands input.yml -o output/ --h --md

# Generate all formats
embgen commands input.yml -o output/ --h --md --py
```

### Registers Domain

```bash
# Generate C header and Markdown documentation
embgen registers input.yml -o output/ --h --md

# Generate all formats
embgen registers input.yml -o output/ --h --md --py
```

### Auto-Detect Mode

```bash
# Automatically detect domain from YAML content
embgen auto input.yml -o output/ --h --md
```

## Adding a New Domain

To add a new domain (e.g., `interfaces`), create a new directory under `src/embgen/domains/`:

```
domains/
└── interfaces/
    ├── __init__.py      # generator = InterfacesGenerator()
    ├── models.py        # Pydantic models for the domain
    ├── generator.py     # Generator class implementing DomainGenerator
    └── templates/
        ├── template.h.j2
        ├── template.md.j2
        └── template.py.j2
```

### Required Files

1. **`__init__.py`**: Export a `generator` instance
   ```python
   from .generator import InterfacesGenerator
   generator = InterfacesGenerator()
   ```

2. **`models.py`**: Define Pydantic models with an `output_filename` property
   ```python
   class InterfacesConfig(BaseModel):
       name: str
       file: str | None = None
       interfaces: list[Interface]

       @property
       def output_filename(self) -> str:
           return self.file or self.name.lower()
   ```

3. **`generator.py`**: Implement the `DomainGenerator` interface
   ```python
   class InterfacesGenerator(DomainGenerator):
       @property
       def name(self) -> str:
           return "interfaces"

       @property
       def description(self) -> str:
           return "Generate code from interface definitions"

       @property
       def templates_path(self) -> Path:
           return Path(__file__).parent / "templates"

       def detect(self, data: dict) -> bool:
           return "interfaces" in data

       def validate(self, data: dict) -> InterfacesConfig:
           return InterfacesConfig.model_validate(data)

       def render(self, config: InterfacesConfig, template: Template) -> str:
           return template.render(name=config.name, interfaces=config.interfaces)
   ```

4. **Templates**: Create Jinja2 templates named `template.{ext}.j2`

The CLI will automatically discover and expose your new domain as a subcommand.

### Multifile Templates

embgen supports generating multiple output files from a single YAML input. This is useful for:
- Generating paired files like `.c` and `.h` for C modules
- Generating multiple files of the same type (e.g., multiple `.sv` SystemVerilog files)

#### Template Naming Conventions

**Different extensions (e.g., C header + source):**
```
template.{group}_multi.{ext}.j2
```

Examples:
- `template.c_multi.h.j2` → generates `{name}.h`
- `template.c_multi.c.j2` → generates `{name}.c`

**Same extension with numbered suffix:**
```
template.{group}_multi.{ext}.{suffix}.j2
```

Examples:
- `template.sv_multi.sv.1.j2` → generates `{name}_1.sv`
- `template.sv_multi.sv.2.j2` → generates `{name}_2.sv`

#### CLI Usage

Multifile groups appear as CLI flags with the pattern `--{group}-multi`:

```bash
# Generate C header + source files
embgen mydom input.yml -o output/ --c-multi

# Generate multiple SystemVerilog files
embgen mydom input.yml -o output/ --sv-multi
```

#### Example Directory Structure

```
templates/
├── template.py.j2           # Single-file template → {name}.py
├── template.c_multi.h.j2    # Multifile C header  → {name}.h
├── template.c_multi.c.j2    # Multifile C source  → {name}.c
├── template.sv_multi.sv.1.j2  # SV file 1 → {name}_1.sv
└── template.sv_multi.sv.2.j2  # SV file 2 → {name}_2.sv
```

## YAML Examples

### Commands

```yaml
name: MyCommands
commands:
  - name: ping
    id: 0
    description: "Ping the device"
    args:
      - name: device_id
        type: B
        description: "Device ID to ping"
        default: 1
```

### Registers

```yaml
name: MyRegisters
regmap:
  - name: CONTROL
    address: 0
    description: "Control register"
    bitfields:
      - name: ENABLE
        width: 1
        offset: 0
        reset: 0
        description: "Enable bit"
```

## License

MIT
