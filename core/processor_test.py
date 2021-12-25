from dataclasses import dataclass
from functools import cached_property
from typing import Sequence, Tuple
from unittest import TestCase

from . import processor


Error = processor.Error


@dataclass(frozen=True)
class ResultValue:
    val: int


Result = processor.Result[ResultValue]


@dataclass(frozen=True)
class State:
    vals: Sequence[int]

    @cached_property
    def empty(self) -> bool:
        return not self.vals

    @cached_property
    def head(self) -> int:
        assert not self.empty
        return self.vals[0]

    @cached_property
    def tail(self) -> 'State':
        return State(self.vals[1:])


ResultAndState = processor.ResultAndState[ResultValue, State]

Rule = processor.Rule[ResultValue, State]

RuleError = processor.RuleError[ResultValue, State]

NestedRuleError = processor.NestedRuleError[ResultValue, State]


class IntMatcher(processor.Processor[ResultValue, State]):
    pass


@dataclass(frozen=True)
class Literal(Rule):
    val: int

    def apply(self, state: State) -> ResultAndState:
        if not state.empty and state.head == self.val:
            return ResultAndState(Result(self.name, ResultValue(self.val), []), state.tail)
        raise RuleError(self, state)


And = processor.And[ResultValue, State]


class IntMatcherTest(TestCase):
    def _rule_test(self, rule: processor.Rule[ResultValue, State], input: Sequence[int], result: processor.Result[ResultValue]) -> None:
        self.assertEqual(
            rule.apply(State(input)),
            processor.ResultAndState[ResultValue, State](
                result,
                State([])
            )
        )

    def _rule_tests(self, rule: processor.Rule[ResultValue, State], cases: Sequence[Tuple[Sequence[int], processor.Result[ResultValue]]]) -> None:
        for case in cases:
            with self.subTest(case):
                self._rule_test(rule, *case)

    def _rule_error_test(self, rule: processor.Rule[ResultValue, State], input: Sequence[int]) -> None:
        with self.assertRaises(processor.RuleError):
            rule.apply(State(input))

    def _rule_error_tests(self, rule: processor.Rule[ResultValue, State], inputs: Sequence[Sequence[int]]) -> None:
        for input in inputs:
            with self.subTest(input):
                self._rule_error_test(rule, input)

    def test_literal_match(self):
        self._rule_test(
            Literal('a', 1),
            [1],
            Result(
                'a',
                ResultValue(1),
                []
            )
        )

    def test_literal_mismatch(self):
        self._rule_error_tests(
            Literal('a', 1),
            [
                [],
                [2],
            ]
        )

    def test_and_match(self):
        self._rule_test(
            And(
                'a',
                [
                    Literal('b', 1),
                    Literal('c', 2),
                ]
            ),
            [1, 2],
            Result('a', None, [
                Result('b', ResultValue(1), []),
                Result('c', ResultValue(2), []),
            ])
        )
