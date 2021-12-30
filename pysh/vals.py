from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass
from typing import Mapping, MutableMapping, Optional, Sequence

from pysh import errors
from pysh import types


class Error(errors.Error):
    ...


class Val(ABC):
    @abstractproperty
    def type(self) -> types.Type: ...

    @abstractproperty
    def scope(self) -> 'Scope': ...


@dataclass
class Var:
    _type: types.Type
    _val: Val

    @property
    def type(self) -> types.Type:
        return self._type

    @property
    def val(self) -> Val:
        return self._val

    def check_assignable(self, val: Val) -> None:
        try:
            self._type.check_assignable(val.type)
        except types.Error as error:
            raise Error(f'{self} cannot assign val {val}: {error}')

    def set_val(self, val: Val) -> None:
        self.check_assignable(val)
        self._val = val


@dataclass
class Scope:
    _vars: MutableMapping[str, Var]
    _parent: Optional['Scope']

    def __contains__(self, name: str) -> bool:
        return name in self._vars or (self._parent is not None and name in self._parent)

    def __getitem__(self, name: str) -> Val:
        if name in self._vars:
            return self._vars[name].val
        elif self._parent is not None:
            return self._parent[name]
        else:
            raise Error(f'unknown var {name}')

    def __setitem__(self, name: str, val: Val) -> None:
        if name not in self._vars:
            raise Error(f'unknown var {name}')
        self._vars[name].set_val(val)

    @property
    def vars(self) -> Mapping[str, Var]:
        return self._vars

    @property
    def parent(self) -> Optional['Scope']:
        return self._parent

    def decl(self, name: str, var: Var) -> None:
        if name in self._vars:
            raise Error(f'duplicate var {name}')
        self._vars[name] = var

    @staticmethod
    def default() -> 'Scope':
        return Scope({
        }, None)


@dataclass(frozen=True)
class Arg:
    val: Val


@dataclass(frozen=True)
class Args:
    args: Sequence[Arg]

    def with_first_arg(self, arg: Val) -> 'Args':
        return Args([Arg(arg)] + list(self.args))


@dataclass(frozen=True)
class Param:
    name: str
    type: types.Type

    def check_assignable(self, arg: Arg) -> None:
        try:
            self.type.check_assignable(arg.val.type)
        except types.Error as error:
            raise Error(f'{self} cannot assign arg {arg}: {error}')


@dataclass(frozen=True)
class Params:
    params: Sequence[Param]

    def check_assignable(self, args: Args) -> None:
        if len(self.params) != len(args.args):
            raise Error(
                f'{self} expected {len(self.params)} args but got {len(args.args)}')
        for param, arg in zip(self.params, args.args):
            param.check_assignable(arg)

    def without_first_param(self) -> 'Params':
        return Params(self.params[1:])


class ISignature(ABC):
    @abstractmethod
    def check_args_assignable(self, args: Args) -> None: ...

    @abstractmethod
    def check_return_val_assignable(self, return_val: Val) -> None: ...

    @abstractmethod
    def without_first_param(self) -> 'ISignature': ...


@dataclass(frozen=True)
class Signature(ISignature):
    params: Params
    return_type: types.Type

    def check_args_assignable(self, args: Args) -> None:
        self.params.check_assignable(args)

    def check_return_val_assignable(self, return_val: Val) -> None:
        self.return_type.check_assignable(return_val.type)

    def without_first_param(self) -> 'ISignature':
        return Signature(self.params.without_first_param(), self.return_type)


@dataclass(frozen=True)
class Callable(Val, ABC):
    @abstractproperty
    def signature(self) -> ISignature: ...

    @abstractmethod
    def _call(self, scope: Scope, args: Args) -> Val: ...

    def call(self, scope: Scope, args: Args) -> Val:
        self.signature.check_args_assignable(args)
        return_val = self._call(scope, args)
        self.signature.check_return_val_assignable(return_val)
        return return_val


@dataclass(frozen=True)
class BoundCallable(Callable):
    bound_arg: Val
    func: Callable

    @property
    def signature(self) -> ISignature:
        return self.func.signature.without_first_param()

    @staticmethod
    def builtin_type() -> types.BuiltinType:
        return types.BuiltinType('bound_callable')

    @property
    def type(self) -> types.Type:
        return self.builtin_type()

    def _call(self, scope: Scope, args: Args) -> Val:
        return self.func.call(scope, args.with_first_arg(self.bound_arg))


@dataclass(frozen=True)
class BindableCallable(Callable):
    def bind(self, arg: Val) -> BoundCallable:
        return BoundCallable(arg, self)


@dataclass(frozen=True)
class Class(Callable, types.Type):
    _name: str
    parent: Optional['Class']
    _scope: Scope

    @staticmethod
    def builtin_type() -> types.BuiltinType:
        return types.BuiltinType('class')

    @property
    def type(self) -> types.Type:
        return self.builtin_type()

    @property
    def name(self) -> str:
        return self._name

    @property
    def scope(self) -> Scope:
        return self._scope

    def check_assignable(self, type: types.Type) -> None:
        if type != self:
            if self.parent is not None:
                self.parent.check_assignable(type)
            else:
                raise Error(f'{self} not assignable with type {type}')

    def _call(self, scope: Scope, args: Args) -> Val:
        object = Object(self, Scope({}, self._scope))
        for name, var in self._scope.vars.items():
            if isinstance(var, BindableCallable):
                bound_var = var.bind(object)
                object.scope.decl(name, Var(bound_var.type, bound_var))
        if '__init__' in object.scope:
            init = object.scope['__init__']
            if isinstance(init, Callable):
                init.call(scope, args)
        return object


@dataclass(frozen=True)
class Object(Val):
    class_: Class
    _scope: Scope

    @property
    def type(self) -> types.Type:
        return self.class_

    @property
    def scope(self) -> Scope:
        return self._scope
