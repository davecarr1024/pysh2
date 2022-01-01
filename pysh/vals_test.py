from pysh import types_, vals

from unittest import TestCase

if 'unittest.util' in __import__('sys').modules:
    # Show full diff in self.assertEqual.
    __import__('sys').modules['unittest.util']._MAX_LENGTH = 999999999


class VarTest(TestCase):
    def test_ctor(self):
        vals.Var(vals.Int.builtin_class(), vals.Int(1))
        with self.assertRaises(vals.Error):
            vals.Var(vals.Str.builtin_class(), vals.Int(1))

    def test_type(self):
        self.assertEqual(vals.Var(vals.Int.builtin_class(),
                         vals.Int(1)).type, vals.Int.builtin_class())

    def test_val(self):
        self.assertEqual(vals.Var(vals.Int.builtin_class(),
                         vals.Int(1)).val, vals.Int(1))

    def test_check_assignable(self):
        vals.Var(vals.Int.builtin_class(), vals.Int(1)
                 ).check_assignable(vals.Int(2))
        with self.assertRaises(vals.Error):
            vals.Var(vals.Int.builtin_class(), vals.Int(1)
                     ).check_assignable(vals.Str('a'))

    def test_set_val(self):
        var = vals.Var(vals.Int.builtin_class(), vals.Int(1))
        self.assertEqual(var.val, vals.Int(1))
        var.set_val(vals.Int(2))
        self.assertEqual(var.val, vals.Int(2))
        with self.assertRaises(vals.Error):
            var.set_val(vals.Str('a'))

    def test_for_val(self):
        self.assertEqual(
            vals.Var.for_val(vals.Int(1)),
            vals.Var(vals.Int.builtin_class(), vals.Int(1))
        )


class ScopeTest(TestCase):
    def test_contains(self):
        scope = vals.Scope({'a': vals.Var.for_val(vals.Int(1))})
        self.assertTrue('a' in scope)
        self.assertFalse('b' in scope)
        scope = vals.Scope({}, scope)
        self.assertTrue('a' in scope)
        self.assertFalse('b' in scope)

    def test_getitem(self):
        scope = vals.Scope({'a': vals.Var.for_val(vals.Int(1))})
        self.assertEqual(scope['a'], vals.Int(1))
        with self.assertRaises(vals.Error):
            scope['b']
        scope = vals.Scope({}, scope)
        self.assertEqual(scope['a'], vals.Int(1))
        with self.assertRaises(vals.Error):
            scope['b']

    def test_setitem(self):
        scope = vals.Scope({'a': vals.Var.for_val(vals.Int(1))})
        self.assertEqual(scope['a'], vals.Int(1))
        scope['a'] = vals.Int(2)
        self.assertEqual(scope['a'], vals.Int(2))
        with self.assertRaises(vals.Error):
            scope['a'] = vals.Str('a')
        with self.assertRaises(vals.Error):
            scope['b'] = vals.Int(3)
        scope = vals.Scope({}, scope)
        self.assertEqual(scope['a'], vals.Int(2))
        scope['a'] = vals.Int(3)
        self.assertEqual(scope['a'], vals.Int(3))
        with self.assertRaises(vals.Error):
            scope['a'] = vals.Str('a')
        with self.assertRaises(vals.Error):
            scope['b'] = vals.Int(4)

    def test_vals(self):
        self.assertDictEqual(
            vals.Scope({'a': vals.Var.for_val(vals.Int(1))}).vals,
            {'a': vals.Int(1)}
        )

    def test_all_vals(self):
        self.assertDictEqual(
            vals.Scope(
                {'a': vals.Var.for_val(vals.Int(1))},
                vals.Scope(
                    {
                        'a': vals.Var.for_val(vals.Int(2)),
                        'b': vals.Var.for_val(vals.Int(3)),
                    }
                )
            ).all_vals(),
            {
                'a': vals.Int(1),
                'b': vals.Int(3),
            }
        )

    def test_all_types(self):
        self.assertDictEqual(
            vals.Scope(
                {'a': vals.Var.for_val(vals.Int(1))},
                vals.Scope(
                    {
                        'a': vals.Var.for_val(vals.Str('s')),
                        'b': vals.Var.for_val(vals.Int(3)),
                    }
                )
            ).all_types(),
            {'a': vals.Int.builtin_class(), 'b': vals.Int.builtin_class()})

    def test_decl(self):
        scope = vals.Scope({})
        scope.decl('a', vals.Var.for_val(vals.Int(1)))
        self.assertEqual(scope['a'], vals.Int(1))
        with self.assertRaises(vals.Error):
            scope.decl('a', vals.Var.for_val(vals.Int(2)))


class BuiltinFuncTest(TestCase):
    def test_signature(self):
        def add_ints(a: vals.Int, b: vals.Int) -> vals.Int:
            return vals.Int(a.val + b.val)
        func = vals.BuiltinFunc(add_ints)
        self.assertEqual(
            func.signature,
            types_.Signature(
                types_.Params([
                    types_.Param('a', vals.Int.builtin_class()),
                    types_.Param('b', vals.Int.builtin_class()),
                ]),
                vals.Int.builtin_class()
            )
        )
