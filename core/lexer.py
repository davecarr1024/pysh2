from dataclasses import dataclass
from functools import cached_property
from typing import Mapping, MutableMapping, MutableSequence, Sequence

from core import processor, stream_processor

Error = stream_processor.Error


@dataclass(frozen=True)
class _ResultValue(processor.ResultValue):
    value: str


@dataclass(frozen=True)
class Position:
    line: int
    column: int

    def after(self, value: str) -> 'Position':
        line: int = self.line
        column: int = self.column
        for c in value:
            if c == '\n':
                line += 1
                column = 0
            else:
                column += 1
        return Position(line, column)


@dataclass(frozen=True)
class _Item:
    value: str
    position: Position

    def __post_init__(self):
        if len(self.value) != 1:
            raise Error(msg=f'invalid lexer item {self.value}')


class StateValue(stream_processor.Stream[_Item]):
    def __repr__(self) -> str:
        if self.empty:
            return '[]'
        else:
            return (''.join([item.value for item in self._values[:10]])+f'@{self._values[0].position}')

    @property
    def tail(self) -> stream_processor.Stream[_Item]:
        return StateValue(super().tail._values)


Result = stream_processor.Result[_ResultValue]
State = stream_processor.State[_ResultValue, _Item]
ResultAndState = stream_processor.ResultAndState[_ResultValue, _Item]
Rule = stream_processor.Rule[_ResultValue, _Item]
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
    items: MutableSequence[_Item] = []
    position: Position = Position(0, 0)
    for c in s:
        items.append(_Item(c, position))
        position = position.after(c)
    return StateValue(items)


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

    def _token_stream_from_result(self, result: Result) -> TokenStream:
        token_results: Sequence[Result] = list(
            result.where(Result.rule_name_in(self.token_types)))
        return TokenStream(
            [
                token for token in
                [self._token_from_result(token_result)
                 for token_result in token_results]
                if not token.type.startswith('_')
            ]
        )

    def __init__(self, rules: Mapping[str, Rule]):
        processor_rules: MutableMapping[str, Rule] = dict(rules)
        processor_rules[_ROOT_RULE_NAME] = UntilEmpty(Ref(_RULES_RULE_NAME))
        processor_rules[_RULES_RULE_NAME] = Or(
            [Ref(rule_name) for rule_name in rules.keys()])
        super().__init__(_ROOT_RULE_NAME, processor_rules)

    def __repr__(self) -> str:
        return f'Lexer({self.token_rules})'

    @cached_property
    def token_rules(self) -> Mapping[str, Rule]:
        return {rule_name: rule for rule_name, rule in self.rules.items() if rule_name not in (_ROOT_RULE_NAME, _RULES_RULE_NAME)}

    @cached_property
    def token_types(self) -> Sequence[str]:
        return list(self.token_rules.keys())

    def apply(self, input: str) -> TokenStream:
        return self._token_stream_from_result(self.apply_root(load_state_value(input)).result)


@dataclass(frozen=True)
class HeadRule(stream_processor.HeadRule[_ResultValue, _Item]):
    def result(self, head: _Item) -> Result:
        return Result(value=_ResultValue(head.value))


@dataclass(frozen=True)
class Class(HeadRule):
    min: str
    max: str

    def __repr__(self) -> str:
        return f'[{self.min}-{self.max}]'

    def pred(self, head: _Item) -> bool:
        return self.min <= head.value <= self.max


@dataclass(frozen=True)
class Literal(HeadRule):
    value: str

    def __post_init__(self):
        assert len(self.value) == 1

    def __repr__(self):
        return self.value

    def pred(self, head: _Item) -> bool:
        return self.value == head.value


@dataclass(frozen=True)
class Not(Rule):
    child: Rule

    def __repr__(self) -> str:
        return f'^{self.child}'

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
