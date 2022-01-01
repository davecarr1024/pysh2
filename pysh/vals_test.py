from dataclasses import dataclass
from pysh import types_, vals

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
        with self.assertRaises(vals.Error):
            vals.Var(str_type, Int(1))

    def test_type(self):
        self.assertEqual(vals.Var(int_type, Int(1)).type, int_type)

    def test_val(self):
        self.assertEqual(vals.Var(int_type, Int(1)).val, Int(1))

    def test_check_assignable(self):
        vals.Var(int_type, Int(1)).check_assignable(Int(2))
        with self.assertRaises(vals.Error):
            vals.Var(int_type, Int(1)).check_assignable(Str('a'))

    def test_set_val(self):
        var = vals.Var(int_type, Int(1))
        self.assertEqual(var.val, Int(1))
        var.set_val(Int(2))
        self.assertEqual(var.val, Int(2))
        with self.assertRaises(vals.Error):
            var.set_val(Str('a'))

    def test_for_val(self):
        self.assertEqual(
            vals.Var.for_val(Int(1)),
            vals.Var(int_type, Int(1))
        )


class ScopeTest(TestCase):
    def test_contains(self):
        scope = vals.Scope({'a': vals.Var.for_val(Int(1))})
        self.assertTrue('a' in scope)
        self.assertFalse('b' in scope)
        scope = vals.Scope({}, scope)
        self.assertTrue('a' in scope)
        self.assertFalse('b' in scope)

    def test_getitem(self):
        scope = vals.Scope({'a': vals.Var.for_val(Int(1))})
        self.assertEqual(scope['a'], Int(1))
        with self.assertRaises(vals.Error):
            scope['b']
        scope = vals.Scope({}, scope)
        self.assertEqual(scope['a'], Int(1))
        with self.assertRaises(vals.Error):
            scope['b']

    def test_setitem(self):
        scope = vals.Scope({'a': vals.Var.for_val(Int(1))})
        self.assertEqual(scope['a'], Int(1))
        scope['a'] = Int(2)
        self.assertEqual(scope['a'], Int(2))
        with self.assertRaises(vals.Error):
            scope['a'] = Str('a')
        with self.assertRaises(vals.Error):
            scope['b'] = Int(3)
        scope = vals.Scope({}, scope)
        self.assertEqual(scope['a'], Int(2))
        scope['a'] = Int(3)
        self.assertEqual(scope['a'], Int(3))
        with self.assertRaises(vals.Error):
            scope['a'] = Str('a')
        with self.assertRaises(vals.Error):
            scope['b'] = Int(4)

    def test_vals(self):
        self.assertDictEqual(
            vals.Scope({'a': vals.Var.for_val(Int(1))}).vals,
            {'a': Int(1)}
        )

    def test_all_vals(self):
        self.assertDictEqual(
            vals.Scope(
                {'a': vals.Var.for_val(Int(1))},
                vals.Scope(
                    {
                        'a': vals.Var.for_val(Int(2)),
                        'b': vals.Var.for_val(Int(3)),
                    }
                )
            ).all_vals(),
            {
                'a': Int(1),
                'b': Int(3),
            }
        )

    def test_all_types(self):
        self.assertDictEqual(
            vals.Scope(
                {'a': vals.Var.for_val(Int(1))},
                vals.Scope(
                    {
                        'a': vals.Var.for_val(Str('s')),
                        'b': vals.Var.for_val(Int(3)),
                    }
                )
            ).all_types(),
            {'a': int_type, 'b': int_type})

    def test_decl(self):
        scope = vals.Scope({})
        scope.decl('a', vals.Var.for_val(Int(1)))
        self.assertEqual(scope['a'], Int(1))
        with self.assertRaises(vals.Error):
            scope.decl('a', vals.Var.for_val(Int(2)))
