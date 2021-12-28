from core import lexer, parser
from typing import Callable, Mapping, MutableMapping, MutableSequence


def lexer_rule(input: str) -> lexer.Rule:
    operators = '()[]+?*-'
    operator_rules: Mapping[str, lexer.Rule] = {
        operator:
        lexer.Literal(operator) for operator in operators}
    lexer_rules: MutableMapping[str, lexer.Rule] = dict(operator_rules)
    lexer_rules['literal'] = lexer.Not(
        lexer.Or(list[lexer.Rule](operator_rules.values())))
    lexer_lexer = lexer.Lexer(lexer_rules)
    lexer_parser = parser.Parser(
        'root',
        {
            'root':   parser.UntilEmpty(parser.Ref('rule')),
            'rule': parser.Or([
                parser.Ref('zero_or_more'),
                parser.Ref('operand'),
            ]),
            'literal': parser.Literal('literal'),
            'paren_rule': parser.And([
                parser.Literal('('),
                parser.OneOrMore(parser.Ref('rule')),
                parser.Literal(')'),
            ]),
            'zero_or_more': parser.And([
                parser.Ref('operand'),
                parser.Literal('*'),
            ]),
            'operand': parser.Or([
                parser.Ref('literal'),
                parser.Ref('paren_rule'),
            ]),
        },
        lexer_lexer
    )
    try:
        result = lexer_parser.apply(input)
    except parser.Error as error:
        raise error

    def load_literal(result: parser.Result) -> lexer.Rule:
        assert result.rule_name == 'literal' and result.value is not None
        return lexer.Literal(result.value.value)

    def load_and(result: parser.Result) -> lexer.Rule:
        children: MutableSequence[lexer.Rule] = []
        for rule in result.where(parser.Result.rule_name_is('rule')):
            children.append(load_rule(rule))
        return lexer.And(children)

    def load_zero_or_more(result: parser.Result) -> lexer.Rule:
        return lexer.ZeroOrMore(load_rule(result.where_one(parser.Result.rule_name_is('operand'))))

    rule_funcs: Mapping[str, Callable[[parser.Result], lexer.Rule]] = {
        'literal': load_literal,
        'paren_rule': load_and,
        'zero_or_more': load_zero_or_more,
    }

    def load_rule(result: parser.Result) -> lexer.Rule:
        rule_result = result.where_one(
            lambda result: result.rule_name in rule_funcs.keys())
        assert rule_result.rule_name is not None
        return rule_funcs[rule_result.rule_name](rule_result)

    return load_and(result)
