# Writing Models

Models define the structure of your YAML configuration and provide validation. embgen uses [Pydantic](https://docs.pydantic.dev/) for data validation.

## Base Configuration

All domain configurations must ultimately provide:

- `name` — The human-readable name
- `output_filename` — The base filename for generated files

You can either extend `BaseConfig` or implement these yourself:

```python
from embgen.models import BaseConfig

class MyConfig(BaseConfig):
    """Configuration for my domain.
    
    Inherits:
        name: str
        file: str | None (optional output filename override)
        output_filename: property (returns file or lowercase name)
    """
    # Add your domain-specific fields
    items: list[str] = []
```

## Defining Models

### Basic Model

```python
# models.py
from typing import Optional
from pydantic import BaseModel
from embgen.models import BaseConfig

class MyConfig(BaseConfig):
    """Top-level configuration."""
    
    description: Optional[str] = None
    version: str = "1.0"
    items: list["Item"] = []

class Item(BaseModel):
    """An item in the configuration."""
    
    name: str
    value: int
    enabled: bool = True
```

This validates YAML like:

```yaml
name: MyProject
description: Example project
version: "2.0"
items:
  - name: foo
    value: 42
  - name: bar
    value: 100
    enabled: false
```

### Using Enums

```python
from enum import StrEnum
from pydantic import BaseModel

class ItemType(StrEnum):
    SIMPLE = "simple"
    COMPLEX = "complex"
    
class Item(BaseModel):
    name: str
    type: ItemType = ItemType.SIMPLE
```

YAML usage:

```yaml
items:
  - name: foo
    type: simple
  - name: bar
    type: complex
```

### Nested Enumerations

For enums that are defined in YAML (not code), use the shared `Enum` model:

```python
from embgen.models import Enum

class Item(BaseModel):
    name: str
    values: list[Enum] | None = None
```

YAML usage:

```yaml
items:
  - name: status
    values:
      - { name: OK, value: 0, description: "Success" }
      - { name: ERROR, value: 1, description: "Failure" }
```

## Validation

### Field Validators

Use Pydantic validators for custom validation logic:

```python
from pydantic import BaseModel, field_validator

class Item(BaseModel):
    name: str
    value: int
    
    @field_validator("value")
    @classmethod
    def value_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("value must be positive")
        return v
```

### Cross-Field Validation

```python
from pydantic import BaseModel, model_validator

class Config(BaseModel):
    min_value: int
    max_value: int
    
    @model_validator(mode="after")
    def check_range(self) -> "Config":
        if self.min_value >= self.max_value:
            raise ValueError("min_value must be less than max_value")
        return self
```

### Default Value Transformation

```python
from typing import Any
from pydantic import BaseModel, field_validator, ValidationInfo

class Argument(BaseModel):
    name: str
    default: int | str | None = None
    enums: list[Enum] | None = None
    
    @field_validator("default", mode="before")
    @classmethod
    def resolve_enum_default(cls, v: Any, info: ValidationInfo) -> Any:
        """Convert string default to Enum if enums are defined."""
        enums = info.data.get("enums")
        if enums and isinstance(v, str):
            for enum in enums:
                if enum.name == v:
                    return enum
        return v
```

## Computed Fields

Add properties that are computed from other fields:

```python
from pydantic import BaseModel, computed_field

class Argument(BaseModel):
    name: str
    type: str  # e.g., "B", "H", "I"
    
    @computed_field
    def type_size(self) -> int:
        """Get size in bytes for the type."""
        sizes = {"B": 1, "H": 2, "I": 4, "Q": 8}
        return sizes.get(self.type, 0)
    
    @computed_field
    def type_python(self) -> str:
        """Get Python type name."""
        types = {"B": "int", "H": "int", "f": "float", "?": "bool"}
        return types.get(self.type, "Any")
```

These computed fields are available in templates:

```jinja
{{ arg.name }}: {{ arg.type_python }}  # foo: int
```

## Complete Example

Here's a complete model for a protocol domain:

```python
# models.py
"""Data models for the protocol domain."""

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field, computed_field

from embgen.models import BaseConfig, Enum


class MessageType(StrEnum):
    """Message type enumeration."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class Field(BaseModel):
    """A field within a message."""
    
    name: str
    description: Optional[str] = None
    type: str  # e.g., "uint8", "uint16", "string"
    optional: bool = False
    enums: Optional[list[Enum]] = None
    
    @computed_field
    def c_type(self) -> str:
        """Get C type for this field."""
        type_map = {
            "uint8": "uint8_t",
            "uint16": "uint16_t", 
            "uint32": "uint32_t",
            "int8": "int8_t",
            "int16": "int16_t",
            "int32": "int32_t",
            "string": "char*",
            "bool": "bool",
        }
        return type_map.get(self.type, "void*")


class Message(BaseModel):
    """A protocol message."""
    
    name: str
    id: int
    type: MessageType = MessageType.REQUEST
    description: Optional[str] = None
    fields: list[Field] = Field(default_factory=list)


class ProtocolConfig(BaseConfig):
    """Top-level protocol configuration."""
    
    version: str = "1.0"
    namespace: Optional[str] = None
    messages: list[Message]
    
    @property
    def requests(self) -> list[Message]:
        """Get all request messages."""
        return [m for m in self.messages if m.type == MessageType.REQUEST]
    
    @property
    def responses(self) -> list[Message]:
        """Get all response messages."""
        return [m for m in self.messages if m.type == MessageType.RESPONSE]
```

Example YAML:

```yaml
name: MyProtocol
version: "2.0"
namespace: myproto

messages:
  - name: Connect
    id: 1
    type: request
    description: "Connect to the device"
    fields:
      - name: device_id
        type: uint32
        description: "Device identifier"
      - name: timeout_ms
        type: uint16
        optional: true
        
  - name: ConnectResponse
    id: 2
    type: response
    fields:
      - name: status
        type: uint8
        enums:
          - { name: OK, value: 0 }
          - { name: ERROR, value: 1 }
          - { name: TIMEOUT, value: 2 }
```
