# Writing Generators

Generators implement the `DomainGenerator` abstract base class and define how your domain processes YAML and renders templates.

## DomainGenerator Interface

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from jinja2 import Template

from embgen.models import BaseConfig


class DomainGenerator(ABC):
    """Abstract base class for domain generators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Domain name for CLI subcommand."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Help text for CLI."""
        ...

    @abstractmethod
    def detect(self, data: dict[str, Any]) -> bool:
        """Return True if this YAML belongs to this domain."""
        ...

    @abstractmethod
    def validate(self, data: dict[str, Any]) -> BaseConfig:
        """Parse and validate YAML into a config object."""
        ...

    @abstractmethod
    def render(self, config: Any, template: Template) -> str:
        """Render a config to a Jinja2 template."""
        ...

    @property
    def templates_path(self) -> Path:
        """Path to this domain's templates directory."""
        ...

    def post_generate(
        self, config: BaseConfig, output: Path, generated_extensions: set[str]
    ) -> list[str]:
        """Hook called after templates are rendered."""
        ...
```

## Implementing a Generator

### Basic Implementation

```python
# generator.py
"""Generator implementation for the protocol domain."""

from pathlib import Path
from typing import Any, cast

from jinja2 import Template

from embgen.domains import DomainGenerator
from embgen.models import BaseConfig
from .models import ProtocolConfig


class ProtocolGenerator(DomainGenerator):
    """Generator for protocol domain."""

    @property
    def name(self) -> str:
        return "protocol"

    @property
    def description(self) -> str:
        return "Generate code from protocol definitions"

    def detect(self, data: dict[str, Any]) -> bool:
        """Detect if YAML belongs to this domain."""
        # Check for characteristic keys
        return "messages" in data or data.get("domain") == "protocol"

    def validate(self, data: dict[str, Any]) -> BaseConfig:
        """Parse and validate YAML into config."""
        return cast(BaseConfig, ProtocolConfig.model_validate(data))

    def render(self, config: Any, template: Template) -> str:
        """Render config to a template."""
        cfg = config if isinstance(config, ProtocolConfig) else ProtocolConfig.model_validate(config)
        return template.render(config=cfg)

    @property
    def templates_path(self) -> Path:
        """Path to templates directory."""
        return Path(__file__).parent / "templates"
```

## Detection Logic

The `detect` method determines if a YAML file belongs to your domain. It's used by `embgen auto` for automatic domain detection.

### Simple Key Detection

```python
def detect(self, data: dict[str, Any]) -> bool:
    # Check for a required key
    return "messages" in data
```

### Multiple Key Detection

```python
def detect(self, data: dict[str, Any]) -> bool:
    # Must have messages, optionally with specific structure
    if "messages" not in data:
        return False
    
    # Check first message has expected structure
    messages = data.get("messages", [])
    if messages and isinstance(messages[0], dict):
        return "id" in messages[0] and "fields" in messages[0]
    
    return False
```

### Explicit Domain Key

```python
def detect(self, data: dict[str, Any]) -> bool:
    # Support explicit domain declaration
    if data.get("domain") == "protocol":
        return True
    
    # Fall back to structure detection
    return "messages" in data
```

## Validation

The `validate` method converts raw YAML data into a typed Pydantic model:

```python
def validate(self, data: dict[str, Any]) -> BaseConfig:
    """Parse and validate YAML into config."""
    try:
        return cast(BaseConfig, ProtocolConfig.model_validate(data))
    except ValidationError as e:
        # Optionally transform error for better messages
        raise
```

The returned config is passed to templates and post-generation hooks.

## Rendering

The `render` method passes data to Jinja2 templates:

### Passing the Whole Config

```python
def render(self, config: Any, template: Template) -> str:
    """Pass entire config to template."""
    cfg: ProtocolConfig = config
    return template.render(config=cfg)
```

Template usage:
```jinja
{% for msg in config.messages %}
#define MSG_{{ msg.name | upper }} {{ msg.id }}
{% endfor %}
```

### Passing Individual Variables

```python
def render(self, config: Any, template: Template) -> str:
    """Pass individual variables to template."""
    cfg: ProtocolConfig = config
    return template.render(
        name=cfg.name,
        version=cfg.version,
        messages=sorted(cfg.messages, key=lambda m: m.id),
        requests=cfg.requests,
        responses=cfg.responses,
    )
```

Template usage:
```jinja
// {{ name }} v{{ version }}
{% for msg in messages %}
...
{% endfor %}
```

### Adding Extra Context

```python
from datetime import datetime

def render(self, config: Any, template: Template) -> str:
    cfg: ProtocolConfig = config
    return template.render(
        config=cfg,
        generated_on=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        generator_version="1.0.0",
    )
```

## Post-Generation Hooks

The `post_generate` method runs after all templates are rendered. Use it to copy additional files:

```python
def post_generate(
    self, config: BaseConfig, output: Path, generated_extensions: set[str]
) -> list[str]:
    """Copy extra files after generation."""
    copied_files = []
    
    # Only copy when C header is generated
    if "h" in generated_extensions:
        # Copy utility header
        src = self.templates_path / "protocol_utils.h"
        if src.exists():
            dst = output / "protocol_utils.h"
            dst.write_text(src.read_text())
            copied_files.append("protocol_utils.h")
    
    # Only copy when Python is generated
    if "py" in generated_extensions:
        src = self.templates_path / "protocol_base.py"
        if src.exists():
            dst = output / f"{config.output_filename}_base.py"
            dst.write_text(src.read_text())
            copied_files.append(f"{config.output_filename}_base.py")
    
    return copied_files
```

### Static Files for Post-Generation

Place static files in your `templates/` directory:

```
protocol/
├── generator.py
├── models.py
└── templates/
    ├── template.h.j2
    ├── template.py.j2
    ├── protocol_utils.h      # Static file, copied as-is
    └── protocol_base.py      # Static file, copied as-is
```

## Complete Example

```python
# generator.py
"""Protocol domain generator."""

from datetime import datetime
from pathlib import Path
from typing import Any, cast

from jinja2 import Template

from embgen.domains import DomainGenerator
from embgen.models import BaseConfig
from .models import ProtocolConfig


class ProtocolGenerator(DomainGenerator):
    """Generator for protocol message definitions."""

    @property
    def name(self) -> str:
        return "protocol"

    @property
    def description(self) -> str:
        return "Generate code from protocol message definitions"

    def detect(self, data: dict[str, Any]) -> bool:
        """Detect protocol YAML by checking for messages key."""
        if data.get("domain") == "protocol":
            return True
        if "messages" not in data:
            return False
        # Verify message structure
        messages = data.get("messages", [])
        return bool(messages) and "id" in messages[0]

    def validate(self, data: dict[str, Any]) -> BaseConfig:
        """Validate YAML into ProtocolConfig."""
        return cast(BaseConfig, ProtocolConfig.model_validate(data))

    def render(self, config: Any, template: Template) -> str:
        """Render protocol config to template."""
        cfg = config if isinstance(config, ProtocolConfig) else ProtocolConfig.model_validate(config)
        
        # Sort messages by ID for consistent output
        messages = sorted(cfg.messages, key=lambda m: m.id)
        
        return template.render(
            name=cfg.name,
            namespace=cfg.namespace or cfg.name.lower(),
            version=cfg.version,
            messages=messages,
            requests=[m for m in messages if m.type.value == "request"],
            responses=[m for m in messages if m.type.value == "response"],
            generated_on=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    @property
    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"

    def post_generate(
        self, config: BaseConfig, output: Path, generated_extensions: set[str]
    ) -> list[str]:
        """Copy utility files."""
        copied = []
        
        if "h" in generated_extensions:
            for filename in ["protocol_utils.h", "protocol_types.h"]:
                src = self.templates_path / filename
                if src.exists():
                    (output / filename).write_text(src.read_text())
                    copied.append(filename)
        
        if "py" in generated_extensions:
            src = self.templates_path / "protocol_base.py"
            if src.exists():
                dst_name = f"{config.output_filename}_base.py"
                (output / dst_name).write_text(src.read_text())
                copied.append(dst_name)
        
        return copied
```
