from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from typing import MutableSequence, Optional, Sequence


@dataclass(frozen=True)
class Lexer:
    rules: Sequence['Lexer.Rule']

    @dataclass(frozen=True)
    class Error(Exception):
        state: 'Lexer.State'

    @dataclass(frozen=True)
    class AmbiguityError(Error):
        results: Sequence['Lexer.Rule.Result']

    @dataclass(frozen=True)
    class State:
        input: str
        pos: int = 0

        @cached_property
        def empty(self) -> bool:
            return self.pos > len(self.input)

        @cached_property
        def value(self) -> str:
            if self.empty:
                raise Lexer.Error(self)
            return self.input[self.pos:]

    @dataclass(frozen=True)
    class Rule(ABC):
        name: str

        @dataclass(frozen=True)
        class Result:
            token: Optional['Lexer.Token']
            state: 'Lexer.State'

        @abstractmethod
        def apply(self, state: 'Lexer.State') -> 'Lexer.Rule.Result': ...

    @dataclass(frozen=True)
    class Position:
        index: int

    @dataclass(frozen=True)
    class Token:
        rule_name: str
        value: str
        position: 'Lexer.Position'

        def __repr__(self) -> str:
            return f'Token({self.rule_name},{self.value})'

    @dataclass(frozen=True)
    class Result:
        tokens: Sequence['Lexer.Token']

    def apply(self, input: str) -> 'Lexer.Result':
        toks: MutableSequence[Lexer.Token] = []
        state: Lexer.State = Lexer.State(input)
        while not state.empty:
            rule_results: Sequence['Lexer.Rule.Result'] = [result for result in [
                rule.apply(state) for rule in self.rules] if result is not None]
            if len(rule_results) > 1:
                raise Lexer.AmbiguityError(state, rule_results)
            elif not rule_results:
                raise Lexer.Error(state)
            rule_result = rule_results[0]
            if rule_result.token is not None:
                toks.append(rule_result.token)
            state = rule_result.state
        return Lexer.Result(toks)
