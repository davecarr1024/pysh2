from typing import Mapping, Optional
from pysh import types_, vals

from unittest import TestCase

if 'unittest.util' in __import__('sys').modules:
    # Show full diff in self.assertEqual.
    __import__('sys').modules['unittest.util']._MAX_LENGTH = 999999999

bool_type = vals.Bool.builtin_class()
bool_type_arg = types_.Arg(bool_type)
int_type = vals.Int.builtin_class()
int_type_arg = types_.Arg(int_type)
str_type = vals.Str.builtin_class()
str_type_arg = types_.Arg(str_type)


def bool_val(val: bool = True) -> vals.Bool:
    return vals.Bool(val)


def bool_arg(val: bool = True) -> vals.Arg:
    return vals.Arg(bool_val(val))


def int_val(val: int = 1) -> vals.Int:
    return vals.Int(val)


def int_arg(val: int = 1) -> vals.Arg:
    return vals.Arg(int_val(val))


def str_val(val: str = 'a') -> vals.Str:
    return vals.Str(val)


def str_arg(val: str = 'a') -> vals.Arg:
    return vals.Arg(str_val(val))


def args(*args: vals.Arg) -> vals.Args:
    return vals.Args(args)


def type_args(*args: types_.Arg) -> types_.Args:
    return types_.Args(args)


class ArgTest(TestCase):
    def test_type(self):
        self.assertEqual(int_arg().type(), int_type)


class ArgsTest(TestCase):
    def test_with_first_arg(self):
        self.assertEqual(
            args(int_arg(1)).with_first_arg(int_arg(2)),
            args(int_arg(2), int_arg(1))
        )

    def test_types(self):
        self.assertEqual(
            args(bool_arg(), int_arg(), str_arg()).types(),
            type_args(bool_type_arg, int_type_arg, str_type_arg)
        )


add_ints_sig = types_.Signature(
    types_.Params([
        types_.Param('lhs', int_type),
        types_.Param('rhs', int_type),
    ]),
    int_type
)


class AddIntsType(types_.Type):

    def name(self) -> str:
        return 'AddIntsType'

    def signature(self) -> Optional[types_.Signature]:
        return add_ints_sig

    def check_assignable(self, type: types_.Type) -> None:
        raise NotImplementedError()

    def member_types(self) -> Mapping[str, types_.Type]:
        return {}


add_ints_type = AddIntsType()


class AddInts(vals.BindableCallable):

    def type(self) -> types_.Type:
        return add_ints_type

    def members(self) -> vals.Scope:
        return vals.Scope({})

    def _call(self, scope: vals.Scope, args: vals.Args) -> vals.Val:
        lhs, rhs = args.vals()
        assert isinstance(lhs, vals.Int)
        assert isinstance(rhs, vals.Int)
        return vals.Int(lhs.val + rhs.val)


class TestCallables(TestCase):
    def test_call(self):
        self.assertEqual(
            AddInts().call(vals.Scope({}), args(int_arg(1), int_arg(2))),
            int_val(3)
        )
        with self.assertRaises(vals.Error):
            AddInts().call(vals.Scope({}), args(int_arg(1)))
        with self.assertRaises(vals.Error):
            AddInts().call(vals.Scope({}), args(str_arg()))

    def test_bind(self):
        self.assertEqual(
            AddInts().bind(int_val(1)).call(vals.Scope({}), args(int_arg(2))),
            int_val(3)
        )


class BuiltinFuncTest(TestCase):
    @staticmethod
    def add_ints(a: vals.Int, b: vals.Int) -> vals.Int:
        return vals.Int(a.val + b.val)

    def test_signatures(self):
        self.assertEqual(
            vals.BuiltinFunc(self.add_ints).signature(),
            types_.Signature(
                types_.Params([
                    types_.Param('a', int_type),
                    types_.Param('b', int_type),
                ]),
                int_type
            )
        )

    def test_call(self):
        self.assertEqual(
            vals.BuiltinFunc(self.add_ints).call(
                vals.Scope({}), args(int_arg(1), int_arg(2))),
            int_val(3)
        )
        with self.assertRaises(vals.Error):
            vals.BuiltinFunc(self.add_ints).call(
                vals.Scope({}), args(int_arg(1)))
        with self.assertRaises(vals.Error):
            vals.BuiltinFunc(self.add_ints).call(
                vals.Scope({}), args(str_arg()))
