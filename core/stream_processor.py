from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar

from core import processor


_ItemType = TypeVar('_ItemType')
_ResultValueType = TypeVar('_ResultValueType', bound=processor.ResultValue)
Error = processor.Error


@dataclass(frozen=True)
class Stream(processor.StateValue, Generic[_ItemType]):
    values: Sequence[_ItemType]

    @property
    def empty(self) -> bool:
        return len(self.values) == 0

    @property
    def head(self) -> _ItemType:
        if self.empty:
            raise Error(msg='stream empty')
        else:
            return self.values[0]

    @property
    def tail(self) -> 'Stream[_ItemType]':
        if self.empty:
            raise Error(msg='stream empty')
        else:
            return self.__class__(self.values[1:])


@dataclass(frozen=True)
class Processor(processor.Processor[_ResultValueType, Stream[_ItemType]]):
    pass


Rule = processor.Rule[_ResultValueType, Stream[_ItemType]]
Result = processor.Result[_ResultValueType]
State = processor.State[_ResultValueType, Stream[_ItemType]]
ResultAndState = processor.ResultAndState[_ResultValueType,
                                          Stream[_ItemType]]
Ref = processor.Ref[_ResultValueType, Stream[_ItemType]]
And = processor.And[_ResultValueType, Stream[_ItemType]]
Or = processor.Or[_ResultValueType, Stream[_ItemType]]
ZeroOrMore = processor.ZeroOrMore[_ResultValueType, Stream[_ItemType]]
OneOrMore = processor.OneOrMore[_ResultValueType, Stream[_ItemType]]
ZeroOrOne = processor.ZeroOrOne[_ResultValueType, Stream[_ItemType]]
UntilEmpty = processor.UntilEmpty[_ResultValueType, Stream[_ItemType]]


class HeadRule(Rule[_ResultValueType, _ItemType], ABC):
    @abstractmethod
    def pred(self, head: _ItemType) -> bool: ...

    @abstractmethod
    def result(self, head: _ItemType) -> Result[_ResultValueType]: ...

    def apply(self, state: State[_ResultValueType, _ItemType]) -> ResultAndState[_ResultValueType, _ItemType]:
        if self.pred(state.value.head):
            return ResultAndState[_ResultValueType, _ItemType](
                self.result(state.value.head),
                state.with_value(state.value.tail)
            )
        else:
            raise Error(msg=f'{self} failed to match head {state.value.head}')


@dataclass(frozen=True)
class Literal(HeadRule[_ResultValueType, _ItemType]):
    value: _ItemType

    def pred(self, head: _ItemType) -> bool:
        return self.value == head
