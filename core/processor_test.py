from dataclasses import dataclass, field
from functools import cached_property
from typing import Generic, Optional, Sequence, TypeVar
import unittest

from core import processor

if 'unittest.util' in __import__('sys').modules:
    # Show full diff in self.assertEqual.
    __import__('sys').modules['unittest.util']._MAX_LENGTH = 999999999

_ResultValueType = TypeVar('_ResultValueType', bound=processor.ResultValue)
_StateValueType = TypeVar('_StateValueType', bound=processor.StateValue)


@dataclass(frozen=True)
class ResultMatcher(Generic[_ResultValueType]):
    value: Optional[_ResultValueType] = field(default=None, kw_only=True)
    rule_name: Optional[str] = field(default=None, kw_only=True)
    children: Sequence['ResultMatcher[_ResultValueType]'] = field(
        kw_only=True,
        default_factory=lambda: list[ResultMatcher[_ResultValueType]]())


@dataclass(frozen=True)
class ResultAndStateMatcher(Generic[_ResultValueType, _StateValueType]):
    result: ResultMatcher[_ResultValueType]
    state_value: Optional[_StateValueType] = None


@dataclass(frozen=True)
class ApplyEqualsCase(Generic[_ResultValueType, _StateValueType]):
    input_state_value: _StateValueType
    expected_output: ResultAndStateMatcher[_ResultValueType, _StateValueType]


@dataclass(frozen=True)
class ErrorMatcher:
    msg: Optional[str] = field(default=None, kw_only=True)
    rule_name: Optional[str] = field(default=None, kw_only=True)

    def assertMatches(self, test: unittest.TestCase, error: processor.Error) -> None:
        test.assertEqual(self.msg, error.msg)
        test.assertEqual(self.rule_name, error.rule_name)


@dataclass(frozen=True)
class ApplyRaisesCase(Generic[_StateValueType]):
    input_state_value: _StateValueType
    expected_error: Optional[processor.Error] = None


class ProcessorTest(unittest.TestCase, Generic[_ResultValueType, _StateValueType]):
    def assertResultEquals(
        self,
        result: processor.Result[_ResultValueType],
        matcher: ResultMatcher[_ResultValueType]
    ) -> None:
        self.assertEquals(result.value, matcher.value, result)
        self.assertEquals(result.rule_name, matcher.rule_name, result)
        self.assertEquals(len(result.children), len(matcher.children), result)
        result_child: processor.Result[_ResultValueType]
        matcher_child: ResultMatcher[_ResultValueType]
        for result_child, matcher_child in zip(result.children, matcher.children):
            self.assertResultEquals(result_child, matcher_child)

    def assertResultAndStateEquals(
        self,
        result_and_state: processor.ResultAndState[_ResultValueType, _StateValueType],
        matcher: ResultAndStateMatcher[_ResultValueType, _StateValueType]
    ):
        self.assertResultEquals(result_and_state.result, matcher.result)
        if matcher.state_value is not None:
            self.assertEquals(matcher.state_value,
                              result_and_state.state.value)

    def assertApplyEquals(
        self,
        processor_: processor.Processor[_ResultValueType, _StateValueType],
        case: ApplyEqualsCase[_ResultValueType, _StateValueType]
    ):
        self.assertResultAndStateEquals(processor_.apply_root(
            case.input_state_value), case.expected_output)

    def assertApplyEqualsCases(
        self,
        processor_: processor.Processor[_ResultValueType, _StateValueType],
        cases: Sequence[ApplyEqualsCase[_ResultValueType, _StateValueType]]
    ):
        for case in cases:
            with self.subTest(case):
                self.assertApplyEquals(processor_, case)

    def assertApplyRaises(
        self,
        processor_: processor.Processor[_ResultValueType, _StateValueType],
        case: ApplyRaisesCase[_StateValueType]
    ):
        with self.assertRaises(processor.Error) as cm:
            processor_.apply_root(case.input_state_value)
        if case.expected_error is not None:
            self.assertEquals(case.expected_error, cm.exception)

    def assertApplyRaisesCases(
        self,
        processor_: processor.Processor[_ResultValueType, _StateValueType],
        cases: Sequence[ApplyRaisesCase[_StateValueType]]
    ) -> None:
        for case in cases:
            with self.subTest(case):
                self.assertApplyRaises(processor_, case)


@dataclass(frozen=True)
class _ResultValue(processor.ResultValue):
    value: int


_Result = processor.Result[_ResultValue]


class ResultTest(unittest.TestCase):
    def test_with_rule_name(self):
        self.assertEqual(
            _Result(
                value=_ResultValue(1),
                children=[
                    _Result(value=_ResultValue(2)),
                ]
            ).with_rule_name('a'),
            _Result(
                value=_ResultValue(1),
                children=[
                    _Result(value=_ResultValue(2)),
                ],
                rule_name='a'
            )
        )

    def test_where_rule_name_is(self):
        self.assertEqual(
            _Result(
                children=[
                    _Result(
                        rule_name='a',
                        value=_ResultValue(1),
                    ),
                    _Result(
                        rule_name='b',
                        value=_ResultValue(2),
                    ),
                ]
            ).where(_Result.rule_name_is('a')),
            _Result(
                children=[
                    _Result(
                        rule_name='a',
                        value=_ResultValue(1),
                    ),
                ]
            )
        )

    def test_has_value(self):
        self.assertEqual(
            _Result(
                children=[
                    _Result(
                        rule_name='a',
                    ),
                    _Result(
                        rule_name='b',
                        value=_ResultValue(1),
                    ),
                ]
            ).where(_Result.has_value),
            _Result(
                children=[
                    _Result(
                        rule_name='b',
                        value=_ResultValue(1),
                    )
                ]
            )
        )

    def test_has_rule_name(self):
        self.assertEqual(
            _Result(
                children=[
                    _Result(
                        value=_ResultValue(1),
                    ),
                    _Result(
                        rule_name='b',
                        value=_ResultValue(2),
                    ),
                ]
            ).where(_Result.has_rule_name),
            _Result(
                children=[
                    _Result(
                        rule_name='b',
                        value=_ResultValue(2),
                    )
                ]
            )
        )

    def test_where_children(self):
        result: _Result = _Result(
            rule_name='a',
            value=_ResultValue(1),
            children=[
                _Result(
                    rule_name='a',
                    value=_ResultValue(2),
                ),
            ]
        )
        self.assertEqual(
            result.where(_Result.rule_name_is('a')),
            _Result(children=[result])
        )
        self.assertEqual(
            result.where_children(_Result.rule_name_is('a')),
            _Result(children=[_Result(rule_name='a', value=_ResultValue(2))])
        )

    def test_skip(self):
        result: _Result = _Result(
            rule_name='a',
            value=_ResultValue(1),
            children=[
                _Result(
                    rule_name='a',
                    value=_ResultValue(2),
                ),
            ]
        )
        self.assertEqual(
            result.where(_Result.rule_name_is('a')),
            _Result(children=[result])
        )
        self.assertEqual(
            result.skip().where(_Result.rule_name_is('a')),
            _Result(children=[_Result(rule_name='a', value=_ResultValue(2))])
        )

    def test_where_n(self):
        result: _Result = _Result(
            children=[
                _Result(rule_name='a'),
                _Result(rule_name='a'),
            ]
        )
        with self.assertRaises(processor.Error):
            result.where_n(1, _Result.rule_name_is('a'))
        self.assertEqual(result, result.where_n(2, _Result.rule_name_is('a')))

    def test_where_one(self):
        self.assertEqual(
            _Result(
                children=[
                    _Result(rule_name='a', value=_ResultValue(1)),
                    _Result(rule_name='b', value=_ResultValue(2)),
                ]
            ).where_one(_Result.rule_name_is('a')),
            _Result(rule_name='a', value=_ResultValue(1))
        )


@dataclass(frozen=True)
class _StateValue(processor.StateValue):
    values: Sequence[int]

    @property
    def empty(self) -> bool:
        return not self.values

    @cached_property
    def head(self) -> int:
        assert not self.empty
        return self.values[0]

    @cached_property
    def tail(self) -> '_StateValue':
        assert not self.empty
        return _StateValue(self.values[1:])


@dataclass(frozen=True)
class _IntMatcher(processor.Processor[_ResultValue, _StateValue]):
    ...


_Rule = processor.Rule[_ResultValue, _StateValue]
_State = processor.State[_ResultValue, _StateValue]
_ResultAndState = processor.ResultAndState[_ResultValue,
                                           _StateValue]
_ApplyEqualsCase = ApplyEqualsCase[_ResultValue, _StateValue]
_ApplyRaisesCase = ApplyRaisesCase[_StateValue]
_ResultMatcher = ResultMatcher[_ResultValue]
_ResultAndStateMatcher = ResultAndStateMatcher[_ResultValue,
                                               _StateValue]
_Ref = processor.Ref[_ResultValue, _StateValue]
_And = processor.And[_ResultValue, _StateValue]
_Or = processor.Or[_ResultValue, _StateValue]
_ZeroOrMore = processor.ZeroOrMore[_ResultValue, _StateValue]
_OneOrMore = processor.OneOrMore[_ResultValue, _StateValue]
_ZeroOrOne = processor.ZeroOrOne[_ResultValue, _StateValue]
_UntilEmpty = processor.UntilEmpty[_ResultValue, _StateValue]


@dataclass(frozen=True)
class _IntMatcherLiteral(_Rule):
    value: int

    def apply(self, state: _State) -> _ResultAndState:
        if state.value.empty:
            raise processor.Error(msg='state empty')
        elif state.value.head != self.value:
            raise processor.Error(
                msg=f'literal mismatch expected {self.value} got {state.value.head}')
        else:
            return _ResultAndState(_Result(value=_ResultValue(state.value.head)), state.with_value(state.value.tail))


class IntMatcherTest(ProcessorTest[_ResultValue, _StateValue]):
    def test_literal_match(self):
        self.assertApplyEqualsCases(
            _IntMatcher(
                'a',
                {'a': _IntMatcherLiteral(1)}
            ),
            [
                _ApplyEqualsCase(
                    _StateValue([1]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            value=_ResultValue(1),
                            rule_name='a'
                        )
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([1, 2]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            value=_ResultValue(1),
                            rule_name='a'),
                        state_value=_StateValue([2])
                    )
                ),
            ]
        )

    def test_literal_mismatch(self):
        self.assertApplyRaisesCases(
            _IntMatcher(
                'a',
                {'a': _IntMatcherLiteral(1)}
            ),
            [
                _ApplyRaisesCase(
                    _StateValue([]),
                    processor.Error(msg='state empty', rule_name='a')
                ),
                _ApplyRaisesCase(
                    _StateValue([2]),
                    processor.Error(
                        msg='literal mismatch expected 1 got 2', rule_name='a')
                )
            ]
        )

    def test_ref_match(self):
        self.assertApplyEqualsCases(
            _IntMatcher(
                'a',
                {
                    'a': _Ref('b'),
                    'b': _IntMatcherLiteral(1),
                }
            ),
            [
                _ApplyEqualsCase(
                    _StateValue([1]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(
                                    rule_name='b',
                                    value=_ResultValue(1),
                                ),
                            ]
                        )
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([1, 2]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(
                                    rule_name='b',
                                    value=_ResultValue(1),
                                ),
                            ]
                        ),
                        _StateValue([2])
                    )
                ),
            ]
        )

    def test_ref_mismatch(self):
        self.assertApplyRaisesCases(
            _IntMatcher(
                'a',
                {
                    'a': _Ref('b'),
                    'b': _IntMatcherLiteral(1),
                }
            ),
            [
                _ApplyRaisesCase(
                    _StateValue([]),
                    processor.Error(
                        rule_name='a',
                        children=[
                            processor.Error(rule_name='b', msg='state empty')
                        ]
                    )
                ),
                _ApplyRaisesCase(
                    _StateValue([2]),
                    processor.Error(
                        rule_name='a',
                        children=[
                            processor.Error(
                                rule_name='b',
                                msg='literal mismatch expected 1 got 2'
                            )
                        ]
                    )
                ),
            ]
        )

    def test_and_match(self):
        self.assertApplyEqualsCases(
            _IntMatcher(
                'a',
                {
                    'a': _And(
                        [
                            _IntMatcherLiteral(1),
                            _IntMatcherLiteral(2),
                        ]
                    )
                }
            ),
            [
                _ApplyEqualsCase(
                    _StateValue([1, 2]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(
                                    value=_ResultValue(1),
                                ),
                                _ResultMatcher(
                                    value=_ResultValue(2),
                                )
                            ]
                        )
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([1, 2, 3]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(
                                    value=_ResultValue(1),
                                ),
                                _ResultMatcher(
                                    value=_ResultValue(2),
                                )
                            ]
                        ),
                        _StateValue([3])
                    )
                ),
            ]
        )

    def test_and_mismatch(self):
        self.assertApplyRaisesCases(
            _IntMatcher(
                'a',
                {
                    'a': _And(
                        [
                            _IntMatcherLiteral(1),
                            _IntMatcherLiteral(2),
                        ]
                    )
                }
            ),
            [
                _ApplyRaisesCase(
                    _StateValue([]),
                    processor.Error(msg='state empty', rule_name='a')
                ),
                _ApplyRaisesCase(
                    _StateValue([2]),
                    processor.Error(
                        msg='literal mismatch expected 1 got 2', rule_name='a')
                ),
                _ApplyRaisesCase(
                    _StateValue([1, 1]),
                    processor.Error(
                        msg='literal mismatch expected 2 got 1', rule_name='a')
                ),
            ]
        )

    def test_or_match(self):
        self.assertApplyEqualsCases(
            _IntMatcher(
                'a',
                {
                    'a': _Or(
                        [
                            _IntMatcherLiteral(1),
                            _IntMatcherLiteral(2),
                        ]
                    )
                }
            ),
            [
                _ApplyEqualsCase(
                    _StateValue([1]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(value=_ResultValue(1)),
                            ]
                        )
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([1, 3]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(value=_ResultValue(1)),
                            ]
                        ),
                        _StateValue([3])
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([2]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(value=_ResultValue(2)),
                            ]
                        )
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([2, 3]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(value=_ResultValue(2)),
                            ]
                        ),
                        _StateValue([3])
                    )
                ),
            ]
        )

    def test_or_mismatch(self):
        self.assertApplyRaisesCases(
            _IntMatcher(
                'a',
                {
                    'a': _Or(
                        [
                            _IntMatcherLiteral(1),
                            _IntMatcherLiteral(2),
                        ]
                    )
                }
            ),
            [
                _ApplyRaisesCase(
                    _StateValue([3]),
                    processor.Error(
                        rule_name='a',
                        children=[
                            processor.Error(
                                msg='literal mismatch expected 1 got 3'),
                            processor.Error(
                                msg='literal mismatch expected 2 got 3'),
                        ]
                    )
                ),
            ]
        )

    def test_zero_or_more_match(self):
        self.assertApplyEqualsCases(
            _IntMatcher(
                'a',
                {
                    'a': _ZeroOrMore(_IntMatcherLiteral(1))
                }
            ),
            [
                _ApplyEqualsCase(
                    _StateValue([]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[]
                        )
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([1]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(value=_ResultValue(1)),
                            ]
                        )
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([1, 1]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(value=_ResultValue(1)),
                                _ResultMatcher(value=_ResultValue(1)),
                            ]
                        )
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([1, 1, 2]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(value=_ResultValue(1)),
                                _ResultMatcher(value=_ResultValue(1)),
                            ]
                        ),
                        _StateValue([2])
                    )
                ),
            ]
        )

    def test_one_or_more_match(self):
        self.assertApplyEqualsCases(
            _IntMatcher(
                'a',
                {'a': _OneOrMore(_IntMatcherLiteral(1))}
            ),
            [
                _ApplyEqualsCase(
                    _StateValue([1]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(value=_ResultValue(1)),
                            ]
                        )
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([1, 1]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(value=_ResultValue(1)),
                                _ResultMatcher(value=_ResultValue(1)),
                            ]
                        )
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([1, 1, 2]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(value=_ResultValue(1)),
                                _ResultMatcher(value=_ResultValue(1)),
                            ]
                        ),
                        _StateValue([2])
                    )
                ),
            ]
        )

    def test_one_or_more_mismatch(self):
        self.assertApplyRaisesCases(
            _IntMatcher('a', {'a': _OneOrMore(_IntMatcherLiteral(1))}),
            [
                _ApplyRaisesCase(
                    _StateValue([]),
                    processor.Error(
                        rule_name='a',
                        msg='state empty'
                    )
                ),
                _ApplyRaisesCase(
                    _StateValue([2]),
                    processor.Error(
                        rule_name='a',
                        msg='literal mismatch expected 1 got 2'
                    )
                ),
            ]
        )

    def test_zero_or_one_match(self):
        self.assertApplyEqualsCases(
            _IntMatcher('a', {'a': _ZeroOrOne(_IntMatcherLiteral(1))}),
            [
                _ApplyEqualsCase(
                    _StateValue([]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(rule_name='a'),
                        _StateValue([])
                    ),
                ),
                _ApplyEqualsCase(
                    _StateValue([1]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(
                                    value=_ResultValue(1)),
                            ],
                        ),
                        _StateValue([])
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([2]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(rule_name='a'),
                        _StateValue([2])
                    ),
                ),
                _ApplyEqualsCase(
                    _StateValue([1, 2]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(
                                    value=_ResultValue(1)),
                            ],
                        ),
                        _StateValue([2])
                    )
                ),
            ]
        )

    def test_until_empty_match(self):
        self.assertApplyEqualsCases(
            _IntMatcher('a', {'a': _UntilEmpty(_IntMatcherLiteral(1))}),
            [
                _ApplyEqualsCase(
                    _StateValue([]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(rule_name='a')
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([1]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(value=_ResultValue(1)),
                            ]
                        )
                    )
                ),
                _ApplyEqualsCase(
                    _StateValue([1, 1]),
                    _ResultAndStateMatcher(
                        _ResultMatcher(
                            rule_name='a',
                            children=[
                                _ResultMatcher(value=_ResultValue(1)),
                                _ResultMatcher(value=_ResultValue(1)),
                            ]
                        )
                    )
                ),
            ]
        )

    def test_until_empty_mismatch(self):
        self.assertApplyRaisesCases(
            _IntMatcher('a', {'a': _UntilEmpty(_IntMatcherLiteral(1))}),
            [
                _ApplyRaisesCase(
                    _StateValue([2]),
                    processor.Error(
                        rule_name='a',
                        msg='literal mismatch expected 1 got 2'
                    )
                )
            ]
        )
