from typing import Sequence
from . import pysp
import unittest


class PyspTest(unittest.TestCase):
    def test_builtin_func(self):
        def add(lhs: pysp.Int, rhs: pysp.Int) -> pysp.Val:
            return pysp.Int(lhs.value + rhs.value)
        add_func = pysp.BuiltinFunc(add)
        self.assertEqual(
            add_func.apply(pysp.Scope(), [pysp.Int(1), pysp.Int(2)]),
            pysp.Int(3)
        )
        with self.assertRaises(ValueError):
            add_func.apply(pysp.Scope(), [])
        with self.assertRaises(TypeError):
            add_func.apply(pysp.Scope(), [pysp.Int(1), pysp.Str('a')])

    def test_expr_eval(self):
        expr: pysp.Expr
        val: pysp.Val
        for expr, val in [
            (pysp.Literal(pysp.Int(1)), pysp.Int(1)),
        ]:
            with self.subTest(expr=expr, val=val):
                self.assertEqual(expr.eval(pysp.Scope.default_scope()), val)

    def test_load_expr(self):
        input: str
        exprs: Sequence[pysp.Expr]
        for input, exprs in [
            ('1', [pysp.Literal(pysp.Int(1))]),
            ('a', [pysp.Ref('a')]),
            ('(a b)', [pysp.CompoundExpr([pysp.Ref('a'), pysp.Ref('b')])]),
        ]:
            with self.subTest(input=input, exprs=exprs):
                self.assertEqual(exprs, pysp.load(input))
