from dataclasses import dataclass
from typing import Sequence

from pysh import exprs, types_, vals


@dataclass(frozen=True)
class Func(vals.Val):
    name: str
    signature: types_.Signature
    exprs: Sequence[exprs.Expr]

    
    def type(self) -> types_.Type:
        return types_.Builtin('func')

    
    def members(self) -> vals.Scope:
        return vals.Scope({})

    
    def signatures(self) -> types_.Signatures:
        return types_.Signatures([self.signature])

    def _call(self, scope: vals.Scope, args: vals.Args) -> vals.Val:
        self.signature.check_args_assignable(args.types)
        func_scope = vals.Scope({
            param.name: vals.Var(param.type, arg.val)
            for param, arg in zip(self.signature.params, args)
        }, scope)
        return [expr.eval(func_scope) for expr in self.exprs][-1]
