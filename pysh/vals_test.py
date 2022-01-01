from dataclasses import dataclass
from pysh import errors, types_, vals

from unittest import TestCase

int_type = types_.BuiltinType('int')
str_type = types_.BuiltinType('str)')


@dataclass(frozen=True)
class Int(vals.Val):
    value: int

    @property
    def type(self) -> types_.Type:
        return int_type

    @property
    def members(self) -> vals.Scope:
        return vals.Scope({})


@dataclass(frozen=True)
class Str(vals.Val):
    value: str

    @property
    def type(self) -> types_.Type:
        return str_type

    @property
    def members(self) -> vals.Scope:
        return vals.Scope({})


class VarTest(TestCase):
    def test_ctor(self):
        vals.Var(int_type, Int(1))
        with self.assertRaises(errors.Error):
            vals.Var(str_type, Int(1))

    def test_type(self):
        self.assertEqual(vals.Var(int_type, Int(1)).type, int_type)

    def test_val(self):
        self.assertEqual(vals.Var(int_type, Int(1)).val, Int(1))

    def test_check_assignable(self):
        vals.Var(int_type, Int(1)).check_assignable(Int(2))
        with self.assertRaises(errors.Error):
            vals.Var(int_type, Int(1)).check_assignable(Str('a'))

    def test_set_val(self):
        var = vals.Var(int_type, Int(1))
        self.assertEqual(var.val, Int(1))
        var.set_val(Int(2))
        self.assertEqual(var.val, Int(2))
        with self.assertRaises(errors.Error):
            var.set_val(Str('a'))

    def test_for_val(self):
        self.assertEqual(
            vals.Var.for_val(Int(1)),
            vals.Var(int_type, Int(1))
        )


