from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Generic, Iterable, Mapping, MutableMapping, Optional, TypeVar, final

from pysh import errors


class Error(errors.Error):
    ...


class Type(ABC):
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def signature(self) -> Optional['Signature']: ...

    @abstractmethod
    def member_types(self) -> Mapping[str, 'Type']: ...

    @abstractmethod
    def check_assignable(self, type: 'Type') -> None: ...


@dataclass(frozen=True)
class Builtin(Type):
    _name: str
    _member_types: Mapping[str, Type]
    _signature: Optional['Signature']

    def name(self) -> str:
        return self._name

    def signature(self) -> Optional['Signature']:
        return self._signature

    def member_types(self) -> Mapping[str, Type]:
        return self._member_types

    def check_assignable(self, type: 'Type') -> None:
        if type != self:
            raise Error(f'{self} cannot be assigned with type {type}')


@dataclass(frozen=True)
class Arg:
    type: Type


class Args(list[Arg]):
    def __init__(self, args: Iterable[Arg]):
        super().__init__(args)


@dataclass(frozen=True)
class Param:
    name: str
    type: Type

    def check_assignable(self, arg: Arg) -> None:
        try:
            self.type.check_assignable(arg.type)
        except errors.Error as error:
            raise Error(f'param {self} cannot assign arg {arg}: {error}')


class Params(list[Param]):
    def __init__(self, params: Iterable[Param]):
        super().__init__(params)

    def check_assignable(self, args: Args) -> None:
        if len(self) != len(args):
            raise Error(
                f'{self} expected {len(self)} args but got {len(args)}')
        for param, arg in zip(self, args):
            param.check_assignable(arg)

    def without_first_param(self) -> 'Params':
        if len(self) == 0:
            raise Error(f'{self} unable to remove first param: empty')
        return Params(self[1:])


@dataclass(frozen=True)
class Signature:
    params: Params
    return_type: Type

    def check_args_assignable(self, args: Args) -> None:
        self.params.check_assignable(args)

    def check_return_assignable(self, return_type: Type) -> None:
        self.return_type.check_assignable(return_type)

    def without_first_param(self) -> 'Signature':
        return Signature(self.params.without_first_param(), self.return_type)


@dataclass
class Var(ABC):
    __type: Type

    @final
    def type(self) -> Type:
        return self.__type


_VarType = TypeVar('_VarType', bound=Var)


@dataclass(frozen=True)
class Scope(Generic[_VarType]):
    _vars: MutableMapping[str, _VarType]
    parent: Optional['Scope[_VarType]'] = field(default=None)

    @final
    def __contains__(self, name: str) -> bool:
        return name in self._vars or (self.parent is not None and name in self.parent)

    @final
    def var(self, name: str) -> _VarType:
        if name in self._vars:
            return self._vars[name]
        elif self.parent is not None:
            return self.parent.var(name)
        else:
            raise Error(f'unknown var {name}')

    @final
    def vars(self) -> Mapping[str, _VarType]:
        return self._vars

    @final
    def types(self) -> Mapping[str, Type]:
        return {name: var.type() for name, var in self.vars().items()}

    @final
    def all_vars(self) -> Mapping[str, _VarType]:
        vars = dict[str, _VarType]()
        if self.parent is not None:
            vars.update(self.parent.all_vars())
        vars.update(self.vars())
        return vars

    @final
    def all_types(self) -> Mapping[str, Type]:
        return {name: var.type() for name, var in self.all_vars().items()}


@dataclass(frozen=True)
class MutableScope(Scope[_VarType]):
    @final
    def set_var(self, name: str, var: _VarType) -> None:
        if name in self._vars:
            raise Error(f'duplicate var {name}')
        else:
            self._vars[name] = var
