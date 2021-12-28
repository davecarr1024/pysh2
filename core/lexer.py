from dataclasses import dataclass
from functools import cached_property
from typing import Mapping, MutableMapping, Sequence

from core import processor, stream_processor

Error = stream_processor.Error


@dataclass(frozen=True)
class _ResultValue(processor.ResultValue):
    value: str


@dataclass(frozen=True)
class _Item:
    value: str

    def __post_init__(self):
        if len(self.value) != 1:
            raise Error(msg=f'invalid lexer item {self.value}')


Result = stream_processor.Result[_ResultValue]
StateValue = stream_processor.Stream[_Item]
State = stream_processor.State[_ResultValue, _Item]
ResultAndState = stream_processor.ResultAndState[_ResultValue, _Item]
Rule = stream_processor.Rule[_ResultValue, _Item]
HeadRule = stream_processor.HeadRule[_ResultValue, _Item]
Ref = stream_processor.Ref[_ResultValue, _Item]
And = stream_processor.And[_ResultValue, _Item]
Or = stream_processor.Or[_ResultValue, _Item]
ZeroOrMore = stream_processor.ZeroOrMore[_ResultValue, _Item]
OneOrMore = stream_processor.OneOrMore[_ResultValue, _Item]
ZeroOrOne = stream_processor.ZeroOrOne[_ResultValue, _Item]
UntilEmpty = stream_processor.UntilEmpty[_ResultValue, _Item]


@dataclass(frozen=True)
class Token(processor.ResultValue):
    type: str
    value: str


TokenStream = stream_processor.Stream[Token]

_ROOT_RULE_NAME = '_root'
_RULES_RULE_NAME = '_rules'


def load_state_value(s: str) -> StateValue:
    return StateValue([_Item(c) for c in s])


@dataclass(frozen=True, init=False)
class Lexer(stream_processor.Processor[_ResultValue, _Item]):
    @staticmethod
    def _flatten_result_value(result: Result) -> str:
        value: str = ''
        if result.value is not None:
            value += result.value.value
        for child in result:
            value += Lexer._flatten_result_value(child)
        return value

    @staticmethod
    def _token_from_result(result: Result) -> Token:
        assert result.rule_name is not None, result
        return Token(result.rule_name, Lexer._flatten_result_value(result))

    def _is_token_result(self, result: Result) -> bool:
        return result.rule_name in self.token_types

    def _token_stream_from_result(self, result: Result) -> TokenStream:
        token_results: Sequence[Result] = list(
            result.where(self._is_token_result))
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
        return self._token_stream_from_result(self.apply_root(load_state_value(input)).result)


@dataclass(frozen=True)
class Class(HeadRule):
    min: str
    max: str

    def pred(self, head: _Item) -> bool:
        return self.min <= head.value <= self.max

    def result(self, head: _Item) -> Result:
        return Result(value=_ResultValue(head.value))


class Literal(stream_processor.Literal[_ResultValue, _Item]):
    def __init__(self, value: str):
        super().__init__(_Item(value))

    def result(self, head: _Item) -> Result:
        return Result(value=_ResultValue(head.value))


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
                Result(value=_ResultValue(state.value.head.value)),
                state.with_value(state.value.tail)
            )
        raise Error(msg=f'child applied: {child_result}')
