from dataclasses import dataclass

from core import lexer, processor


ResultValue = lexer.Token

State = lexer.TokenStream

Result = processor.Result[ResultValue, State]

ResultAndState = processor.ResultAndState[ResultValue, State]

Error = processor.Error

RuleError = processor.RuleError[ResultValue, State]

NestedRuleError = processor.NestedRuleError[ResultValue, State]

Rule = processor.Rule[ResultValue, State]

And = processor.And[ResultValue, State]

Or = processor.Or[ResultValue, State]

ZeroOrMore = processor.ZeroOrMore[ResultValue, State]

OneOrMore = processor.OneOrMore[ResultValue, State]

ZeroOrOne = processor.ZeroOrOne[ResultValue, State]

UntilEmpty = processor.UntilEmpty[ResultValue, State]


@dataclass(frozen=True)
class Literal(Rule):
    value: str

    def apply(self, state: State) -> ResultAndState:
        if not state.empty and state.head.type == self.value:
            return ResultAndState(Result(self, state.head, []), state.tail)
        raise RuleError(self, state)


@dataclass(frozen=True)
class Parser(processor.Processor[ResultValue, State]):
    lexer: lexer.Lexer

    def apply(self, input: str) -> Result:
        return self.apply_root(self.lexer.apply(input)).result
