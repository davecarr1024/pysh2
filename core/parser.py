from dataclasses import dataclass

from core import lexer, processor


ResultValue = lexer.Token

StateValue = lexer.TokenStream

Result = processor.Result[ResultValue]

State = processor.State[ResultValue, StateValue]

ResultAndState = processor.ResultAndState[ResultValue, StateValue]

Error = processor.Error

Rule = processor.Rule[ResultValue, StateValue]

Ref = processor.Ref[ResultValue, StateValue]

And = processor.And[ResultValue, StateValue]

Or = processor.Or[ResultValue, StateValue]

ZeroOrMore = processor.ZeroOrMore[ResultValue, StateValue]

OneOrMore = processor.OneOrMore[ResultValue, StateValue]

ZeroOrOne = processor.ZeroOrOne[ResultValue, StateValue]

UntilEmpty = processor.UntilEmpty[ResultValue, StateValue]


@dataclass(frozen=True)
class Literal(Rule):
    value: str

    def apply(self, state: State) -> ResultAndState:
        if state.value.empty:
            raise Error(msg='state empty')
        elif state.value.head.type == self.value:
            return ResultAndState(Result(value=state.value.head), state.with_value(state.value.tail))
        else:
            raise Error(
                msg=f'literal mismatch expected {self.value} got {state.value.head.type}')


@dataclass(frozen=True)
class Parser(processor.Processor[ResultValue, StateValue]):
    lexer: lexer.Lexer

    def apply(self, input: str) -> Result:
        return self.apply_root(self.lexer.apply(input)).result
