from abc import ABC, abstractmethod

from .common import StrictModel


class Generator(ABC):
    @abstractmethod
    def generate(self, input: str) -> str: ...


class Schema(StrictModel):
    pass
