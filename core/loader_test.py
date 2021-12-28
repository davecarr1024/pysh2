import unittest

from core import lexer, loader


class LoaderTest(unittest.TestCase):
    def test_load_lexer_rule(self):
        input: str
        rule: lexer.Rule
        for input, rule in [
            (
                'a',
                lexer.And([
                    lexer.Literal('a'),
                ])
            ),
            (
                'ab',
                lexer.And([
                    lexer.Literal('a'),
                    lexer.Literal('b'),
                ])
            ),
            (
                '(a)',
                lexer.And([
                    lexer.And([
                        lexer.Literal('a'),
                    ])
                ])
            ),
            (
                '(ab)',
                lexer.And([
                    lexer.And([
                        lexer.Literal('a'),
                        lexer.Literal('b'),
                    ])
                ])
            ),
            ('a*', lexer.And([lexer.ZeroOrMore(lexer.Literal('a'))])),
            ('a+', lexer.And([lexer.OneOrMore(lexer.Literal('a'))])),
            ('a?', lexer.And([lexer.ZeroOrOne(lexer.Literal('a'))])),
            ('a!', lexer.And([lexer.UntilEmpty(lexer.Literal('a'))])),
            ('^a', lexer.And([lexer.Not(lexer.Literal('a'))])),
            ('[a-z]', lexer.And([lexer.Class('a', 'z')])),
            ('(a|b)', lexer.And(
                [lexer.Or([lexer.Literal('a'), lexer.Literal('b')])])),
        ]:
            with self.subTest((input, rule)):
                self.assertEqual(rule, loader.lexer_rule(input))
