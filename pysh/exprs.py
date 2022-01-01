from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

from pysh import errors, types_, vals


class Error(errors.Error):
    ...


@dataclass(frozen=True)
class Expr(types_.Val, ABC):
    scope: 'Scope'

    @abstractmethod
    def eval(self, scope: vals.Scope) -> vals.Val: ...

    def apply(self, scope: 'MutableScope') -> None: ...


Scope = types_.Scope[Expr]
MutableScope = types_.MutableScope[Expr]
Var = types_.Var[Expr]
MutableVar = types_.MutableVar[Expr]


@dataclass(frozen=True)
class Decl(Expr):
    _type: types_.Type
    name: str
    expr: Expr

    @property
    def type(self) -> types_.Type:
        return self._type

    def apply(self, scope: 'MutableScope') -> None:
        scope.decl(self.name, Var(self._type, self.expr))

    def eval(self, scope: vals.Scope) -> vals.Val:
        if not isinstance(scope, vals.MutableScope):
            raise Error(f'applying decl {self} to immutable scope')
        val = self.expr.eval(scope)
        scope.decl(self.name, vals.Var(self._type, val))
        return val


@dataclass(frozen=True)
class Literal(Expr):
    val: vals.Val

    @property
    def type(self) -> types_.Type:
        return self.val.type

    def eval(self, scope: vals.Scope) -> vals.Val:
        return self.val


@dataclass(frozen=True)
class Ref(Expr):
    name: str

    @property
    def type(self) -> types_.Type:
        return self.scope[self.name].type

    def eval(self, scope: vals.Scope) -> vals.Val:
        return self.scope[self.name].eval(scope)


@dataclass(frozen=True)
class Member(Expr):
    object: Expr
    name: str

    @property
    def type(self) -> types_.Type:
        return self.object.type.member_types[self.name]

    def eval(self, scope: vals.Scope) -> vals.Val:
        return self.object.eval(scope).members[self.name]


@dataclass(frozen=True)
class Args(list[Expr]):
    def __init__(self, exprs: Iterable[Expr]):
        super().__init__(exprs)

    @property
    def types(self) -> types_.Args:
        return types_.Args([types_.Arg(expr.type) for expr in self])

    def eval(self, scope: vals.Scope) -> vals.Args:
        return vals.Args([vals.Arg(expr.eval(scope)) for expr in self])


@dataclass(frozen=True)
class Call(Expr):
    func: Expr
    args: Args

    @property
    def signature(self) -> types_.Signature:
        return self.func.type.signatures.for_args(self.args.types)

    @property
    def type(self) -> types_.Type:
        return self.signature.return_type

    def eval(self, scope: vals.Scope) -> vals.Val:
        return self.func.eval(scope).call(scope, self.args.eval(scope))
