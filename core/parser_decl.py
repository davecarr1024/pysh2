from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from typing import Mapping, MutableMapping, Optional, Sequence

from core.parser import Parser


@dataclass(frozen=True)
class ParserDecl:
    root_rule_name: str
    rules: Sequence['ParserDecl.Rule']

    @dataclass
    class State:
        parser_decl: 'ParserDecl'
        rule_cache: MutableMapping[str, Parser.Rule]

    @dataclass(frozen=True)
    class Rule(ABC):
        name: Optional[str]

        def bind(self, state: 'ParserDecl.State') -> 'Parser.Rule':
            if self.name and self.name in state.rule_cache:
                return state.rule_cache[self.name]
            rule = self._bind(state)
            if rule.name is None:
                return rule
            if rule.name in state.rule_cache:
                raise ValueError(f'duplicate rule {rule.name}')
            state.rule_cache[rule.name] = rule
            return rule

        @abstractmethod
        def _bind(self, state: 'ParserDecl.State') -> 'Parser.Rule':
            ...

    @dataclass(frozen=True)
    class Ref(Rule):
        value: str

        def _bind(self, state: 'ParserDecl.State') -> 'Parser.Rule':
            return state.parser_decl.rules_by_name[self.value].bind(state)

    @dataclass(frozen=True)
    class And(Rule):
        children: Sequence['ParserDecl.Rule']

        def _bind(self, state: 'ParserDecl.State') -> 'Parser.Rule':
            return Parser.And(self.name, [child.bind(state) for child in self.children])

    @dataclass(frozen=True)
    class Or(Rule):
        children: Sequence['ParserDecl.Rule']

        def _bind(self, state: 'ParserDecl.State') -> 'Parser.Rule':
            return Parser.Or(self.name, [child.bind(state) for child in self.children])

    @dataclass(frozen=True)
    class ZeroOrMore(Rule):
        child: 'ParserDecl.Rule'

        def _bind(self, state: 'ParserDecl.State') -> 'Parser.Rule':
            return Parser.ZeroOrMore(self.name, self.child.bind(state))

    @dataclass(frozen=True)
    class OneOrMore(Rule):
        child: 'ParserDecl.Rule'

        def _bind(self, state: 'ParserDecl.State') -> 'Parser.Rule':
            return Parser.ZeroOrMore(self.name, self.child.bind(state))

    @dataclass(frozen=True)
    class ZeroOrOne(Rule):
        child: 'ParserDecl.Rule'

        def _bind(self, state: 'ParserDecl.State') -> 'Parser.Rule':
            return Parser.ZeroOrOne(self.name, self.child.bind(state))

    @dataclass(frozen=True)
    class UntilEnd(Rule):
        child: 'ParserDecl.Rule'

        def _bind(self, state: 'ParserDecl.State') -> 'Parser.Rule':
            return Parser.UntilEnd(self.name, self.child.bind(state))

    @dataclass(frozen=True)
    class Literal(Rule):
        value: str

        def _bind(self, state: 'ParserDecl.State') -> 'Parser.Rule':
            return Parser.Literal(self.name, self.value)

    def bind(self) -> Parser:
        state: ParserDecl.State = ParserDecl.State(self, {})
        return Parser(self.root_rule_name, [rule.bind(state) for rule in self.rules])

    @cached_property
    def rules_by_name(self) -> Mapping[str, 'ParserDecl.Rule']:
        return {rule.name: rule for rule in self.rules if rule.name is not None}
