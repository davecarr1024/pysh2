from typing import Sequence
from unittest import TestCase

from . import lexer


# TODO StartsWithTest(RuleTest)

# TODO NotTest(RuleTest)

class StateTest(TestCase):
    def test_empty(self):
        self.assertTrue(lexer.StateValue('').empty)
        self.assertFalse(lexer.StateValue('abc').empty)

    def test_head(self):
        self.assertEqual('a', lexer.StateValue('abc').head)

    def test_tail(self):
        self.assertEqual(lexer.StateValue('abc', 1),
                         lexer.StateValue('abc').tail)


class TokenStreamTest(TestCase):
    def test_empty(self):
        self.assertTrue(lexer.TokenStream([]).empty)
        self.assertFalse(lexer.TokenStream([lexer.Token('a', 'b')]).empty)

    def test_head(self):
        self.assertEqual(lexer.Token('a', 'b'), lexer.TokenStream(
            [lexer.Token('a', 'b')]).head)

    def test_tail(self):
        toks: Sequence[lexer.Token] = [
            lexer.Token('a', 'b'), lexer.Token('c', 'd')]
        self.assertEqual(
            lexer.TokenStream(toks[1:]),
            lexer.TokenStream(toks).tail
        )


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
                        'a': lexer.StartsWith('a'),
                        'b': lexer.OneOrMore(lexer.StartsWith('c')),
                    }).apply(input),
                    lexer.TokenStream(output)
                )
