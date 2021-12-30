from dataclasses import dataclass
from abc import ABC, abstractmethod, abstractproperty

from pysh import errors


class Error(errors.Error):
    ...


class Type(ABC):
    @abstractproperty
    def name(self) -> str: ...

    @abstractmethod
    def check_assignable(self, type: 'Type') -> None: ...


@dataclass(frozen=True)
class BuiltinType(Type):
    _name: str

    @property
    def name(self) -> str:
        return self._name

    def check_assignable(self, type: 'Type') -> None:
        raise Error(f'{self} not assignable')
