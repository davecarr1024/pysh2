from dataclasses import dataclass
from functools import cached_property
from typing import Callable, MutableSequence, Optional, Sequence, TypeVar
from core import parser, processor


_ResultValueType = TypeVar(
    '_ResultValueType', bound=processor.ResultValue)


@dataclass(frozen=True)
class State(processor.StateValue):
    result: parser.Result

    @cached_property
    def children(self) -> Sequence['State']:
        return [State(child) for child in self.result.children]

    def search(self, cond: Callable[[parser.Result], bool]) -> Sequence['State']:
        if cond(self.result):
            return [self]
        return sum([child.search(cond) for child in self.children], list[State]())


Rule = processor.Rule[_ResultValueType, State]

@dataclass(frozen=True)
class Where(Rule[_ResultValueType]):
    cond: Callable[[parser.Result], bool]
    child: Rule[_ResultValueType]
    num_states: Optional[int] = None

    def apply(self, state: State) -> processor.ResultAndState[_ResultValueType, State]:
        child_results: MutableSequence[processor.Result[_ResultValueType, State]] = [
        ]
        search_states: Sequence[State] = state.search(self.cond)
        if self.num_states is not None and len(search_states) != self.num_states:
            raise processor.RuleError[_ResultValueType, State](
                self, state, msg=f'num_states mismatch {len(search_states)} != {self.num_states}')
        for search_state in search_states:
            try:
                child_result: processor.ResultAndState[_ResultValueType, State] = self.child.apply(
                    search_state)
                child_results.append(child_result.result)
            except processor.Error as error:
                raise processor.NestedRuleError[_ResultValueType, State](self, state, [
                                                                         error])
        return processor.ResultAndState[_ResultValueType, State](
            processor.Result[_ResultValueType, State](
                self,
                None,
                child_results
            ),
            state
        )


@dataclass(frozen=True)
class Expr(Rule[_ResultValueType]):
    factory: Callable[[parser.Result], _ResultValueType]

    def apply(self, state: State) -> processor.ResultAndState[_ResultValueType, State]:
        return processor.ResultAndState[_ResultValueType, State](
            processor.Result[_ResultValueType, State](
                self,
                self.factory(state.result),
                []
            ),
            state
        )


class Syntax(processor.Processor[_ResultValueType, State]):
    ...
