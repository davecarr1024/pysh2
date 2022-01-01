from dataclasses import dataclass
from abc import ABC, abstractmethod, abstractproperty
from typing import Mapping, Sequence

from pysh import errors


class Error(errors.Error):
    ...


class Type(ABC):
    @abstractproperty
    def name(self) -> str: ...

    @abstractproperty
    def member_types(self) -> Mapping[str, 'Type']: ...

    @abstractmethod
    def check_assignable(self, type: 'Type') -> None: ...


@dataclass(frozen=True)
class BuiltinType(Type):
    _name: str

    @property
    def name(self) -> str:
        return self._name

    @property
    def member_types(self) -> Mapping[str, Type]:
        return {}

    def check_assignable(self, type: 'Type') -> None:
        if type != self:
            raise Error(f'{self} cannot be assigned with type {type}')


@dataclass(frozen=True)
class Param:
    name: str
    type: Type

    def check_assignable(self, arg_type: Type) -> None:
        try:
            self.type.check_assignable(arg_type)
        except errors.Error as error:
            raise Error(f'{self} cannot assign type {arg_type}: {error}')


@dataclass(frozen=True)
class Params:
    params: Sequence[Param]

    def check_assignable(self, arg_types: Sequence[Type]) -> None:
        if len(self.params) != len(arg_types):
            raise Error(
                f'{self} expected {len(self.params)} args but got {len(arg_types)}')
        for param, arg_type in zip(self.params, arg_types):
            param.check_assignable(arg_type)

    def without_first_param(self) -> 'Params':
        return Params(self.params[1:])


@dataclass(frozen=True)
class Signature:
    params: Params
    return_type: Type

    def check_args_assignable(self, arg_types: Sequence[Type]) -> None:
        self.params.check_assignable(arg_types)

    def check_return_val_assignable(self, return_type: Type) -> None:
        self.return_type.check_assignable(return_type)

    def without_first_param(self) -> 'Signature':
        return Signature(self.params.without_first_param(), self.return_type)
