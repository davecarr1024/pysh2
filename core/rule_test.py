from dataclasses import dataclass
from typing import Generic, Sequence, Tuple, TypeVar
from unittest.case import TestCase

from core import processor

_ResultValueType = TypeVar(
    '_ResultValueType', bound=processor.ResultValue)

_StateType = TypeVar('_StateType', bound=processor.State)


@dataclass(frozen=True)
class RuleWithName(processor.Rule[_ResultValueType, _StateType]):
    name: str

    def __eq__(self, rhs: object) -> bool:
        return isinstance(rhs, processor.Rule) and rhs.name == self.name

    def apply(self, state: _StateType) -> processor.ResultAndState[_ResultValueType, _StateType]:
        raise NotImplemented()


class RuleTest(TestCase, Generic[_ResultValueType, _StateType]):
    def _rule_test(self,
                   rule: processor.Rule[_ResultValueType, _StateType],
                   input_state: _StateType,
                   expected_result: processor.Result[_ResultValueType, _StateType],
                   expected_state: _StateType
                   ) -> None:
        self.assertEqual(
            rule.apply(input_state),
            processor.ResultAndState[_ResultValueType, _StateType](
                expected_result,
                expected_state
            )
        )

    def _rule_tests(self,
                    rule: processor.Rule[_ResultValueType, _StateType],
                    cases: Sequence[Tuple[_StateType,
                                          processor.Result[_ResultValueType, _StateType], _StateType]]
                    ) -> None:
        for case in cases:
            with self.subTest(case):
                self._rule_test(rule, *case)

    def _rule_error_test(self,
                         rule: processor.Rule[_ResultValueType, _StateType],
                         input_state: _StateType
                         ) -> None:
        with self.assertRaises(processor.Error):
            rule.apply(input_state)

    def _rule_error_tests(self,
                          rule: processor.Rule[_ResultValueType, _StateType],
                          input_states: Sequence[_StateType]
                          ) -> None:
        for input_state in input_states:
            with self.subTest(input_state):
                self._rule_error_test(rule, input_state)
