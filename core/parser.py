from dataclasses import dataclass

from core import lexer, stream_processor


ResultValue = _Item = lexer.Token


StateValue = lexer.TokenStream

Result = stream_processor.Result[ResultValue]

State = stream_processor.State[ResultValue, _Item]

ResultAndState = stream_processor.ResultAndState[ResultValue, _Item]

Error = stream_processor.Error

Rule = stream_processor.Rule[ResultValue, _Item]

Ref = stream_processor.Ref[ResultValue, _Item]

And = stream_processor.And[ResultValue, _Item]

Or = stream_processor.Or[ResultValue, _Item]

ZeroOrMore = stream_processor.ZeroOrMore[ResultValue, _Item]

OneOrMore = stream_processor.OneOrMore[ResultValue, _Item]

ZeroOrOne = stream_processor.ZeroOrOne[ResultValue, _Item]

UntilEmpty = stream_processor.UntilEmpty[ResultValue, _Item]


class HeadRule(stream_processor.HeadRule[ResultValue, _Item]):
    def result(self, head: _Item) -> Result:
        return Result(value=head)


@dataclass(frozen=True)
class Literal(HeadRule):
    token_type: str

    def pred(self, head: _Item) -> bool:
        return head.type == self.token_type


class Any(HeadRule):
    def pred(self, head: _Item) -> bool:
        return True


@dataclass(frozen=True)
class Parser(stream_processor.Processor[ResultValue, _Item]):
    lexer: lexer.Lexer

    def apply(self, input: str) -> Result:
        return self.apply_root(self.lexer.apply(input)).result
