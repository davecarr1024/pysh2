from dataclasses import dataclass
from functools import cached_property
from typing import Mapping, MutableMapping, Sequence

from core import processor


@dataclass(frozen=True)
class ResultValue(processor.ResultValue):
    value: str


@dataclass(frozen=True)
class StateValue(processor.StateValue):
    input: str
    pos: int = 0

    @property
    def empty(self) -> bool:
        return self.pos >= len(self.input)

    @cached_property
    def head(self) -> str:
        assert not self.empty
        return self.input[self.pos]

    @cached_property
    def tail(self) -> 'StateValue':
        assert not self.empty
        return StateValue(self.input, self.pos+1)


Error = processor.Error

Rule = processor.Rule[ResultValue, StateValue]

Ref = processor.Ref[ResultValue, StateValue]

And = processor.And[ResultValue, StateValue]

Or = processor.Or[ResultValue, StateValue]

ZeroOrMore = processor.ZeroOrMore[ResultValue, StateValue]

OneOrMore = processor.OneOrMore[ResultValue, StateValue]

ZeroOrOne = processor.ZeroOrOne[ResultValue, StateValue]

Result = processor.Result[ResultValue]

State = processor.State[ResultValue, StateValue]

ResultAndState = processor.ResultAndState[ResultValue, StateValue]

UntilEmpty = processor.UntilEmpty[ResultValue, StateValue]


@dataclass(frozen=True)
class Token(processor.ResultValue):
    type: str
    value: str


@dataclass(frozen=True)
class TokenStream(processor.StateValue):
    tokens: Sequence[Token]

    @property
    def empty(self) -> bool:
        return not self.tokens

    @cached_property
    def head(self) -> Token:
        assert not self.empty
        return self.tokens[0]

    @cached_property
    def tail(self) -> 'TokenStream':
        assert not self.empty
        return TokenStream(self.tokens[1:])


_ROOT_RULE_NAME = '_root'
_RULES_RULE_NAME = '_rules'


@dataclass(frozen=True, init=False)
class Lexer(processor.Processor[ResultValue, StateValue]):
    @staticmethod
    def _flatten_result_value(result: Result) -> str:
        value: str = ''
        if result.value is not None:
            value += result.value.value
        for child in result.children:
            value += Lexer._flatten_result_value(child)
        return value

    @staticmethod
    def _token_from_result(result: Result) -> Token:
        assert result.rule_name is not None, result
        return Token(result.rule_name, Lexer._flatten_result_value(result))

    def _is_token_result(self, result: Result) -> bool:
        return result.rule_name in self.token_types

    def _token_stream_from_result(self, result: Result) -> TokenStream:
        token_results: Sequence[Result] = result.where(
            self._is_token_result).children
        return TokenStream([Lexer._token_from_result(token_result) for token_result in token_results])

    def __init__(self, rules: Mapping[str, Rule]):
        processor_rules: MutableMapping[str, Rule] = dict(rules)
        processor_rules[_ROOT_RULE_NAME] = UntilEmpty(Ref(_RULES_RULE_NAME))
        processor_rules[_RULES_RULE_NAME] = Or(
            [Ref(rule_name) for rule_name in rules.keys()])
        super().__init__(_ROOT_RULE_NAME, processor_rules)

    @cached_property
    def token_types(self) -> Sequence[str]:
        return [rule_name for rule_name in self.rules.keys() if rule_name not in (_ROOT_RULE_NAME, _RULES_RULE_NAME)]

    def apply(self, input: str) -> TokenStream:
        return self._token_stream_from_result(self.apply_root(StateValue(input)).result)


@dataclass(frozen=True)
class StartsWith(Rule):
    value: str

    def apply(self, state: State) -> ResultAndState:
        if state.value.empty:
            raise Error(msg=f'state empty')
        elif self.value == state.value.head:
            return ResultAndState(
                Result(value=ResultValue(self.value)),
                state.with_value(state.value.tail)
            )
        else:
            raise Error(
                msg=f'startswith mismatch expected {repr(self.value)} got {repr(state.value.head)}')


@dataclass(frozen=True)
class Not(Rule):
    child: Rule

    def apply(self, state: State) -> ResultAndState:
        if state.value.empty:
            raise Error(msg='state empty')
        try:
            child_result: ResultAndState = self.child.apply(state)
        except Error:
            return ResultAndState(
                Result(value=ResultValue(state.value.head)),
                state.with_value(state.value.tail)
            )
        raise Error(msg=f'child applied: {child_result}')
