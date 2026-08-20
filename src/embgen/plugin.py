from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .common import StrictModel


class Schema(StrictModel):
    pass


SchemaT = TypeVar("SchemaT", bound=Schema)


class Generator(ABC, Generic[SchemaT]):
    @abstractmethod
    def generate(self, input: SchemaT) -> str: ...
