from dataclasses import dataclass
from functools import cached_property
from typing import Sequence

from . import processor


@dataclass(frozen=True)
class ResultValue(processor.ResultValue):
    value: str


@dataclass(frozen=True)
class State(processor.State):
    input: str
    pos: int = 0

    @property
    def empty(self) -> bool:
        return self.pos >= len(self.input)

    @cached_property
    def value(self) -> str:
        return self.input[self.pos:]

    def with_pos(self, pos: int) -> 'State':
        return State(self.input, pos)

    def after(self, result_value: ResultValue) -> 'State':
        if not self.value.startswith(result_value.value):
            raise ValueError(result_value)
        return self.with_pos(self.pos+len(result_value.value))


Error = processor.Error

RuleError = processor.RuleError[ResultValue, State]

NestedRuleError = processor.NestedRuleError[ResultValue, State]

Rule = processor.Rule[ResultValue, State]

And = processor.And[ResultValue, State]

Or = processor.Or[ResultValue, State]

ZeroOrMore = processor.ZeroOrMore[ResultValue, State]

OneOrMore = processor.OneOrMore[ResultValue, State]

ZeroOrOne = processor.ZeroOrOne[ResultValue, State]

Result = processor.Result[ResultValue, State]

ResultAndState = processor.ResultAndState[ResultValue, State]

UntilEmpty = processor.UntilEmpty[ResultValue, State]


@dataclass(frozen=True)
class Token:
    type: str
    value: str


@dataclass(frozen=True)
class TokenStream:
    tokens: Sequence[Token]
    pos: int = 0

    @cached_property
    def empty(self) -> bool:
        return self.pos >= len(self.tokens)

    @cached_property
    def head(self) -> Token:
        assert not self.empty
        return self.tokens[self.pos]

    @cached_property
    def tail(self) -> 'TokenStream':
        return TokenStream(self.tokens, self.pos+1)


_ROOT_RULE_NAME = '_root'
_RULES_RULE_NAME = '_rules'


@dataclass(frozen=True, init=False)
class Lexer(processor.Processor[ResultValue, State]):
    @staticmethod
    def _flatten_result_value(result: Result) -> str:
        value: str = ''
        if result.value is not None:
            value += result.value.value
        for child in result.children:
            value += Lexer._flatten_result_value(child)
        return value

    @staticmethod
    def _token_from_result(result: Result):
        assert result.rule.name == _RULES_RULE_NAME, result
        assert len(result.children) == 1, result
        rule_result: Result = result.children[0]
        assert rule_result.rule.name is not None, rule_result
        return Token(rule_result.rule.name, Lexer._flatten_result_value(rule_result))

    @staticmethod
    def _token_stream_from_result(result: Result) -> TokenStream:
        assert result.rule.name == _ROOT_RULE_NAME, result
        return TokenStream([Lexer._token_from_result(child) for child in result.children])

    def __init__(self, rules: Sequence[Rule]):
        assert all([rule.name is not None for rule in rules])
        super().__init__(_ROOT_RULE_NAME, [
            UntilEmpty(_ROOT_RULE_NAME, Or(_RULES_RULE_NAME, rules))])

    def apply(self, input: str) -> TokenStream:
        return self._token_stream_from_result(self._apply(State(input)))
