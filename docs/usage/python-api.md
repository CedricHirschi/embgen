# Python API

embgen can be used as a Python library for programmatic code generation.

## Quick Start

```python
from pathlib import Path
from embgen.discovery import discover_domains
from embgen.generator import CodeGenerator

# Discover available domains
domains = discover_domains()

# Get the commands generator
commands_gen = domains["commands"]

# Create a code generator
code_gen = CodeGenerator(commands_gen, Path("output"))

# Generate from a YAML file
templates = {"h": "template.h.j2", "py": "template.py.j2"}
generated_files = code_gen.generate_from_file(Path("config.yml"), templates)

print(f"Generated: {generated_files}")
```

## Core Classes

### CodeGenerator

The main orchestration class for code generation.

```python
from embgen.generator import CodeGenerator

code_gen = CodeGenerator(domain_generator, output_path)
```

#### Constructor Parameters

| Parameter     | Type              | Description                 |
| ------------- | ----------------- | --------------------------- |
| `generator`   | `DomainGenerator` | The domain generator to use |
| `output_path` | `Path`            | Directory for output files  |

#### Methods

##### `parse_yaml(input_path: Path) -> dict`

Parse a YAML file and return the data as a dictionary.

```python
data = code_gen.parse_yaml(Path("config.yml"))
```

##### `validate(data: dict) -> BaseConfig`

Validate YAML data against the domain schema.

```python
config = code_gen.validate(data)
```

##### `generate_from_file(input_path: Path, templates: dict) -> list[str]`

Generate output files from a YAML input file.

```python
templates = {"h": "template.h.j2", "md": "template.md.j2"}
filenames = code_gen.generate_from_file(Path("config.yml"), templates)
```

##### `generate(config: BaseConfig, templates: dict) -> list[str]`

Generate output files from an already-validated configuration.

```python
config = code_gen.validate(data)
filenames = code_gen.generate(config, templates)
```

## Discovery Functions

### discover_domains

Discover all available domain generators.

```python
from embgen.discovery import discover_domains

# Discover built-in domains only
domains = discover_domains()
# Returns: {"commands": CommandsGenerator, "registers": RegistersGenerator}

# Include custom domains directory
domains = discover_domains(extra_domains_dir=Path("/path/to/domains"))
```

### detect_domain

Auto-detect which domain should handle given YAML data.

```python
from embgen.discovery import detect_domain, discover_domains

domains = discover_domains()
data = {"name": "MyCommands", "commands": [...]}

domain_name = detect_domain(data, domains)
# Returns: "commands"
```

## Template Discovery

### discover_templates

Discover available templates for a domain.

```python
from embgen.templates import discover_templates

single_templates, multifile_groups = discover_templates(templates_path)

# single_templates: {"h": ("C Header", "template.h.j2"), ...}
# multifile_groups: {"c": MultifileGroup(...), ...}
```

## Working with Configurations

### Loading and Validating

```python
from pathlib import Path
from embgen.discovery import discover_domains
from embgen.generator import CodeGenerator

domains = discover_domains()
code_gen = CodeGenerator(domains["commands"], Path("output"))

# Parse YAML
data = code_gen.parse_yaml(Path("commands.yml"))

# Validate and get typed config
config = code_gen.validate(data)

# Access config properties
print(f"Name: {config.name}")
print(f"Output filename: {config.output_filename}")
```

### Direct Model Instantiation

You can also create configurations directly in Python:

```python
from embgen.domains.commands.models import CommandsConfig, Command, Argument

config = CommandsConfig(
    name="MyCommands",
    commands=[
        Command(
            name="ping",
            id=0,
            description="Ping the device",
            args=[
                Argument(name="probe_id", type="B", description="Probe ID")
            ]
        )
    ]
)
```

## Custom Generation Pipeline

### Step-by-Step Generation

```python
from pathlib import Path
from embgen.discovery import discover_domains
from embgen.generator import CodeGenerator
from embgen.templates import discover_templates

# 1. Set up
domains = discover_domains()
generator = domains["commands"]
code_gen = CodeGenerator(generator, Path("output"))

# 2. Discover available templates
single, multifile = discover_templates(generator.templates_path)
print(f"Available formats: {list(single.keys())}")

# 3. Load and validate
data = code_gen.parse_yaml(Path("config.yml"))
config = code_gen.validate(data)

# 4. Generate specific templates
templates = {"h": single["h"][1]}  # Just C header
code_gen.ensure_output_dir()

for ext, template_name in templates.items():
    filename = code_gen.render_to_file(config, template_name, ext)
    print(f"Generated: {filename}")

# 5. Run post-generation hooks
extra_files = generator.post_generate(
    config, 
    code_gen.output_path, 
    set(templates.keys())
)
print(f"Extra files: {extra_files}")
```

### Rendering to String

If you need the generated content without writing to a file:

```python
from jinja2 import Template

template = code_gen.env.get_template("template.h.j2")
content = generator.render(config, template)
print(content)
```

## Scaffolding New Domains

```python
from pathlib import Path
from embgen.scaffold import scaffold_domain

# Create a new domain
created_files = scaffold_domain("myprotocol", Path("./domains"))

for f in created_files:
    print(f"Created: {f}")
```

## Complete Example

```python
"""Generate both C header and Python from commands YAML."""
from pathlib import Path

from embgen.discovery import discover_domains, detect_domain
from embgen.generator import CodeGenerator
from embgen.templates import discover_templates


def generate_commands(yaml_path: Path, output_dir: Path) -> list[str]:
    """Generate all formats from a commands YAML file."""
    
    # Discover domains
    domains = discover_domains()
    
    # Set up generator
    generator = domains["commands"]
    code_gen = CodeGenerator(generator, output_dir)
    
    # Discover templates
    single_templates, _ = discover_templates(generator.templates_path)
    
    # Build template dict (all formats)
    templates = {ext: info[1] for ext, info in single_templates.items()}
    
    # Generate
    return code_gen.generate_from_file(yaml_path, templates)


if __name__ == "__main__":
    files = generate_commands(
        Path("commands.yml"),
        Path("generated")
    )
    print(f"Generated {len(files)} files: {files}")
```

## Error Handling

```python
from pydantic import ValidationError

try:
    config = code_gen.validate(data)
except RuntimeError as e:
    print(f"Validation failed: {e}")

try:
    data = code_gen.parse_yaml(Path("missing.yml"))
except FileNotFoundError as e:
    print(f"File not found: {e}")
```
