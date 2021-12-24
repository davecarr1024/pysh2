from .lexer import Lexer

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property, total_ordering
from typing import Mapping, MutableSequence, Optional, Sequence


@dataclass(frozen=True)
class Parser:
    rules: Sequence['Parser.Rule']
    root_rule_name: str = 'root'

    @dataclass(frozen=True)
    class Error(Exception):
        rule: 'Parser.Rule'
        state: 'Parser.State'
        children: Sequence['Parser.Error'] = field(
            default_factory=list)
        msg: Optional[str] = None

        @cached_property
        def max_descendent(self) -> 'Parser.Error':
            return max([child.max_descendent for child in self.children] + [self],
                       key=lambda error: error.state)

    @dataclass(frozen=True)
    class AmbiguityError(Exception):
        results: Sequence['Parser.Result']

    @dataclass(frozen=True)
    class IncompleteError(Exception):
        results: Sequence['Parser.Result']

    @dataclass(frozen=True)
    @total_ordering
    class State:
        lexer_result: 'Lexer.Result'
        pos: int = 0

        def __repr__(self) -> str:
            return f'State({self.pos})'

        def __gt__(self, rhs: 'Parser.State') -> bool:
            return self.pos > rhs.pos

        @cached_property
        def empty(self) -> bool:
            return self.pos >= len(self.lexer_result.tokens)

        @cached_property
        def head(self) -> Lexer.Token:
            if self.empty:
                raise ValueError(self.pos)
            return self.lexer_result.tokens[self.pos]

        def at_pos(self, pos: int) -> 'Parser.State':
            return Parser.State(self.lexer_result, pos)

        @cached_property
        def tail(self) -> 'Parser.State':
            return self.at_pos(self.pos+1)

    @dataclass(frozen=True)
    class Result:
        rule_name: Optional[str]
        token: Optional[Lexer.Token] = None
        children: Sequence['Parser.Result'] = field(default_factory=list)

        def __repr__(self) -> str:
            return self._repr(0)

        def _repr(self, indent: int) -> str:
            return '\n' + f'{"  "*indent}{self.rule_name}({self.token})' + ''.join([child._repr(indent+1) for child in self.children])

    @dataclass(frozen=True)
    class Rule(ABC):
        @dataclass(frozen=True)
        class Result:
            result: 'Parser.Result'
            state: 'Parser.State'

        name: Optional[str]

        @abstractmethod
        def apply(self, state: 'Parser.State') -> 'Parser.Rule.Result':
            ...

    @dataclass(frozen=True)
    class And(Rule):
        children: Sequence['Parser.Rule']

        def apply(self, state: 'Parser.State') -> 'Parser.Rule.Result':
            child_results: MutableSequence[Parser.Result] = []
            child_state: Parser.State = state
            for child in self.children:
                try:
                    child_result: Parser.Rule.Result = child.apply(
                        child_state)
                except Parser.Error as error:
                    raise Parser.Error(self, state, [error])
                child_results.append(child_result.result)
                child_state = child_result.state
            return Parser.Rule.Result(Parser.Result(self.name, children=child_results), child_state)

    @dataclass(frozen=True)
    class Or(Rule):
        children: Sequence['Parser.Rule']

        def apply(self, state: 'Parser.State') -> 'Parser.Rule.Result':
            child_errors: MutableSequence['Parser.Error'] = []
            for child in self.children:
                try:
                    child_result: Parser.Rule.Result = child.apply(state)
                    return Parser.Rule.Result(Parser.Result(self.name, children=[child_result.result]), child_result.state)
                except Parser.Error as error:
                    child_errors.append(error)
            raise Parser.Error(self, state, child_errors)

    @dataclass(frozen=True)
    class ZeroOrMore(Rule):
        child: 'Parser.Rule'

        def apply(self, state: 'Parser.State') -> 'Parser.Rule.Result':
            child_results: MutableSequence[Parser.Result] = []
            child_state: Parser.State = state
            while True:
                try:
                    child_result = self.child.apply(child_state)
                    child_results.append(child_result.result)
                    child_state = child_result.state
                except Parser.Error:
                    break
            return Parser.Rule.Result(Parser.Result(self.name, children=child_results), child_state)

    @dataclass(frozen=True)
    class OneOrMore(Rule):
        child: 'Parser.Rule'

        def apply(self, state: 'Parser.State') -> 'Parser.Rule.Result':
            try:
                child_result: Parser.Rule.Result = self.child.apply(state)
            except Parser.Error as error:
                raise Parser.Error(self, state, [error])
            child_results: MutableSequence[Parser.Result] = [
                child_result.result]
            child_state: Parser.State = child_result.state
            while True:
                try:
                    child_result = self.child.apply(child_state)
                    child_results.append(child_result.result)
                    child_state = child_result.state
                except Parser.Error:
                    break
            return Parser.Rule.Result(Parser.Result(self.name, children=child_results), child_state)

    @dataclass(frozen=True)
    class UntilEnd(Rule):
        child: 'Parser.Rule'

        def apply(self, state: 'Parser.State') -> 'Parser.Rule.Result':
            child_results: MutableSequence[Parser.Result] = []
            child_state: Parser.State = state
            while not child_state.empty:
                try:
                    child_result = self.child.apply(child_state)
                    child_results.append(child_result.result)
                    child_state = child_result.state
                except Parser.Error as error:
                    raise Parser.Error(self, state, [error])
            return Parser.Rule.Result(Parser.Result(self.name, children=child_results), child_state)

    @dataclass(frozen=True)
    class ZeroOrOne(Rule):
        child: 'Parser.Rule'

        def apply(self, state: 'Parser.State') -> 'Parser.Rule.Result':
            try:
                child_result: Parser.Rule.Result = self.child.apply(state)
                return Parser.Rule.Result(Parser.Result(self.name, children=[child_result.result]), child_result.state)
            except Parser.Error:
                return Parser.Rule.Result(Parser.Result(self.name), state)

    @dataclass(frozen=True)
    class Literal(Rule):
        def __post_init__(self):
            if self.name is None:
                raise ValueError(self.name)

        def apply(self, state: 'Parser.State') -> 'Parser.Rule.Result':
            if not state.empty and self.name == state.head.rule_name:
                return Parser.Rule.Result(Parser.Result(self.name, token=state.head), state.tail)
            else:
                raise Parser.Error(self, state)

    @cached_property
    def rules_by_name(self) -> Mapping[str, 'Parser.Rule']:
        return {rule.name: rule for rule in self.rules if rule.name is not None}

    @cached_property
    def root_rule(self) -> 'Parser.Rule':
        return self.rules_by_name[self.root_rule_name]

    def apply(self, lexer_result: Lexer.Result) -> 'Parser.Result':
        return self.root_rule.apply(Parser.State(lexer_result)).result
