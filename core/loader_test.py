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
        ]:
            with self.subTest((input, rule)):
                self.assertEqual(rule, loader.lexer_rule(input))
