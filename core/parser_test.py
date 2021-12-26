from dataclasses import dataclass
from unittest import TestCase

from core import lexer, parser, processor

if 'unittest.util' in __import__('sys').modules:
    # Show full diff in self.assertEqual.
    __import__('sys').modules['unittest.util']._MAX_LENGTH = 999999999


@dataclass(frozen=True)
class RuleWithName(parser.Rule):
    name: str

    def __eq__(self, rhs: object) -> bool:
        return isinstance(rhs, processor.Rule) and rhs.name == self.name

    def apply(self, state: parser.State) -> parser.ResultAndState:
        raise NotImplemented()


class LiteralTest(TestCase):
    def test_match(self):
        self.assertEqual(
            parser.Literal('a', 'a').apply(
                parser.State(
                    [lexer.Token('a', 'b')]
                )
            ),
            parser.ResultAndState(
                parser.Result(
                    RuleWithName('a'),
                    lexer.Token('a', 'b'),
                    []
                ),
                parser.State([]))
        )
