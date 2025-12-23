"""Models for the testing domain.

This module defines a comprehensive configuration that exercises many Pydantic features:
- Required and optional fields
- Nested models
- Lists of models
- Enums
- Validators
- Computed fields
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, computed_field, field_validator

from ...models import BaseConfig


class ItemType(StrEnum):
    """Type of test item."""

    SIMPLE = "simple"
    COMPLEX = "complex"
    NESTED = "nested"


class Tag(BaseModel):
    """A simple tag with name and optional value."""

    name: str
    value: int | None = None
    description: str | None = None


class NestedItem(BaseModel):
    """A nested item to test deep nesting."""

    id: int
    label: str
    tags: list[Tag] = Field(default_factory=list)


class Item(BaseModel):
    """A test item with various field types."""

    name: str
    item_type: ItemType = ItemType.SIMPLE
    value: int = 0
    enabled: bool = True
    description: str | None = None
    tags: list[Tag] = Field(default_factory=list)
    children: list[NestedItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not empty and lowercase it."""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @computed_field
    @property
    def name_upper(self) -> str:
        """Get uppercase version of name."""
        return self.name.upper()

    @computed_field
    @property
    def tag_count(self) -> int:
        """Get total number of tags including nested."""
        return len(self.tags) + sum(len(c.tags) for c in self.children)


class TestingConfig(BaseConfig):
    """Configuration for the testing domain.

    This exercises many config features:
    - Inherits from BaseConfig (name, file)
    - Has required and optional fields
    - Contains lists of complex objects
    - Has metadata dict
    """

    version: str = "1.0"
    description: str | None = None
    items: list[Item] = Field(default_factory=list)
    global_tags: list[Tag] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def item_count(self) -> int:
        """Total number of items."""
        return len(self.items)

    @computed_field
    @property
    def enabled_items(self) -> list[Item]:
        """Get only enabled items."""
        return [item for item in self.items if item.enabled]

    @computed_field
    @property
    def items_by_type(self) -> dict[str, list[Item]]:
        """Group items by type."""
        result: dict[str, list[Item]] = {}
        for item in self.items:
            key = item.item_type.value
            if key not in result:
                result[key] = []
            result[key].append(item)
        return result
