from dataclasses import dataclass
from typing import Sequence
from unittest import TestCase

from . import lexer


@dataclass(frozen=True)
class StartsWith(lexer.Rule):
    value: str

    def apply(self, state: lexer.State) -> lexer.ResultAndState:
        if state.value.startswith(self.value):
            result_value: lexer.ResultValue = lexer.ResultValue(self.value)
            return lexer.ResultAndState(lexer.Result(self, result_value, []), state.after(result_value))
        raise lexer.RuleError(self, state)


class StateTest(TestCase):
    def test_empty(self):
        self.assertTrue(lexer.State('').empty)
        self.assertFalse(lexer.State('foo').empty)

    def test_value(self):
        self.assertEqual('foo', lexer.State('foo').value)
        self.assertEqual('bar', lexer.State('foobar', 3).value)

    def test_with_pos(self):
        self.assertEqual(10, lexer.State('').with_pos(10).pos)

    def test_after(self):
        self.assertEqual(lexer.State('foobar', 3), lexer.State(
            'foobar').after(lexer.ResultValue('foo')))
        with self.assertRaises(ValueError):
            lexer.State('foobar').after(lexer.ResultValue('baz'))


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
            self.assertEqual(
                lexer.Lexer([
                    StartsWith('a', 'a'),
                    lexer.OneOrMore('b', StartsWith(None, 'c')),
                ]).apply(input),
                lexer.TokenStream(output)
            )
