from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import inspect
from typing import Callable, Mapping, MutableMapping, Optional, Sequence

from core import loader, parser


@dataclass(frozen=True)
class Expr(ABC):
    @abstractmethod
    def eval(self, scope: 'Scope') -> 'Val': ...


@dataclass(frozen=True)
class CompoundExpr(Expr):
    exprs: Sequence[Expr]

    def eval(self, scope: 'Scope') -> 'Val':
        vals = [expr.eval(scope) for expr in self.exprs]
        return vals[0].apply(scope, vals[1:])


@dataclass(frozen=True)
class FuncDef(Expr):
    params: Sequence[str]
    body: Sequence[Expr]

    def eval(self, scope: 'Scope') -> 'Val':
        return Func(self, scope)


@dataclass(frozen=True)
class Ref(Expr):
    var: str

    def eval(self, scope: 'Scope') -> 'Val':
        return scope[self.var]


@dataclass(frozen=True)
class Val:
    def apply(self, scope: 'Scope', args: Sequence['Val']) -> 'Val':
        raise NotImplemented


@dataclass
class Scope:
    _vals: MutableMapping[str, Val] = field(default_factory=dict)
    _parent: Optional['Scope'] = None

    def __contains__(self, var: str) -> bool:
        return var in self._vals or (self._parent is not None and var in self._parent)

    def __getitem__(self, var: str) -> Val:
        if var in self._vals:
            return self._vals[var]
        elif self._parent is not None:
            return self._parent[var]
        else:
            raise KeyError(var)

    def __setitem__(self, var: str, val: Val) -> None:
        self._vals[var] = val

    @staticmethod
    def default_scope() -> 'Scope':
        return Scope(_vals={
            '+': BuiltinFunc(Int.__add__),
        })


@dataclass(frozen=True)
class Int(Val):
    value: int

    def __add__(self, rhs: 'Int') -> Val:
        return Int(self.value + rhs.value)


@dataclass(frozen=True)
class Str(Val):
    value: str


@dataclass(frozen=True)
class Func(Val):
    func_def: FuncDef
    scope: Scope

    def apply(self, scope: Scope, args: Sequence[Val]) -> Val:
        if len(self.func_def.params) != len(args):
            raise ValueError(
                f'{self} expected {len(self.func_def.params)} args but got {len(args)}')
        func_scope = Scope(_parent=self.scope, _vals={
                           param: arg for param, arg in zip(self.func_def.params, args)})
        return [expr.eval(func_scope) for expr in self.func_def.body][-1]


@dataclass(frozen=True)
class Literal(Expr):
    val: Val

    def eval(self, scope: Scope) -> Val:
        return self.val


@dataclass(frozen=True)
class BuiltinFunc(Val):
    func: Callable[..., Val]

    def apply(self, scope: Scope, args: Sequence['Val']) -> 'Val':
        func_arg_types = [p.annotation for p in inspect.signature(
            self.func).parameters.values()]
        if len(func_arg_types) != len(args):
            raise ValueError(
                f'{self} expected {len(func_arg_types)} args but got {len(args)}')
        for i, (func_arg_type, val) in enumerate(zip(func_arg_types, args)):
            if not isinstance(val, func_arg_type):
                raise TypeError(
                    f'{self} arg {i} expected type {func_arg_type} but got {val}')
            assert isinstance(val, func_arg_type)
        return self.func(*args)


def load(input: str) -> Sequence[Expr]:
    parser_ = loader.load_parser(r'''
        _ws = "\w+";
        int = "\-?[0-9]+";
        id = "(_|[a-z]|[A-Z])(_|\-|[a-z]|[A-Z]|[0-9])*";

        exprs -> expr!;
        expr -> lambda | compound_expr | literal | ref;
        literal -> int;
        ref -> id;
        compound_expr -> "\(" expr+ "\)";
        lambda -> "\(" "lambda" params func_body "\)";
        params -> "\(" id* "\)";
        func_body -> expr+;
    ''')
    result = parser_.apply(input)

    def dict_loader(expr_loaders: Mapping[str, Callable[[parser.Result], Expr]]) -> Callable[[parser.Result], Expr]:
        def closure(result: parser.Result) -> Expr:
            expr_result = result.where_one(
                parser.Result.rule_name_in(list(expr_loaders.keys())))
            assert expr_result.rule_name is not None
            return expr_loaders[expr_result.rule_name](expr_result)
        return closure

    def load_compound_expr(result: parser.Result) -> Expr:
        return CompoundExpr([load_expr(expr) for expr in result.where(parser.Result.rule_name_is('expr'))])

    def load_ref(result: parser.Result) -> Expr:
        return Ref(result.where_one(parser.Result.rule_name_is('id')).get_value().value)

    def load_int(result: parser.Result) -> Expr:
        return Literal(Int(int(result.get_value().value)))

    def load_params(result: parser.Result) -> Sequence[str]:
        return [id.get_value().value for id in result.where(parser.Result.rule_name_is('id'))]

    def load_func_body(result: parser.Result) -> Sequence[Expr]:
        return [load_expr(expr) for expr in result.where(parser.Result.rule_name_is('expr'))]

    def load_lambda(result: parser.Result) -> Expr:
        params = load_params(result.where_one(
            parser.Result.rule_name_is('params')))
        func_body = load_func_body(result.where_one(
            parser.Result.rule_name_is('func_body')))
        return FuncDef(params, func_body)

    load_literal = dict_loader({'int': load_int})
    load_expr = dict_loader({
        'literal': load_literal,
        'ref': load_ref,
        'compound_expr': load_compound_expr,
        'lambda': load_lambda,
    })

    return [load_expr(expr) for expr in result.where(parser.Result.rule_name_is('expr'))]
