from abc import ABC, abstractmethod
from dataclasses import dataclass
import inspect
from typing import Iterable, Mapping, MutableMapping, Optional, Sequence, TypeVar, final
import typing

from pysh import errors, types_


class Error(errors.Error):
    ...


class Val(ABC):
    def __post_init__(self):
        for name, type in self.member_types().items():
            if name not in self.members():
                raise Error(f'type member {name} missing from {self}')
            try:
                type.check_assignable(self.members().val(name).type())
            except errors.Error as error:
                raise Error(f'member {name} has invalid type: {error}')

    @abstractmethod
    def type(self) -> types_.Type: ...

    @abstractmethod
    def _call(self, scope: 'Scope', args: 'Args') -> 'Val': ...

    @abstractmethod
    def members(self) -> 'Scope': ...

    def can_bind(self) -> bool:
        return False

    def bind(self, arg: 'Val') -> 'Val':
        raise Error('unbindable')

    @final
    def signature(self) -> Optional[types_.Signature]:
        return self.type().signature()

    @final
    def bound_signature(self) -> types_.Signature:
        if not self.can_bind():
            raise Error('unbindable')
        signature = self.signature()
        if signature is None:
            raise Error(f'unable to bind uncallable {self}')
        return signature.without_first_param()

    @final
    def member_types(self) -> Mapping[str, types_.Type]:
        return self.type().member_types()

    @final
    def call(self, scope: 'Scope', args: 'Args') -> 'Val':
        signature = self.signature()
        if signature is None:
            raise Error(f'{self} not callable')
        try:
            signature.check_args_assignable(args.types())
        except errors.Error as error:
            raise Error(
                f'failed to find signature for {self} args {args}: {error}')
        try:
            val = self._call(scope, args)
        except errors.Error as error:
            raise Error(
                f'failed to call {self} with args {args} and sig {signature}: {error}')
        try:
            signature.check_return_assignable(val.type())
        except errors.Error as error:
            raise Error(
                f'{self} returned invalid result {val}: {error}')
        return val


@dataclass
class Var(types_.Var):
    _val: Optional[Val]

    def __post_init__(self):
        if self._val is not None:
            try:
                self.type().check_assignable(self._val.type())
            except Error as error:
                raise Error(f'{self} has incompatible val: {error}')

    def val(self) -> Val:
        if self._val is None:
            raise Error(f'getting val from uninitialized var {self}')
        return self._val

    def check_assignable(self, val: Val) -> None:
        try:
            self.type().check_assignable(val.type())
        except Error as error:
            raise Error(f'{self} unable to be set with val {val}: {error}')

    def initialized(self) -> bool:
        return self._val is not None

    def with_val(self, val: Val) -> 'Var':
        self.check_assignable(val)
        return Var(self.type(), val)

    @staticmethod
    def for_val(val: Val) -> 'Var':
        return Var(val.type(), val)


@dataclass
class MutableVar(Var):
    def set_val(self, val: Val) -> None:
        self.check_assignable(val)
        self._val = val

    def with_val(self, val: Val) -> 'Var':
        self.check_assignable(val)
        return MutableVar(self.type(), val)


class Scope(types_.Scope[Var]):
    def val(self, name: str) -> Val:
        return self.var(name).val()


class MutableScope(Scope, types_.MutableScope[Var]):
    def set_val(self, name: str, val: Val) -> None:
        if not name in self.vars():
            raise Error(f'setting unknown var {name}')
        var = self.vars()[name]
        if not isinstance(var, MutableVar):
            raise Error(f'setting immutable var {name}')
        try:
            var.set_val(val)
        except Error as error:
            raise Error(f'failed to set var {name}: {error}')


@dataclass(frozen=True)
class Arg:
    val: Val

    def type(self) -> types_.Type:
        return self.val.type()


@dataclass(frozen=True)
class Args(list[Arg]):
    def __init__(self, args: Iterable[Arg]):
        super().__init__(args)

    def with_first_arg(self, arg: Arg) -> 'Args':
        return Args([arg] + self)

    def types(self) -> types_.Args:
        return types_.Args([types_.Arg(arg.type()) for arg in self])

    def vals(self) -> Sequence[Val]:
        return [arg.val for arg in self]


@dataclass(frozen=True)
class BindableCallable(Val):
    def can_bind(self) -> bool:
        return True

    def bind(self, arg: Val) -> Val:
        return BoundCallable(self, arg)


@dataclass(frozen=True)
class BoundCallable(Val):
    func: BindableCallable
    arg: Val

    def type(self) -> types_.Type:
        signature = self.func.signature()
        if signature is None:
            raise Error('func is not callable')
        return types_.Builtin(
            'bound_callable',
            self.func.member_types(),
            signature.without_first_param()
        )

    def members(self) -> Scope:
        return self.func.members()

    def _call(self, scope: Scope, args: Args) -> Val:
        return self.func.call(scope, args.with_first_arg(Arg(self.arg)))


@dataclass(frozen=True)
class Class(Val, types_.Type):
    _name: str
    parent: Optional['Class']
    static_scope: Scope
    object_scope: Scope

    def __post_init__(self) -> None:
        if '__init__' in self.static_scope:
            init = self.static_scope.val('__init__')
            if init.signature is None or not init.can_bind():
                raise Error(f'invalid init {init}')

    def type(self) -> types_.Type:
        return types_.Builtin('class',
                              self.static_scope.all_types(),
                              self._init_signature())

    def _init_signature(self) -> Optional[types_.Signature]:
        if '__init__' in self.static_scope:
            return self.static_scope.val('__init__').bound_signature()
        return types_.Signature(types_.Params([]), self)

    def name(self) -> str:
        return self._name

    def members(self) -> Scope:
        return self.static_scope

    def check_assignable(self, type: types_.Type) -> None:
        if type != self:
            if self.parent is not None:
                self.parent.check_assignable(type)
            else:
                raise Error(f'{self} not assignable with type {type}')

    def _call(self, scope: Scope, args: Args) -> Val:
        return Object(self, scope, args)


@dataclass(frozen=True, init=False)
class Object(Val):
    class_: Class
    _scope: Scope

    def __init__(self, class_: Class, scope: Scope, args: Args):
        self.__dict__['class_'] = class_
        self.__dict__['_scope'] = Scope(
            {
                name: var.with_val(var.val().bind(self))
                for name, var in class_.object_scope.vars().items()
            }, parent=class_.members())
        if '__init__' in self.members():
            self.members().val('__init__').call(scope, args)

    def type(self) -> types_.Type:
        return self.class_

    def members(self) -> Scope:
        return self._scope

    def _call(self, scope: Scope, args: Args) -> Val:
        if '__call__' in self.members():
            return self.members().val('__call__').call(scope, args)
        raise Error(f'{self} not callable')


@dataclass(frozen=True)
class BuiltinFunc(Val):
    func: typing.Callable[..., Val]

    def __post_init__(self):
        self.check_assignable(self.func)

    def type(self) -> types_.Type:
        return types_.Builtin('builtin_func', {}, self._signature())

    def members(self) -> Scope:
        return Scope({})

    def _signature(self) -> types_.Signature:
        func_sig = inspect.signature(self.func)
        return types_.Signature(
            types_.Params(
                [types_.Param(name, builtin_class_for_type(param.annotation))
                 for name, param in func_sig.parameters.items()]
            ),
            builtin_class_for_type(func_sig.return_annotation)
        )

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

    def _call(self, scope: Scope, args: Args) -> Val:
        return self.func(*args.vals())


@dataclass(frozen=True)
class BindableBuiltinFunc(BuiltinFunc, BindableCallable):
    ...


@dataclass(frozen=True)
class BuiltinClass(Val, types_.Type):
    cls: type['BuiltinObject']

    def type(self) -> types_.Type:
        return types_.Builtin('builtin_class', self.members().all_types(), None)

    def name(self) -> str:
        return self.cls.__name__

    def members(self) -> Scope:
        # TODO extract builtinfuncs
        return Scope({})

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

    def type(self) -> types_.Type:
        return self.builtin_class()

    def members(self) -> Scope:
        # TODO bind bindables
        return Scope({}, self.builtin_class().members())

    def _call(self, scope: Scope, args: Args) -> Val:
        if '__call__' in self.members():
            return self.members().val('__call__').call(scope, args)
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
        builtin_class.name(): Var.for_val(builtin_class)
        for builtin_class in _builtin_classes.values()
    })
