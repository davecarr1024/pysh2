from pysh import types_, vals

from unittest import TestCase

if 'unittest.util' in __import__('sys').modules:
    # Show full diff in self.assertEqual.
    __import__('sys').modules['unittest.util']._MAX_LENGTH = 999999999


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
