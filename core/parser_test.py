from typing import Sequence
from .lexer import Lexer
from .parser import Parser

from typing import Optional, Sequence
from unittest import TestCase

if 'unittest.util' in __import__('sys').modules:
    # Show full diff in self.assertEqual.
    __import__('sys').modules['unittest.util']._MAX_LENGTH = 999999999


class RuleTest(TestCase):
    @staticmethod
    def _token(type: str, val: str) -> Lexer.Token:
        return Lexer.Token(type, val, Lexer.Position(0))

    @staticmethod
    def _token_result(token: Lexer.Token) -> Parser.Result:
        return Parser.Result(token.rule_name, token)

    @ staticmethod
    def _child_result(type: Optional[str], children: Sequence[Parser.Result]) -> Parser.Result:
        return Parser.Result(type, children=children)

    @ staticmethod
    def _apply_rule(rule: Parser.Rule, tokens: Sequence[Lexer.Token]) -> Parser.Rule.Result:
        return rule.apply(Parser.State(Lexer.Result(tokens)))

    def _test_rule(self, rule: Parser.Rule, tokens: Sequence[Lexer.Token], result: Parser.Result) -> None:
        lexer_result: Lexer.Result = Lexer.Result(tokens)
        self.assertEqual(
            self._apply_rule(rule, tokens),
            Parser.Rule.Result(
                result,
                Parser.State(lexer_result, len(tokens))
            )
        )


class LiteralTest(RuleTest):
    def test_match(self):
        self._test_rule(
            Parser.Literal('int'),
            [self._token('int', '1')],
            self._token_result(self._token('int', '1'))
        )

    def test_empty(self):
        with self.assertRaises(Parser.Error):
            self._apply_rule(Parser.Literal('int'), [])

    def test_mismatch(self):
        with self.assertRaises(Parser.Error):
            self._apply_rule(Parser.Literal('int'), [self._token('str', 'a')])


class AndTest(RuleTest):
    def test_match(self):
        self._test_rule(
            Parser.And('a',
                       [
                           Parser.Literal('b'),
                           Parser.Literal('c'),
                       ]
                       ),
            [
                self._token('b', '1'),
                self._token('c', '2'),
            ],
            self._child_result(
                'a',
                [
                    self._token_result(self._token('b', '1')),
                    self._token_result(self._token('c', '2')),
                ]
            )
        )

    def test_mismatch(self):
        tokens: Sequence[Lexer.Token]
        for tokens in [
            [self._token('b', '1')],
            [self._token('c', '1')],
            [self._token('d', '1')],
            [],
        ]:
            with self.subTest(tokens):
                with self.assertRaises(Parser.Error):
                    self._apply_rule(
                        Parser.And('a',
                                   [
                                       Parser.Literal('b'),
                                       Parser.Literal('c'),
                                   ]
                                   ),
                        tokens,
                    )


class OrTest(RuleTest):
    def test_match(self):
        token: Lexer.Token
        for token in [
            self._token('b', '1'),
            self._token('c', '2'),
        ]:
            with self.subTest(token):
                self._test_rule(
                    Parser.Or('a',
                              [
                                  Parser.Literal('b'),
                                  Parser.Literal('c'),
                              ]
                              ),
                    [
                        token
                    ],
                    self._child_result(
                        'a',
                        [
                            self._token_result(token),
                        ]
                    )
                )

    def test_mismatch(self):
        tokens: Sequence[Lexer.Token]
        for tokens in [
            [self._token('d', '1')],
            [],
        ]:
            with self.subTest(tokens):
                with self.assertRaises(Parser.Error):
                    self._apply_rule(
                        Parser.Or('a',
                                  [
                                      Parser.Literal('b'),
                                      Parser.Literal('c'),
                                  ]
                                  ),
                        tokens,
                    )
