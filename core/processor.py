from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass, field
from functools import cached_property
from typing import Generic, Mapping, MutableSequence, Optional, Sequence, TypeVar


class ResultValue:
    ...


_ResultValueType = TypeVar('_ResultValueType', bound=ResultValue)


class State(ABC):
    @abstractproperty
    def empty(self) -> bool: ...


_StateType = TypeVar('_StateType', bound=State)


@dataclass(frozen=True)
class Rule(ABC, Generic[_ResultValueType, _StateType]):
    name: Optional[str]

    @abstractmethod
    def apply(self, state: _StateType) -> 'ResultAndState[_ResultValueType, _StateType]':
        ...


@dataclass(frozen=True)
class Result(Generic[_ResultValueType, _StateType]):
    rule: Rule[_ResultValueType, _StateType]
    value: Optional[_ResultValueType]
    children: Sequence['Result[_ResultValueType, _StateType]']


@dataclass(frozen=True)
class ResultAndState(Generic[_ResultValueType, _StateType]):
    result: Result[_ResultValueType, _StateType]
    state: _StateType


@dataclass(frozen=True)
class Error(Exception):
    msg: Optional[str] = field(default=None, kw_only=True)


@dataclass(frozen=True)
class RuleError(Error, Generic[_ResultValueType, _StateType]):
    rule: Rule[_ResultValueType, _StateType]
    state: _StateType


@dataclass(frozen=True)
class NestedRuleError(RuleError[_ResultValueType, _StateType]):
    child_errors: Sequence[Error]


@dataclass(frozen=True)
class Processor(Generic[_ResultValueType, _StateType]):
    root_rule_name: str
    rules: Sequence[Rule[_ResultValueType, _StateType]]

    @cached_property
    def rules_by_name(self) -> Mapping[str, Rule[_ResultValueType, _StateType]]:
        return {rule.name: rule for rule in self.rules if rule.name is not None}

    @cached_property
    def root_rule(self) -> Rule[_ResultValueType, _StateType]:
        return self.rules_by_name[self.root_rule_name]

    def _apply(self, state: _StateType) -> Result[_ResultValueType, _StateType]:
        return self.rules_by_name[self.root_rule_name].apply(state).result


@ dataclass(frozen=True)
class And(Rule[_ResultValueType, _StateType]):
    children: Sequence[Rule[_ResultValueType, _StateType]]

    def apply(self, state: _StateType) -> ResultAndState[_ResultValueType, _StateType]:
        child_results: MutableSequence[Result[_ResultValueType, _StateType]] = [
        ]
        child_state: _StateType = state
        for child in self.children:
            try:
                child_result: ResultAndState[_ResultValueType,
                                             _StateType] = child.apply(child_state)
                child_results.append(child_result.result)
                child_state = child_result.state
            except Error as error:
                raise NestedRuleError(self, state, [error])
        return ResultAndState[_ResultValueType, _StateType](Result[_ResultValueType, _StateType](self, None, child_results), child_state)


@ dataclass(frozen=True, repr=False)
class Or(Rule[_ResultValueType, _StateType]):
    children: Sequence[Rule[_ResultValueType, _StateType]]

    def apply(self, state: _StateType) -> ResultAndState[_ResultValueType, _StateType]:
        child_errors: MutableSequence[Error] = []
        for child in self.children:
            try:
                child_result: ResultAndState[_ResultValueType, _StateType] = child.apply(
                    state)
                return ResultAndState[_ResultValueType, _StateType](Result[_ResultValueType, _StateType](self, None, [child_result.result]), child_result.state)
            except Error as error:
                child_errors.append(error)
        raise NestedRuleError(self, state, child_errors)


@dataclass(frozen=True)
class ZeroOrMore(Rule[_ResultValueType, _StateType]):
    child: Rule[_ResultValueType, _StateType]

    def apply(self, state: _StateType) -> ResultAndState[_ResultValueType, _StateType]:
        child_results: MutableSequence[Result[_ResultValueType, _StateType]] = [
        ]
        child_state: _StateType = state
        while True:
            try:
                child_result: ResultAndState[_ResultValueType,
                                             _StateType] = self.child.apply(child_state)
                child_results.append(child_result.result)
                child_state = child_result.state
            except Error:
                break
        return ResultAndState[_ResultValueType, _StateType](Result[_ResultValueType, _StateType](self, None, child_results), child_state)


@dataclass(frozen=True)
class OneOrMore(Rule[_ResultValueType, _StateType]):
    child: Rule[_ResultValueType, _StateType]

    def apply(self, state: _StateType) -> ResultAndState[_ResultValueType, _StateType]:
        try:
            child_result: ResultAndState[_ResultValueType,
                                         _StateType] = self.child.apply(state)
            child_results: MutableSequence[Result[_ResultValueType, _StateType]] = [
                child_result.result]
            child_state: _StateType = child_result.state
        except Error as error:
            raise NestedRuleError[_ResultValueType, _StateType](
                self, state, [error])
        while True:
            try:
                child_result = self.child.apply(child_state)
                child_results.append(child_result.result)
                child_state = child_result.state
            except Error:
                break
        return ResultAndState[_ResultValueType, _StateType](Result[_ResultValueType, _StateType](self, None, child_results), child_state)


@dataclass(frozen=True)
class ZeroOrOne(Rule[_ResultValueType, _StateType]):
    child: Rule[_ResultValueType, _StateType]

    def apply(self, state: _StateType) -> ResultAndState[_ResultValueType, _StateType]:
        try:
            child_result: ResultAndState[_ResultValueType,
                                         _StateType] = self.child.apply(state)
            return ResultAndState[_ResultValueType, _StateType](Result[_ResultValueType, _StateType](self, None, [child_result.result]), child_result.state)
        except Error:
            return ResultAndState[_ResultValueType, _StateType](Result[_ResultValueType, _StateType](self, None, []), state)


@dataclass(frozen=True)
class UntilEmpty(Rule[_ResultValueType, _StateType]):
    child: Rule[_ResultValueType, _StateType]

    def apply(self, state: _StateType) -> ResultAndState[_ResultValueType, _StateType]:
        child_state: _StateType = state
        child_results: MutableSequence[Result[_ResultValueType, _StateType]] = [
        ]
        while not child_state.empty:
            try:
                child_result: ResultAndState[_ResultValueType, _StateType] = self.child.apply(
                    child_state)
                child_state = child_result.state
                child_results.append(child_result.result)
            except Error as error:
                raise NestedRuleError(self, state, [error])
        return ResultAndState(Result(self, None, child_results), child_state)
