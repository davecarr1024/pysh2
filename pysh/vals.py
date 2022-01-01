from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass
from functools import cached_property
import inspect
from typing import Mapping, MutableMapping, Optional, Sequence, TypeVar
import typing

from pysh import errors, types_


class Error(errors.Error):
    ...


class Val(ABC):
    @abstractproperty
    def type(self) -> types_.Type: ...


@dataclass
class Var:
    _type: types_.Type
    _val: Val

    def __post_init__(self):
        try:
            self._type.check_assignable(self._val.type)
        except errors.Error as error:
            raise Error(
                f'unable to set var with type {self._type} val {self._val}: {error}')

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
        try:
            self.check_assignable(val)
        except errors.Error as error:
            raise Error(
                f'unable to set var with type {self._type} val {val}: {error}')
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
    def vals(self) -> Mapping[str, Val]:
        return {name: var.val for name, var in self._vars.items()}

    def all_vals(self) -> Mapping[str, Val]:
        vals = dict[str, Val]()
        if self.parent is not None:
            vals.update(self.parent.all_vals())
        vals.update(self.vals)
        return vals

    def all_types(self) -> Mapping[str, types_.Type]:
        return {name: val.type for name, val in self.all_vals().items()}

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
    def types(self) -> types_.Args:
        return types_.Args([types_.Arg(arg.type) for arg in self.args])


@dataclass(frozen=True)
class Callable(Val, ABC):
    @abstractproperty
    def signature(self) -> types_.Signature: ...

    @abstractmethod
    def _call(self, scope: Scope, args: Args) -> Val: ...

    def call(self, scope: Scope, args: Args) -> Val:
        self.signature.check_args_assignable(args.types)
        return_val = self._call(scope, args)
        self.signature.check_return_assignable(return_val.type)
        return return_val


@dataclass(frozen=True)
class BoundCallable(Callable):
    bound_arg: Val
    func: Callable

    @property
    def signature(self) -> types_.Signature:
        return self.func.signature.without_first_param()

    @staticmethod
    def builtin_type() -> types_.Builtin:
        return types_.Builtin('bound_callable')

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
    def builtin_type() -> types_.Builtin:
        return types_.Builtin('class')

    @property
    def type(self) -> types_.Type:
        return self.builtin_type()

    @property
    def name(self) -> str:
        return self._name

    @property
    def member_types(self) -> Mapping[str, types_.Type]:
        return self.members.all_types()

    @property
    def members(self) -> Scope:
        return self._scope

    @property
    def signature(self) -> types_.Signature:
        if '__init__' in self._scope:
            init = self._scope['init']
            if isinstance(init, BindableCallable):
                return init.signature.without_first_param()
            elif isinstance(init, Callable):
                return init.signature
            else:
                raise Error(f'ucallable init {init}')
        else:
            return types_.Signature(types_.Params([]), self)

    def check_assignable(self, type: types_.Type) -> None:
        if type != self:
            if self.parent is not None:
                self.parent.check_assignable(type)
            else:
                raise Error(f'{self} not assignable with type {type}')

    def _call(self, scope: Scope, args: Args) -> Val:
        object = Object(self, Scope(
            {'__type__': Var.for_val(self)}, self._scope))
        for name, val in self._scope.vals.items():
            if isinstance(val, BindableCallable):
                val = val.bind(object)
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


@dataclass(frozen=True)
class BuiltinFunc(Callable):
    func: typing.Callable[..., Val]

    def __post_init__(self):
        self.check_assignable(self.func)

    @staticmethod
    def builtin_type() -> types_.Builtin:
        return types_.Builtin('builtin_func')

    @property
    def type(self) -> types_.Type:
        return self.builtin_type()

    @property
    def members(self) -> Scope:
        return Scope({})

    @staticmethod
    def check_assignable(func: typing.Callable[..., typing.Any]) -> None:
        func_sig = inspect.signature(func)
        for param in func_sig.parameters.values():
            if param.annotation not in _builtin_classes:
                raise Error(f'{func} has invalid param {param}')
        if func_sig.return_annotation not in _builtin_classes:
            raise Error(
                f'{func} has invalid return type {func_sig.return_annotation}')

    @staticmethod
    def is_assignable(func: typing.Callable[..., typing.Any]) -> bool:
        try:
            BuiltinFunc.check_assignable(func)
            return True
        except Error:
            return False

    @property
    def signature(self) -> types_.Signature:
        try:
            func_sig = inspect.signature(self.func)
            return types_.Signature(
                types_.Params(
                    [types_.Param(name, builtin_class_for_type(param.annotation))
                     for name, param in func_sig.parameters.items()]
                ),
                builtin_class_for_type(func_sig.return_annotation)
            )
        except Error as error:
            raise Error(f'{self} failed to convert signature: {error}')

    def _call(self, scope: Scope, args: Args) -> Val:
        raise NotImplementedError()


@dataclass(frozen=True)
class BindableBuiltinFunc(BuiltinFunc, BindableCallable):
    ...


_builtin_classes: MutableMapping[type, Class] = {}


@dataclass(frozen=True)
class BuiltinClass(Val):
    @classmethod
    def builtin_class(cls) -> Class:
        return builtin_class_for_type(cls)

    @property
    def type(self) -> types_.Type:
        return self.builtin_class()


_BuiltinClassType = TypeVar('_BuiltinClassType', bound=type[BuiltinClass])


def register_builtin_class(cls: _BuiltinClassType) -> _BuiltinClassType:
    _builtin_classes[cls] = Class(cls.__name__,
                                  None,
                                  Scope({}))
    return cls


def builtin_class_for_type(type: typing.Type[typing.Any]) -> Class:
    if type not in _builtin_classes:
        raise Error(f'{type} is not a builtin class')
    return _builtin_classes[type]


def builtin_classes() -> Mapping[type, Class]:
    return _builtin_classes


@dataclass(frozen=True)
@register_builtin_class
class Bool(BuiltinClass):
    val: bool


@dataclass(frozen=True)
@register_builtin_class
class Int(BuiltinClass):
    val: int


@dataclass(frozen=True)
@register_builtin_class
class Str(BuiltinClass):
    val: str
