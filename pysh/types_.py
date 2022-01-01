from dataclasses import dataclass
from abc import ABC, abstractmethod, abstractproperty
from typing import Generic, Iterable, Mapping, MutableMapping, Optional, TypeVar

from pysh import errors


class Error(errors.Error):
    ...


class Type(ABC):
    @abstractproperty
    def name(self) -> str: ...

    @abstractmethod
    def check_assignable(self, type: 'Type') -> None: ...

    @abstractproperty
    def signatures(self) -> 'Signatures': ...

    @abstractproperty
    def member_types(self) -> Mapping[str, 'Type']: ...


@dataclass(frozen=True)
class Builtin(Type):
    _name: str

    @property
    def name(self) -> str:
        return self._name

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


class Signatures(list[Signature]):
    def __init__(self, signatures: Iterable[Signature]):
        super().__init__(signatures)

    def for_args(self, args: Args) -> Signature:
        if len(self) == 0:
            raise Error(f'not callable')
        errors = list[Error]()
        signatures = list[Signature]()
        for signature in self:
            try:
                signature.check_args_assignable(args)
                signatures.append(signature)
            except Error as error:
                errors.append(error)
        if len(signatures) > 1:
            raise Error(f'ambiguous call: {signatures}')
        elif len(signatures) == 1:
            return signatures[0]
        else:
            raise Error(f'no signatures matched: {errors}')

    def without_first_param(self) -> 'Signatures':
        return Signatures(signature.without_first_param() for signature in self)


class Val(ABC):
    @abstractproperty
    def type(self) -> Type: ...


_ValType = TypeVar('_ValType', bound=Val)


@dataclass
class Var(Generic[_ValType]):
    _type: Type
    _val: _ValType

    def __post_init__(self):
        try:
            self._type.check_assignable(self._val.type)
        except Error as error:
            raise Error(f'{self} has incompatible val: {error}')

    @property
    def type(self) -> Type:
        return self._type

    @property
    def val(self) -> _ValType:
        return self._val

    @val.setter
    def val(self, val: _ValType) -> None:
        raise Error(f'unable to set {self} with {val}: immutable')

    def check_assignable(self, val: _ValType) -> None:
        try:
            self._type.check_assignable(val.type)
        except Error as error:
            raise Error(f'{self} unable to be set with val {val}: {error}')

    @staticmethod
    def for_val(val: _ValType) -> 'Var[_ValType]':
        return Var[_ValType](val.type, val)


@dataclass
class MutableVar(Var[_ValType]):
    @property
    def val(self) -> _ValType:
        return self._val

    @val.setter
    def val(self, val: _ValType) -> None:
        self.check_assignable(val)
        self._val = val

    @staticmethod
    def for_val(val: _ValType) -> 'MutableVar[_ValType]':
        return MutableVar[_ValType](val.type, val)


@dataclass(frozen=True)
class Scope(Generic[_ValType]):
    _vars: MutableMapping[str, Var[_ValType]]
    parent: Optional['Scope[_ValType]'] = None

    def __contains__(self, name: str) -> bool:
        return name in self._vars or (self.parent is not None and name in self.parent)

    def __getitem__(self, name: str) -> _ValType:
        if name in self._vars:
            return self._vars[name].val
        elif self.parent is not None:
            return self.parent[name]
        else:
            raise Error(f'unknown var {name}')

    @property
    def vars(self) -> Mapping[str, Var[_ValType]]:
        return self._vars

    @property
    def vals(self) -> Mapping[str, _ValType]:
        return {name: var.val for name, var in self._vars.items()}

    def all_vals(self) -> Mapping[str, _ValType]:
        vals = dict[str, _ValType]()
        if self.parent is not None:
            vals.update(self.parent.all_vals())
        vals.update(self.vals)
        return vals

    def all_types(self) -> Mapping[str, Type]:
        return {name: val.type for name, val in self.all_vals().items()}


@dataclass(frozen=True)
class MutableScope(Scope[_ValType]):
    def __setitem__(self, name: str, val: _ValType) -> None:
        if name in self._vars:
            try:
                self._vars[name].val = val
            except Error as error:
                raise Error(f'unable to set {name} to val {val}: {error}')
        elif isinstance(self.parent, MutableScope):
            self.parent[name] = val
        else:
            raise Error(f'unknown var {name}')

    def decl(self, name: str, var: Var[_ValType]) -> None:
        if name in self._vars:
            raise Error(f'duplicate var {name}')
        self._vars[name] = var
