from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from typing import Generic, Mapping, MutableSequence, Optional, Sequence, TypeVar


ResultValue = TypeVar('ResultValue')

State = TypeVar('State')


@dataclass(frozen=True)
class Rule(ABC, Generic[ResultValue, State]):
    name: Optional[str]

    @abstractmethod
    def apply(self, state: State) -> 'ResultAndState[ResultValue, State]': ...


@dataclass(frozen=True)
class Result(Generic[ResultValue, State]):
    rule: Rule[ResultValue, State]
    value: Optional[ResultValue]
    children: Sequence['Result[ResultValue, State]']


@dataclass(frozen=True)
class ResultAndState(Generic[ResultValue, State]):
    result: Result[ResultValue, State]
    state: State


class Error(Exception):
    ...


@dataclass(frozen=True)
class RuleError(Error, Generic[ResultValue, State]):
    rule: Rule[ResultValue, State]
    state: State


@dataclass(frozen=True)
class NestedRuleError(RuleError[ResultValue, State]):
    child_errors: Sequence[Error]


@dataclass(frozen=True)
class Processor(Generic[ResultValue, State]):
    rules: Sequence[Rule[ResultValue, State]]
    root_rule_name: str

    @cached_property
    def rules_by_name(self) -> Mapping[str, Rule[ResultValue, State]]:
        return {rule.name: rule for rule in self.rules if rule.name is not None}

    @cached_property
    def root_rule(self) -> Rule[ResultValue, State]:
        return self.rules_by_name[self.root_rule_name]

    def _apply(self, state: State) -> Result[ResultValue, State]:
        return self.rules_by_name[self.root_rule_name].apply(state).result


@ dataclass(frozen=True)
class And(Rule[ResultValue, State]):
    children: Sequence[Rule[ResultValue, State]]

    def apply(self, state: State) -> ResultAndState[ResultValue, State]:
        child_results: MutableSequence[Result[ResultValue, State]] = []
        child_state: State = state
        for child in self.children:
            try:
                child_result: ResultAndState[ResultValue,
                                             State] = child.apply(child_state)
                child_results.append(child_result.result)
                child_state = child_result.state
            except Error as error:
                raise NestedRuleError(self, state, [error])
        return ResultAndState[ResultValue, State](Result[ResultValue, State](self, None, child_results), child_state)


@ dataclass(frozen=True)
class Or(Rule[ResultValue, State]):
    children: Sequence[Rule[ResultValue, State]]

    def apply(self, state: State) -> ResultAndState[ResultValue, State]:
        child_errors: MutableSequence[Error] = []
        for child in self.children:
            try:
                child_result: ResultAndState[ResultValue, State] = child.apply(
                    state)
                return ResultAndState[ResultValue, State](Result[ResultValue, State](self, None, [child_result.result]), child_result.state)
            except Error as error:
                child_errors.append(error)
        raise NestedRuleError(self, state, child_errors)


@dataclass(frozen=True)
class ZeroOrMore(Rule[ResultValue, State]):
    child: Rule[ResultValue, State]

    def apply(self, state: State) -> ResultAndState[ResultValue, State]:
        child_results: MutableSequence[Result[ResultValue, State]] = []
        child_state: State = state
        while True:
            try:
                child_result: ResultAndState[ResultValue,
                                             State] = self.child.apply(child_state)
                child_results.append(child_result.result)
                child_state = child_result.state
            except Error:
                break
        return ResultAndState[ResultValue, State](Result[ResultValue, State](self, None, child_results), child_state)


@dataclass(frozen=True)
class OneOrMore(Rule[ResultValue, State]):
    child: Rule[ResultValue, State]

    def apply(self, state: State) -> ResultAndState[ResultValue, State]:
        try:
            child_result: ResultAndState[ResultValue,
                                         State] = self.child.apply(state)
            child_results: MutableSequence[Result[ResultValue, State]] = [
                child_result.result]
            child_state: State = child_result.state
        except Error as error:
            raise NestedRuleError[ResultValue, State](self, state, [error])
        while True:
            try:
                child_result = self.child.apply(child_state)
                child_results.append(child_result.result)
                child_state = child_result.state
            except Error:
                break
        return ResultAndState[ResultValue, State](Result[ResultValue, State](self, None, child_results), child_state)


@dataclass(frozen=True)
class ZeroOrOne(Rule[ResultValue, State]):
    child: Rule[ResultValue, State]

    def apply(self, state: State) -> ResultAndState[ResultValue, State]:
        try:
            child_result: ResultAndState[ResultValue,
                                         State] = self.child.apply(state)
            return ResultAndState[ResultValue, State](Result[ResultValue, State](self, None, [child_result.result]), child_result.state)
        except Error:
            return ResultAndState[ResultValue, State](Result[ResultValue, State](self, None, []), state)
