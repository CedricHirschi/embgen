from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

from .common import StrictModel


class Schema(StrictModel):
    pass


SchemaT = TypeVar("SchemaT", bound=Schema)


class GeneratedFile(StrictModel):
    path: Path
    content: str | bytes


class Generator(ABC, Generic[SchemaT]):
    @abstractmethod
    def generate(self, input: SchemaT) -> list[GeneratedFile]: ...
