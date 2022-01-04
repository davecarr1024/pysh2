from dataclasses import dataclass
from typing import Optional, Sequence
from pysh import types_

from unittest import TestCase

int_type = types_.Builtin('int')
int_arg = types_.Arg(int_type)


def int_param(name: str = 'a') -> types_.Param:
    return types_.Param(name, int_type)


str_type = types_.Builtin('str')
str_arg = types_.Arg(str_type)


def str_param(name: str = 's') -> types_.Param:
    return types_.Param(name, str_type)


class BuiltinTypeTest(TestCase):
    def test_name(self):
        self.assertEqual(int_type.name, 'int')

    def test_check_assignable(self):
        int_type.check_assignable(int_type)
        with self.assertRaises(types_.Error):
            int_type.check_assignable(str_type)


class ParamTest(TestCase):
    def test_check_assignable(self):
        int_param().check_assignable(int_arg)
        with self.assertRaises(types_.Error):
            int_param().check_assignable(str_arg)


class ParamsTest(TestCase):
    def test_check_assignable(self):
        params = types_.Params([int_param()])
        params.check_assignable(types_.Args([int_arg]))
        with self.assertRaises(types_.Error):
            params.check_assignable(types_.Args([]))
        with self.assertRaises(types_.Error):
            params.check_assignable(types_.Args([str_arg]))

    def test_without_first_param(self):
        self.assertEqual(types_.Params([int_param()]).without_first_param(),
                         types_.Params([]))
        with self.assertRaises(types_.Error):
            types_.Params([]).without_first_param()


class SignatureTest(TestCase):
    def test_check_assignable(self):
        signature = types_.Signature(types_.Params(
            [int_param('a'), int_param('b')]), int_type)
        signature.check_args_assignable(
            types_.Args([int_arg, int_arg]))
        with self.assertRaises(types_.Error):
            signature.check_args_assignable(types_.Args([]))
        with self.assertRaises(types_.Error):
            signature.check_args_assignable(
                types_.Args([int_arg, str_arg]))
        signature.check_return_assignable(int_type)
        with self.assertRaises(types_.Error):
            signature.check_return_assignable(str_type)

    def test_without_first_param(self):
        self.assertEqual(types_.Signature(types_.Params([int_param()]), int_type).without_first_param(),
                         types_.Signature(types_.Params([]), int_type))
        with self.assertRaises(types_.Error):
            types_.Signature(types_.Params([]), int_type).without_first_param()


class SignaturesTest(TestCase):
    # def test_check_assignable(self):
    #     signatures = types_.Signatures([
    #         types_.Signature(
    #             types_.Params([
    #                 int_param(),
    #             ]),
    #             int_type
    #         ),
    #         types_.Signature(
    #             types_.Params([
    #                 str_param(),
    #             ]),
    #             int_type
    #         ),
    #     ])
    #     signatures.check_args_assignable(types_.Args([int_arg]))
    #     signatures.check_args_assignable(types_.Args([str_arg]))
    #     with self.assertRaises(types_.Error):
    #         signatures.check_args_assignable(types_.Args([]))
    #     with self.assertRaises(types_.Error):
    #         signatures.check_args_assignable(types_.Args([int_arg, str_arg]))
    #     signatures.check_return_assignable(int_type)
    #     with self.assertRaises(types_.Error):
    #         signatures.check_return_assignable(str_type)

    def test_without_first_param(self):
        self.assertEqual(types_.Signatures([types_.Signature(types_.Params([int_param()]), int_type)]).without_first_param(),
                         types_.Signatures([types_.Signature(types_.Params([]), int_type)]))
        with self.assertRaises(types_.Error):
            types_.Signatures(
                [types_.Signature(types_.Params([]), int_type)]).without_first_param()


@dataclass(frozen=True)
class Val(types_.Val):
    _type: types_.Type
    name: str = 'v'

    
    def type(self) -> types_.Type:
        return self._type


def val(type: types_.Type, name: str) -> Val:
    return Val(type, name)


def int_val(name: str = 'i') -> Val:
    return val(int_type, name)


def str_val(name: str = 's') -> Val:
    return val(str_type, name)


Var = types_.Var[Val]


def int_var(name: str = 'i', type: type[Var] = Var) -> Var:
    return type(int_type, int_val(name))


def str_var(name: str = 's', type: type[Var] = Var) -> Var:
    return type(str_type, str_val(name))


class VarTest(TestCase):
    def test_validate(self):
        int_var()
        with self.assertRaises(types_.Error):
            types_.Var(int_type, Val(str_type))

    def test_type(self):
        self.assertEqual(int_var().type, int_type)

    def test_val(self):
        self.assertEqual(int_var().val, int_val())

    def test_check_assignable(self):
        int_var().check_assignable(int_val())
        with self.assertRaises(types_.Error):
            int_var().check_assignable(str_val())

    def test_for_val(self):
        self.assertEqual(Var.for_val(int_val()), int_var())

    def test_set(self):
        with self.assertRaises(types_.Error):
            int_var().val = int_val()


MutableVar = types_.MutableVar[Val]


class MutableVarTest(TestCase):
    def test_set(self):
        i = int_var('i', MutableVar)
        self.assertEqual(i.val, int_val('i'))
        i.val = int_val('j')
        self.assertEqual(i.val, int_val('j'))


Scope = types_.Scope[Val]


def scope(vals: Sequence[Val], parent: Optional[Scope] = None) -> Scope:
    return Scope({val.name: Var.for_val(val) for val in vals}, parent)


class ScopeTest(TestCase):
    def test_contains(self):
        s = scope([int_val('a')], scope([int_val('b')]))
        self.assertTrue('a' in s)
        self.assertTrue('b' in s)
        self.assertFalse('c' in s)

    def test_getitem(self):
        s = scope([int_val('a')], scope([int_val('b')]))
        self.assertEqual(int_val('a'), s['a'])
        self.assertEqual(int_val('b'), s['b'])
        with self.assertRaises(types_.Error):
            s['c']

    def test_vals(self):
        self.assertEqual(
            scope([int_val('a')], scope([int_val('b')])).vals,
            {'a': int_val('a')}
        )

    def test_all_vals(self):
        self.assertEqual(
            scope([int_val('a')], scope([int_val('b')])).all_vals(),
            {'a': int_val('a'), 'b': int_val('b')}
        )

    def test_all_types(self):
        self.assertEqual(
            scope([int_val('a')], scope([str_val('b')])).all_types(),
            {'a': int_type, 'b': str_type}
        )


MutableScope = types_.MutableScope[Val]


def mutable_scope(vals: Sequence[Val], parent: Optional[Scope] = None) -> MutableScope:
    return MutableScope({val.name: MutableVar.for_val(val) for val in vals}, parent)


class MutableScopeTest(TestCase):
    def test_setitem(self):
        s = mutable_scope([int_val('a')], mutable_scope([int_val('b')]))
        s['a'] = int_val('c')
        self.assertEqual(s['a'], int_val('c'))
        s['b'] = int_val('d')
        self.assertEqual(s['b'], int_val('d'))
        with self.assertRaises(types_.Error):
            s['e'] = int_val('f')

    def test_decl(self):
        s = mutable_scope([int_val('a')], mutable_scope([int_val('b')]))
        s.decl('b', int_var('c'))
        self.assertEqual(s['b'], int_val('c'))
        with self.assertRaises(types_.Error):
            s.decl('a', int_var('d'))
