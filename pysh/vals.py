from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass
from functools import cached_property
from typing import Mapping, MutableMapping, Optional, Sequence

from pysh import errors, types_


class Error(errors.Error):
    ...


class Val(ABC):
    @abstractproperty
    def type(self) -> types_.Type: ...

    @abstractproperty
    def members(self) -> 'Scope': ...


@dataclass
class Var:
    _type: types_.Type
    _val: Val

    @property
    def type(self) -> types_.Type:
        return self._type

    @property
    def val(self) -> Val:
        return self._val

    def check_assignable(self, val: Val) -> None:
        try:
            self._type.check_assignable(val.type)
        except errors.Error as error:
            raise Error(f'{self} cannot assign val {val}: {error}')

    def set_val(self, val: Val) -> None:
        self.check_assignable(val)
        self._val = val

    @staticmethod
    def for_val(val: Val) -> 'Var':
        return Var(val.type, val)


@dataclass(frozen=True)
class Scope:
    _vars: MutableMapping[str, Var]
    parent: Optional['Scope'] = None

    def __contains__(self, name: str) -> bool:
        return name in self._vars or (self.parent is not None and name in self.parent)

    def __getitem__(self, name: str) -> Val:
        if name in self._vars:
            return self._vars[name].val
        elif self.parent is not None:
            return self.parent[name]
        else:
            raise Error(f'unknown var {name}')

    def __setitem__(self, name: str, val: Val) -> None:
        if name in self._vars:
            try:
                self._vars[name].set_val(val)
            except errors.Error as error:
                raise Error(
                    f'unable to set {name} {self._vars[name]} to incompatible val {val}: {error}')
        elif self.parent is not None:
            self.parent[name] = val
        else:
            raise Error(f'unknown var {name}')

    @property
    def vars(self) -> Mapping[str, Var]:
        return self._vars

    def all_vars(self) -> Mapping[str, Var]:
        vars = MutableMapping[str, Var]()
        if self.parent is not None:
            vars.update(self.parent.all_vars())
        vars.update(self._vars)
        return vars

    def all_types(self) -> Mapping[str, types_.Type]:
        return {name: var.type for name, var in self.all_vars().items()}

    def decl(self, name: str, var: Var) -> None:
        if name in self._vars:
            raise Error(f'duplicate var {name}')
        self._vars[name] = var

    @staticmethod
    def default() -> 'Scope':
        return Scope({
        }, None)


@dataclass(frozen=True)
class Args:
    args: Sequence[Val]

    def with_first_arg(self, arg: Val) -> 'Args':
        return Args([arg] + list(self.args))

    @cached_property
    def types(self) -> Sequence[types_.Type]:
        return [arg.type for arg in self.args]


@dataclass(frozen=True)
class Callable(Val, ABC):
    @abstractproperty
    def signature(self) -> types_.Signature: ...

    @abstractmethod
    def _call(self, scope: Scope, args: Args) -> Val: ...

    def call(self, scope: Scope, args: Args) -> Val:
        self.signature.check_args_assignable(args.types)
        return_val = self._call(scope, args)
        self.signature.check_return_val_assignable(return_val.type)
        return return_val


@dataclass(frozen=True)
class BoundCallable(Callable):
    bound_arg: Val
    func: Callable

    @property
    def signature(self) -> types_.Signature:
        return self.func.signature.without_first_param()

    @staticmethod
    def builtin_type() -> types_.BuiltinType:
        return types_.BuiltinType('bound_callable')

    @property
    def type(self) -> types_.Type:
        return self.builtin_type()

    def _call(self, scope: Scope, args: Args) -> Val:
        return self.func.call(scope, args.with_first_arg(self.bound_arg))


@dataclass(frozen=True)
class BindableCallable(Callable):
    def bind(self, arg: Val) -> BoundCallable:
        return BoundCallable(arg, self)


@dataclass(frozen=True)
class Class(Callable, types_.Type):
    _name: str
    parent: Optional['Class']
    _scope: Scope

    @staticmethod
    def builtin_type() -> types_.BuiltinType:
        return types_.BuiltinType('class')

    @property
    def type(self) -> types_.Type:
        return self.builtin_type()

    @property
    def name(self) -> str:
        return self._name

    @property
    def member_types(self) -> Mapping[str, types_.Type]:
        return self._scope.all_types()

    @property
    def members(self) -> Scope:
        return self._scope

    def check_assignable(self, type: types_.Type) -> None:
        if type != self:
            if self.parent is not None:
                self.parent.check_assignable(type)
            else:
                raise Error(f'{self} not assignable with type {type}')

    def _call(self, scope: Scope, args: Args) -> Val:
        object = Object(self, Scope(
            {'__type__': Var.for_val(self)}, self._scope))
        for name, var in self._scope.vars.items():
            if isinstance(var, BindableCallable):
                val = var.bind(object)
                object.members.decl(name, Var.for_val(val))
        if '__init__' in object.members:
            init = object.members['__init__']
            if not isinstance(init, Callable):
                raise Error(f'object {object} __init__ {init} not callable')
            init.call(scope, args)
        return object


@dataclass(frozen=True)
class Object(Val):
    class_: Class
    _scope: Scope

    @property
    def type(self) -> types_.Type:
        return self.class_

    @property
    def members(self) -> Scope:
        return self._scope
