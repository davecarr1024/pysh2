from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

from pysh import errors, types_, vals


class Error(errors.Error):
    ...


class Var(types_.Var):
    ...


class Scope(types_.Scope[Var]):
    ...


class MutableScope(Scope, types_.MutableScope[Var]):
    ...


class Expr(ABC):
    @abstractmethod
    def type(self, scope: Scope) -> types_.Type: ...

    @abstractmethod
    def eval(self, scope: vals.Scope) -> vals.Val: ...


class Decl(ABC):
    @abstractmethod
    def apply(self, scope: MutableScope) -> None: ...


@dataclass(frozen=True)
class Literal(Expr):
    val: vals.Val

    def type(self, scope: Scope) -> types_.Type:
        return self.val.type()

    def eval(self, scope: vals.Scope) -> vals.Val:
        return self.val


@ dataclass(frozen=True)
class Ref(Expr):
    name: str

    def type(self, scope: Scope) -> types_.Type:
        return scope.var(self.name).type()

    def eval(self, scope: vals.Scope) -> vals.Val:
        return scope.val(self.name)


@ dataclass(frozen=True)
class Member(Expr):
    object: Expr
    name: str

    def type(self, scope: Scope) -> types_.Type:
        return self.object.type(scope).member_types()[self.name]

    def eval(self, scope: vals.Scope) -> vals.Val:
        return self.object.eval(scope).members().val(self.name)


@ dataclass(frozen=True)
class Args(list[Expr]):
    def __init__(self, exprs: Iterable[Expr]):
        super().__init__(exprs)

    def types(self, scope: Scope) -> types_.Args:
        return types_.Args([types_.Arg(expr.type(scope)) for expr in self])

    def eval(self, scope: vals.Scope) -> vals.Args:
        return vals.Args([vals.Arg(expr.eval(scope)) for expr in self])


@ dataclass(frozen=True)
class Call(Expr):
    func: Expr
    args: Args

    def signature(self, scope: Scope) -> types_.Signature:
        signature = self.func.type(scope).signature()
        if signature is None:
            raise Error(f'{self.func} uncallable')
        return signature

    def type(self, scope: Scope) -> types_.Type:
        return self.signature(scope).return_type

    def eval(self, scope: vals.Scope) -> vals.Val:
        return self.func.eval(scope).call(scope, self.args.eval(scope))
