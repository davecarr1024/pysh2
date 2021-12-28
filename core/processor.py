from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass, field
from typing import Callable, Generic, Iterator, Mapping, MutableSequence, Optional, Sequence, TypeVar


class ResultValue:
    ...


_ResultValueType = TypeVar('_ResultValueType', bound=ResultValue)


@dataclass(frozen=True)
class Result(Generic[_ResultValueType]):
    rule_name: Optional[str] = field(default=None, kw_only=True)
    value: Optional[_ResultValueType] = field(kw_only=True, default=None)
    children: Sequence['Result[_ResultValueType]'] = field(
        kw_only=True, default_factory=lambda: list[Result[_ResultValueType]]())

    def __iter__(self) -> Iterator['Result[_ResultValueType]']:
        return self.children.__iter__()

    def with_rule_name(self, rule_name: str) -> 'Result[_ResultValueType]':
        return Result[_ResultValueType](value=self.value, children=self.children, rule_name=rule_name)

    def where(self, pred: Callable[['Result[_ResultValueType]'], bool]) -> 'Result[_ResultValueType]':
        if pred(self):
            return Result[_ResultValueType](children=[self])
        else:
            return self.where_children(pred)

    def where_children(self, pred: Callable[['Result[_ResultValueType]'], bool]) -> 'Result[_ResultValueType]':
        child_results: MutableSequence[Result[_ResultValueType]] = []
        for child in self.children:
            for child_result in child.where(pred).children:
                child_results.append(child_result)
        return Result[_ResultValueType](children=child_results)

    def skip(self) -> 'Result[_ResultValueType]':
        return Result[_ResultValueType](children=self.children)

    def where_n(self, n: int, pred: Callable[['Result[_ResultValueType]'], bool]) -> 'Result[_ResultValueType]':
        result: Result[_ResultValueType] = self.where(pred)
        if len(result.children) != n:
            raise Error(
                msg=f'result count mismatch expected {n} got {len(result.children)}')
        return result

    def where_one(self, pred: Callable[['Result[_ResultValueType]'], bool]) -> 'Result[_ResultValueType]':
        return self.where_n(1, pred).children[0]

    @staticmethod
    def rule_name_is(rule_name: str) -> Callable[['Result[_ResultValueType]'], bool]:
        return lambda result: result.rule_name == rule_name

    def has_value(self) -> bool:
        return self.value is not None

    def has_rule_name(self) -> bool:
        return self.rule_name is not None


class StateValue(ABC):
    @abstractproperty
    def empty(self) -> bool: ...


_StateValueType = TypeVar('_StateValueType', bound=StateValue)


@dataclass(frozen=True, repr=False)
class State(Generic[_ResultValueType, _StateValueType]):
    processor: 'Processor[_ResultValueType,_StateValueType]'
    value: _StateValueType

    def __repr__(self) -> str:
        return repr(self.value)

    def with_value(self, value: _StateValueType) -> 'State[_ResultValueType,_StateValueType]':
        return State[_ResultValueType, _StateValueType](self.processor, value)


@dataclass(frozen=True)
class ResultAndState(Generic[_ResultValueType, _StateValueType]):
    result: Result[_ResultValueType]
    state: State[_ResultValueType, _StateValueType]

    def with_rule_name(self, rule_name: str) -> 'ResultAndState[_ResultValueType,_StateValueType]':
        return ResultAndState[_ResultValueType, _StateValueType](self.result.with_rule_name(rule_name), self.state)


class Rule(ABC, Generic[_ResultValueType, _StateValueType]):
    @abstractmethod
    def apply(self, state: State[_ResultValueType, _StateValueType]) -> ResultAndState[_ResultValueType, _StateValueType]:
        ...


@dataclass(frozen=True)
class Processor(Generic[_ResultValueType, _StateValueType]):
    root_rule_name: str
    rules: Mapping[str, Rule[_ResultValueType, _StateValueType]]

    def apply_rule_to_state(
        self,
        rule_name: str,
        state: State[_ResultValueType, _StateValueType]
    ) -> ResultAndState[_ResultValueType, _StateValueType]:
        if rule_name not in self.rules:
            raise Error(msg=f'unknown rule {rule_name}')
        try:
            return self.rules[rule_name].apply(state).with_rule_name(rule_name)
        except Error as error:
            raise error.with_rule_name(rule_name)

    def apply_rule(self, rule_name: str, state_value: _StateValueType) -> ResultAndState[_ResultValueType, _StateValueType]:
        return self.apply_rule_to_state(rule_name, State[_ResultValueType, _StateValueType](self, state_value))

    def apply_root(self, state_value: _StateValueType) -> ResultAndState[_ResultValueType, _StateValueType]:
        return self.apply_rule(self.root_rule_name, state_value)


@dataclass(frozen=True)
class Error(Exception):
    rule_name: Optional[str] = field(default=None, kw_only=True)
    msg: Optional[str] = field(default=None, kw_only=True)
    children: Sequence['Error'] = field(default_factory=list, kw_only=True)

    def __str__(self) -> str: return repr(self)

    def with_rule_name(self, rule_name: str) -> 'Error':
        return Error(msg=self.msg, rule_name=rule_name, children=self.children)


@dataclass(frozen=True)
class Ref(Rule[_ResultValueType, _StateValueType]):
    rule_name: str

    def apply(self, state: State[_ResultValueType, _StateValueType]) -> ResultAndState[_ResultValueType, _StateValueType]:
        try:
            child_result: ResultAndState[_ResultValueType, _StateValueType] = state.processor.apply_rule_to_state(
                self.rule_name, state)
            return ResultAndState[_ResultValueType, _StateValueType](
                Result[_ResultValueType](
                    children=[child_result.result],
                ),
                child_result.state
            )
        except Error as error:
            raise Error(children=[error])


@dataclass(frozen=True)
class And(Rule[_ResultValueType, _StateValueType]):
    children: Sequence[Rule[_ResultValueType, _StateValueType]]

    def apply(self, state: State[_ResultValueType, _StateValueType]) -> ResultAndState[_ResultValueType, _StateValueType]:
        child_results: MutableSequence[Result[_ResultValueType]] = [
        ]
        child_state: State[_ResultValueType, _StateValueType] = state
        for child in self.children:
            child_result: ResultAndState[_ResultValueType,
                                         _StateValueType] = child.apply(child_state)
            child_results.append(child_result.result)
            child_state = child_result.state
        return ResultAndState[_ResultValueType, _StateValueType](Result[_ResultValueType](children=child_results), child_state)


@ dataclass(frozen=True, repr=False)
class Or(Rule[_ResultValueType, _StateValueType]):
    children: Sequence[Rule[_ResultValueType, _StateValueType]]

    def apply(self, state: State[_ResultValueType, _StateValueType]) -> ResultAndState[_ResultValueType, _StateValueType]:
        child_errors: MutableSequence[Error] = []
        child_results: MutableSequence[ResultAndState[_ResultValueType, _StateValueType]] = [
        ]
        for child in self.children:
            try:
                child_results.append(child.apply(state))
            except Error as error:
                child_errors.append(error)
        if len(child_results) > 1:
            raise Error(msg=f'ambiguous or result {child_results}')
        elif not child_results:
            raise Error(children=child_errors)
        else:
            child_result: ResultAndState[_ResultValueType,
                                         _StateValueType] = child_results[0]
            return ResultAndState[_ResultValueType, _StateValueType](
                Result[_ResultValueType](
                    children=[child_result.result]
                ),
                child_result.state
            )


@ dataclass(frozen=True)
class ZeroOrMore(Rule[_ResultValueType, _StateValueType]):
    child: Rule[_ResultValueType, _StateValueType]

    def apply(self, state: State[_ResultValueType, _StateValueType]) -> ResultAndState[_ResultValueType, _StateValueType]:
        child_results: MutableSequence[Result[_ResultValueType]] = [
        ]
        child_state: State[_ResultValueType, _StateValueType] = state
        while True:
            try:
                child_result: ResultAndState[_ResultValueType,
                                             _StateValueType] = self.child.apply(child_state)
                child_results.append(child_result.result)
                child_state = child_result.state
            except Error:
                break
        return ResultAndState[_ResultValueType, _StateValueType](Result[_ResultValueType](children=child_results), child_state)


@ dataclass(frozen=True)
class OneOrMore(Rule[_ResultValueType, _StateValueType]):
    child: Rule[_ResultValueType, _StateValueType]

    def apply(self, state: State[_ResultValueType, _StateValueType]) -> ResultAndState[_ResultValueType, _StateValueType]:
        child_result: ResultAndState[_ResultValueType,
                                     _StateValueType] = self.child.apply(state)
        child_results: MutableSequence[Result[_ResultValueType]] = [
            child_result.result]
        child_state: State[_ResultValueType,
                           _StateValueType] = child_result.state
        while True:
            try:
                child_result = self.child.apply(child_state)
                child_results.append(child_result.result)
                child_state = child_result.state
            except Error:
                break
        return ResultAndState[_ResultValueType, _StateValueType](Result[_ResultValueType](children=child_results), child_state)


@ dataclass(frozen=True)
class ZeroOrOne(Rule[_ResultValueType, _StateValueType]):
    child: Rule[_ResultValueType, _StateValueType]

    def apply(self, state: State[_ResultValueType, _StateValueType]) -> ResultAndState[_ResultValueType, _StateValueType]:
        try:
            child_result: ResultAndState[_ResultValueType,
                                         _StateValueType] = self.child.apply(state)
            return ResultAndState[_ResultValueType, _StateValueType](
                Result[_ResultValueType](
                    children=[child_result.result]
                ),
                child_result.state
            )
        except Error:
            return ResultAndState[_ResultValueType, _StateValueType](Result[_ResultValueType](), state)


@ dataclass(frozen=True)
class UntilEmpty(Rule[_ResultValueType, _StateValueType]):
    child: Rule[_ResultValueType, _StateValueType]

    def apply(self, state: State[_ResultValueType, _StateValueType]) -> ResultAndState[_ResultValueType, _StateValueType]:
        child_state: State[_ResultValueType, _StateValueType] = state
        child_results: MutableSequence[Result[_ResultValueType]] = [
        ]
        while not child_state.value.empty:
            child_result: ResultAndState[_ResultValueType, _StateValueType] = self.child.apply(
                child_state)
            child_state = child_result.state
            child_results.append(child_result.result)
        return ResultAndState[_ResultValueType, _StateValueType](Result[_ResultValueType](children=child_results), child_state)
