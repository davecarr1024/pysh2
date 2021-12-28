from typing import Sequence
from unittest import TestCase

from . import lexer


# TODO LiteralTest(RuleTest)

# TODO NotTest(RuleTest)


class LexerTest(TestCase):
    def test_lex(self):
        input: str
        output: Sequence[lexer.Token]
        for input, output in [
            ('a', [lexer.Token('a', 'a')]),
            ('c', [lexer.Token('b', 'c')]),
            ('cc', [lexer.Token('b', 'cc')]),
            ('acc', [lexer.Token('a', 'a'), lexer.Token('b', 'cc')]),
        ]:
            with self.subTest((input, output)):
                self.assertEqual(
                    lexer.Lexer({
                        'a': lexer.Literal('a'),
                        'b': lexer.OneOrMore(lexer.Literal('c')),
                    }).apply(input),
                    lexer.TokenStream(output)
                )
