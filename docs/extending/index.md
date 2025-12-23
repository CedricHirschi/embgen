# Extending embgen

embgen is designed to be easily extensible with custom domains. A domain is a self-contained package that:

- Defines a YAML schema for input configuration
- Provides Jinja2 templates for code generation
- Implements validation and rendering logic

## Creating a New Domain

The quickest way to create a new domain is using the `embgen new` command:

```bash
# Create in a custom directory
embgen new myprotocol --location ./domains

# Create as a built-in domain
embgen new myprotocol --builtin
```

This scaffolds a complete domain with:

```
myprotocol/
├── __init__.py       # Domain entry point
├── generator.py      # Generator implementation
├── models.py         # Pydantic data models
└── templates/
    ├── template.h.j2   # C header template
    ├── template.py.j2  # Python template
    └── template.md.j2  # Markdown template
```

## Domain Structure

### Required Files

| File           | Purpose                            |
| -------------- | ---------------------------------- |
| `__init__.py`  | Exports the generator instance     |
| `generator.py` | Implements `DomainGenerator` ABC   |
| `models.py`    | Defines Pydantic validation models |
| `templates/`   | Contains Jinja2 templates          |

### Entry Point (`__init__.py`)

The `__init__.py` must export a `generator` variable:

```python
"""The myprotocol domain for embgen."""

from .generator import MyprotocolGenerator

generator = MyprotocolGenerator()
```

## Topics

<div class="grid cards" markdown>

-   :material-database-outline: **[Writing Models](models.md)**

    ---

    Define Pydantic models for YAML validation

-   :material-cog-outline: **[Writing Generators](generators.md)**

    ---

    Implement the DomainGenerator interface

-   :material-file-document-outline: **[Writing Templates](templates.md)**

    ---

    Create Jinja2 templates for output formats

-   :material-folder-multiple-outline: **[Multifile Templates](multifile.md)**

    ---

    Generate multiple files from a single template group

</div>
