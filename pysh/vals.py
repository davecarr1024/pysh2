from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass
import inspect
from typing import Iterable, Mapping, MutableMapping, Optional, TypeVar, final
import typing

from pysh import errors, types_


class Error(errors.Error):
    ...


class Val(types_.Val, ABC):
    def __post_init__(self):
        for name, type in self.member_types.items():
            if name not in self.members:
                raise Error(f'type member {name} missing from {self}')
            try:
                type.check_assignable(self.members[name].type)
            except errors.Error as error:
                raise Error(f'member {name} has invalid type: {error}')

    @property
    def signatures(self) -> types_.Signatures:
        return self.type.signatures

    @property
    def member_types(self) -> Mapping[str, types_.Type]:
        return self.type.member_types

    @abstractmethod
    def _call(self, scope: 'Scope', args: 'Args') -> 'Val': ...

    @final
    def call(self, scope: 'Scope', args: 'Args') -> 'Val':
        signature = self.signatures.for_args(args.types)
        val = self._call(scope, args)
        try:
            signature.check_return_assignable(val.type)
        except errors.Error as error:
            raise Error(
                f'{self} {signature} return invalid result {val}: {error}')
        return val

    @abstractproperty
    def members(self) -> 'Scope': ...


Var = types_.Var[Val]
MutableVar = types_.MutableVar[Val]
Scope = types_.Scope[Val]


class MutableScope(types_.MutableScope[Val]):
    ...


@dataclass(frozen=True)
class Arg:
    val: Val

    @property
    def type(self) -> types_.Type:
        return self.val.type


@dataclass(frozen=True)
class Args(list[Arg]):
    def __init__(self, args: Iterable[Arg]):
        super().__init__(args)

    def with_first_arg(self, arg: Arg) -> 'Args':
        return Args([arg] + self)

    @property
    def types(self) -> types_.Args:
        return types_.Args([types_.Arg(arg.type) for arg in self])


@dataclass(frozen=True)
class BoundCallable(Val):
    bound_arg: Val
    func: Val

    @property
    def signatures(self) -> types_.Signatures:
        return self.func.signatures.without_first_param()

    @staticmethod
    def builtin_type() -> types_.Builtin:
        return types_.Builtin('bound_callable')

    @property
    def type(self) -> types_.Type:
        return self.builtin_type()

    def _call(self, scope: Scope, args: Args) -> Val:
        return self.func.call(scope, args.with_first_arg(Arg(self.bound_arg)))


@dataclass(frozen=True)
class BindableCallable(Val):
    def bind(self, arg: Val) -> BoundCallable:
        return BoundCallable(arg, self)


@dataclass(frozen=True)
class Class(Val, types_.Type):
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
    def signatures(self) -> types_.Signatures:
        if '__init__' in self._scope:
            init = self._scope['init']
            if isinstance(init, BindableCallable):
                return init.signatures.without_first_param()
            else:
                return init.signatures
        else:
            return types_.Signatures([types_.Signature(types_.Params([]), self)])

    def check_assignable(self, type: types_.Type) -> None:
        if type != self:
            if self.parent is not None:
                self.parent.check_assignable(type)
            else:
                raise Error(f'{self} not assignable with type {type}')

    def _call(self, scope: Scope, args: Args) -> Val:
        object = Object(self, MutableScope(
            {'__type__': Var.for_val(self)}, self._scope))
        for name, val in self._scope.vals.items():
            if isinstance(val, BindableCallable):
                val = val.bind(object)
                object.members.decl(name, Var.for_val(val))
        if '__init__' in object.members:
            object.members['__init__'].call(scope, args)
        return object


@dataclass(frozen=True)
class Object(Val):
    class_: Class
    _scope: MutableScope

    @property
    def type(self) -> types_.Type:
        return self.class_

    @property
    def members(self) -> MutableScope:
        return self._scope

    def _call(self, scope: Scope, args: Args) -> Val:
        if '__call__' in self.members:
            return self.members['__call__'].call(scope, args)
        raise Error(f'{self} not callable')


@dataclass(frozen=True)
class BuiltinFunc(Val):
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


@dataclass(frozen=True)
class BuiltinClass(Val, types_.Type):
    cls: type['BuiltinObject']

    @property
    def type(self) -> types_.Type:
        return types_.Builtin('builtin_class')

    @property
    def name(self) -> str:
        return self.cls.__name__

    @property
    def signatures(self) -> types_.Signatures:
        # TODO check init and conversions
        return types_.Signatures([])

    @property
    def members(self) -> Scope:
        # TODO extract builtinfuncs
        return Scope({})

    @property
    def member_types(self) -> Mapping[str, types_.Type]:
        return self.members.all_types()

    def _call(self, scope: Scope, args: Args) -> Val:
        # TODO check init and conversions
        raise Error(f'{self} not callable')

    def check_assignable(self, type: types_.Type) -> None:
        # TODO check supertypes
        if self != type:
            raise Error(f'{self} not assignable with type {type}')


@dataclass(frozen=True)
class BuiltinObject(Val):
    @classmethod
    def builtin_class(cls) -> BuiltinClass:
        return _builtin_classes[cls]

    @property
    def type(self) -> types_.Type:
        return self.builtin_class()

    @property
    def members(self) -> Scope:
        # TODO bind bindables
        return Scope({}, self.builtin_class().members)

    def _call(self, scope: Scope, args: Args) -> Val:
        if '__call__' in self.members:
            return self.members['__call__'].call(scope, args)
        raise Error(f'{self} not callable')


_builtin_classes: MutableMapping[type, BuiltinClass] = {}
_builtin_class_types: MutableMapping[BuiltinClass, type] = {}

_BuiltinObjectType = TypeVar('_BuiltinObjectType', bound=type[BuiltinObject])


def register_builtin_class(cls: _BuiltinObjectType) -> _BuiltinObjectType:
    builtin_class = BuiltinClass(cls)
    _builtin_classes[cls] = builtin_class
    _builtin_class_types[builtin_class] = cls
    return cls


def builtin_class_for_type(type: typing.Type[typing.Any]) -> BuiltinClass:
    if type not in _builtin_classes:
        raise Error(f'{type} is not a builtin class')
    return _builtin_classes[type]


def builtin_classes() -> Mapping[type, BuiltinClass]:
    return _builtin_classes


@dataclass(frozen=True)
@register_builtin_class
class Bool(BuiltinObject):
    val: bool


@dataclass(frozen=True)
@register_builtin_class
class Int(BuiltinObject):
    val: int


@dataclass(frozen=True)
@register_builtin_class
class Str(BuiltinObject):
    val: str


def default_scope() -> Scope:
    return Scope({
        builtin_class.name: Var.for_val(builtin_class)
        for builtin_class in _builtin_classes.values()
    })
