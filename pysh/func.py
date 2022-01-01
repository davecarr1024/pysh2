from dataclasses import dataclass
from typing import Sequence

from pysh import exprs, types_, vals


@dataclass(frozen=True)
class Func(vals.Callable):
    _signature: types_.Signature
    exprs: Sequence[exprs.Expr]

    @property
    def type(self) -> types_.Type:
        return types_.Builtin('func')

    @property
    def members(self) -> vals.Scope:
        return vals.Scope({})

    @property
    def signature(self) -> types_.Signature:
        return self._signature

    def _call(self, scope: vals.Scope, args: vals.Args) -> vals.Val:
        self._signature.check_args_assignable(args.types)
        func_scope = vals.Scope({
            param.name: vals.Var(param.type, arg)
            for param, arg in zip(self._signature.params.params, args.args)
        }, scope)
        return [expr.eval(func_scope) for expr in self.exprs][-1]
