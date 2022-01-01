from pysh import types_

from unittest import TestCase

int_ = types_.BuiltinType('int')
str_ = types_.BuiltinType('str')


class BuiltinTypeTest(TestCase):
    def test_name(self):
        self.assertEqual(int_.name, 'int')

    def test_check_assignable(self):
        int_.check_assignable(int_)
        with self.assertRaises(types_.Error):
            int_.check_assignable(str_)


class ParamTest(TestCase):
    def test_check_assignable(self):
        types_.Param('a', int_).check_assignable(int_)
        with self.assertRaises(types_.Error):
            types_.Param('a', int_).check_assignable(str_)


class ParamsTest(TestCase):
    def test_check_assignable(self):
        params = types_.Params([types_.Param('a', int_)])
        params.check_assignable([int_])
        with self.assertRaises(types_.Error):
            params.check_assignable([])
        with self.assertRaises(types_.Error):
            params.check_assignable([str_])


class SignatureTest(TestCase):
    def test_check_assignable(self):
        signature = types_.Signature(types_.Params(
            [types_.Param('a', int_), types_.Param('b', int_)]), int_)
        signature.check_args_assignable([int_,int_])
        with self.assertRaises(types_.Error):
            signature.check_args_assignable([])
        with self.assertRaises(types_.Error):
            signature.check_args_assignable([int_,str_])
        signature.check_return_val_assignable(int_)
        with self.assertRaises(types_.Error):
            signature.check_return_val_assignable(str_)
