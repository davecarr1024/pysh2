from dataclasses import dataclass
from functools import cached_property
from typing import Sequence, Tuple
from unittest import TestCase

from . import processor

if 'unittest.util' in __import__('sys').modules:
    # Show full diff in self.assertEqual.
    __import__('sys').modules['unittest.util']._MAX_LENGTH = 999999999


Error = processor.Error


@dataclass(frozen=True)
class ResultValue:
    val: int


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


Result = processor.Result[ResultValue, State]

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
            return ResultAndState(Result(self, ResultValue(self.val), []), state.tail)
        raise RuleError(self, state)


And = processor.And[ResultValue, State]

Or = processor.Or[ResultValue, State]

ZeroOrMore = processor.ZeroOrMore[ResultValue, State]

OneOrMore = processor.OneOrMore[ResultValue, State]

ZeroOrOne = processor.ZeroOrOne[ResultValue, State]


class RuleWithName(Rule):
    def __eq__(self, rhs: object) -> bool:
        return isinstance(rhs, processor.Rule) and rhs.name == self.name

    def apply(self, state: State) -> ResultAndState:
        raise NotImplemented()


class IntMatcherTest(TestCase):
    def _rule_test(self, rule: Rule, input: Sequence[int], expected_result: Result) -> None:
        self.assertEqual(
            rule.apply(State(input)),
            ResultAndState(
                expected_result,
                State([])
            )
        )

    def _rule_tests(self, rule: Rule, cases: Sequence[Tuple[Sequence[int], Result]]) -> None:
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
            Result(RuleWithName('a'), ResultValue(1), [])
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
            Result(RuleWithName('a'), None, [
                Result(RuleWithName('b'), ResultValue(1), []),
                Result(RuleWithName('c'), ResultValue(2), []),
            ])
        )

    def test_and_mismatch(self):
        self._rule_error_tests(
            And(
                'a',
                [
                    Literal('b', 1),
                    Literal('c', 2),
                ]
            ),
            [
                [],
                [2],
                [3],
            ]
        )

    def test_or_match(self):
        self._rule_tests(
            Or(
                'a',
                [
                    Literal('b', 1),
                    Literal('c', 2),
                ]
            ),
            [
                (
                    [1],
                    Result(RuleWithName('a'), None, [
                           Result(RuleWithName('b'), ResultValue(1), [])])
                ),
                (
                    [2],
                    Result(RuleWithName('a'), None, [
                           Result(RuleWithName('c'), ResultValue(2), [])])
                ),
            ]
        )

    def test_or_mismatch(self):
        self._rule_error_tests(
            Or('a', [Literal('b', 1), Literal('c', 2)]),
            [[], [3]]
        )

    def test_zero_or_more_match(self):
        self._rule_tests(
            ZeroOrMore('a', Literal('b', 1)),
            [
                ([], Result(RuleWithName('a'), None, [])),
                ([1], Result(RuleWithName('a'), None, [
                 Result(RuleWithName('b'), ResultValue(1), [])])),
                ([1, 1], Result(RuleWithName('a'), None, [
                 Result(RuleWithName('b'), ResultValue(1), []), Result(RuleWithName('b'), ResultValue(1), [])])),
            ]
        )

    def test_one_or_more_match(self):
        self._rule_tests(
            OneOrMore('a', Literal('b', 1)),
            [
                ([1], Result(RuleWithName('a'), None, [
                 Result(RuleWithName('b'), ResultValue(1), [])])),
                ([1, 1], Result(RuleWithName('a'), None, [
                 Result(RuleWithName('b'), ResultValue(1), []), Result(RuleWithName('b'), ResultValue(1), [])])),
            ]
        )

    def test_one_or_more_mismatch(self):
        self._rule_error_tests(
            OneOrMore('a', Literal('b', 1)),
            [[], [2]]
        )

    def test_zero_or_one_match(self):
        self._rule_tests(
            ZeroOrOne('a', Literal('b', 1)),
            [
                ([], Result(RuleWithName('a'), None, [])),
                ([1], Result(RuleWithName('a'), None, [
                 Result(RuleWithName('b'), ResultValue(1), [])])),
            ]
        )
