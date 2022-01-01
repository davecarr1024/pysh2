from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass
from typing import Mapping, MutableMapping, Optional, Sequence

from pysh import errors, types_, vals


class Error(errors.Error):
    ...


class Expr(ABC):
    @abstractmethod
    def type(self, scope: 'Scope') -> types_.Type: ...

    @abstractmethod
    def eval(self, scope: vals.Scope) -> vals.Val: ...


@dataclass
class Var:
    _type: types_.Type
    _expr: Expr

    @property
    def type(self) -> types_.Type:
        return self._type

    @property
    def expr(self) -> Expr:
        return self._expr

    def set_expr(self, scope: 'Scope', expr: Expr) -> None:
        self._type.check_assignable(expr.type(scope))
        self._expr = expr


@dataclass(frozen=True)
class Scope:
    _vars: MutableMapping[str, Var]
    parent: Optional['Scope'] = None

    def __contains__(self, name: str) -> bool:
        return name in self._vars or (self.parent is not None and name in self.parent)

    def __getitem__(self, name: str) -> Expr:
        if name in self._vars:
            return self._vars[name].expr
        elif self.parent is not None:
            return self.parent[name]
        else:
            raise Error(f'unknown expr {name}')

    def __setitem__(self, name: str, expr: Expr) -> None:
        if name in self._vars:
            self._vars[name].set_expr(self, expr)
        elif self.parent is not None:
            self.parent[name] = expr
        else:
            raise Error(f'unknown expr {name}')

    @property
    def vars(self) -> Mapping[str, Var]:
        return self._vars

    def decl(self, name: str, var: Var) -> None:
        if name in self._vars:
            raise Error(f'duplicate expr {name}')
        self._vars[name] = var


@dataclass(frozen=True)
class Decl(Expr):
    _type: types_.Type
    name: str
    expr: Expr

    def type(self, scope: Scope) -> types_.Type:
        scope.decl(self.name, Var(self._type, self.expr))
        return self._type

    def eval(self, scope: vals.Scope) -> vals.Val:
        val = self.expr.eval(scope)
        scope.decl(self.name, vals.Var(self._type, val))
        return val


@dataclass(frozen=True)
class Literal(Expr):
    val: vals.Val

    def type(self, scope: Scope) -> types_.Type:
        return self.val.type

    def eval(self, scope: vals.Scope) -> vals.Val:
        return self.val


@dataclass(frozen=True)
class Ref(Expr):
    name: str

    def type(self, scope: Scope) -> types_.Type:
        return scope[self.name].type(scope)

    def eval(self, scope: vals.Scope) -> vals.Val:
        return scope[self.name]


@dataclass(frozen=True)
class Member(Expr):
    parent: Expr
    name: str

    def type(self, scope: Scope) -> types_.Type:
        if self.name not in self.parent.type(scope).member_types:
            raise Error(f'unknown member {self.name} in {self.parent}')
        else:
            return self.parent.type(scope).member_types[self.name]

    def eval(self, scope: vals.Scope) -> vals.Val:
        return self.parent.eval(scope).members[self.name]


@dataclass(frozen=True)
class Args:
    args: Sequence[Expr]

    def types(self, scope: Scope) -> Sequence[types_.Type]:
        return [arg.type(scope) for arg in self.args]

    def eval(self, scope: vals.Scope) -> vals.Args:
        return vals.Args([arg.eval(scope) for arg in self.args])


@dataclass(frozen=True)
class Callable(Expr):
    @abstractproperty
    def signature(self) -> types_.Signature: ...


@dataclass(frozen=True)
class Call(Expr):
    func: Callable
    args: Args

    def type(self, scope: Scope) -> types_.Type:
        self.func.signature.check_args_assignable(self.args.types(scope))
        return self.func.signature.return_type

    def eval(self, scope: vals.Scope) -> vals.Val:
        func = self.func.eval(scope)
        if not isinstance(func, vals.Callable):
            raise Error(f'{func} not callable')
        return func.call(scope, self.args.eval(scope))
