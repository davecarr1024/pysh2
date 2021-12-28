from core import lexer, parser
from typing import Callable, Mapping, MutableMapping, MutableSequence


def lexer_rule(input: str) -> lexer.Rule:
    operators = '()[-]+?*!^|'
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
                parser.Ref('operation'),
                parser.Ref('operand'),
            ]),
            'operation': parser.Or([
                parser.Ref('zero_or_more'),
                parser.Ref('one_or_more'),
                parser.Ref('zero_or_one'),
                parser.Ref('until_empty'),
                parser.Ref('unary_operation'),
            ]),
            'unary_operation': parser.Or([
                parser.Ref('not'),
            ]),
            'literal': parser.Literal('literal'),
            'and': parser.And([
                parser.Literal('('),
                parser.OneOrMore(parser.Ref('rule')),
                parser.Literal(')'),
            ]),
            'zero_or_more': parser.And([
                parser.Ref('operand'),
                parser.Literal('*'),
            ]),
            'one_or_more': parser.And([
                parser.Ref('operand'),
                parser.Literal('+'),
            ]),
            'zero_or_one': parser.And([
                parser.Ref('operand'),
                parser.Literal('?'),
            ]),
            'until_empty': parser.And([
                parser.Ref('operand'),
                parser.Literal('!'),
            ]),
            'not': parser.And([
                parser.Literal('^'),
                parser.Ref('unary_operand'),
            ]),
            'operand': parser.Or([
                parser.Ref('and'),
                parser.Ref('or'),
                parser.Ref('unary_operand'),
            ]),
            'unary_operand': parser.Or([
                parser.Ref('literal'),
                parser.Ref('class'),
            ]),
            'class': parser.And([
                parser.Literal('['),
                parser.Ref('literal'),
                parser.Literal('-'),
                parser.Ref('literal'),
                parser.Literal(']'),
            ]),
            'or': parser.And([
                parser.Literal('('),
                parser.Ref('rule'),
                parser.OneOrMore(
                    parser.And([
                        parser.Literal('|'),
                        parser.Ref('rule'),
                    ])
                ),
                parser.Literal(')'),
            ]),
        },
        lexer_lexer
    )

    def load_literal(result: parser.Result) -> lexer.Rule:
        assert result.rule_name == 'literal' and result.value is not None
        return lexer.Literal(result.value.value)

    def load_and(result: parser.Result) -> lexer.Rule:
        children: MutableSequence[lexer.Rule] = []
        for rule in result.where(parser.Result.rule_name_is('rule')):
            children.append(load_rule(rule))
        return lexer.And(children)

    def load_or(result: parser.Result) -> lexer.Rule:
        return lexer.Or([load_rule(rule) for rule in result.where(parser.Result.rule_name_is('rule'))])

    def load_operation(factory: Callable[[lexer.Rule], lexer.Rule]) -> Callable[[parser.Result], lexer.Rule]:
        return lambda result: factory(load_rule(result.where_one(parser.Result.rule_name_in(('operand', 'unary_operand')))))

    def load_class(result: parser.Result) -> lexer.Rule:
        min, max = result.where(parser.Result.rule_name_is('literal'))
        assert min.value is not None and max.value is not None
        return lexer.Class(min.value.value, max.value.value)

    rule_funcs: Mapping[str, Callable[[parser.Result], lexer.Rule]] = {
        'literal': load_literal,
        'and': load_and,
        'or': load_or,
        'zero_or_more': load_operation(lexer.ZeroOrMore),
        'one_or_more': load_operation(lexer.OneOrMore),
        'zero_or_one': load_operation(lexer.ZeroOrOne),
        'until_empty': load_operation(lexer.UntilEmpty),
        'not': load_operation(lexer.Not),
        'class': load_class,
    }

    def load_rule(result: parser.Result) -> lexer.Rule:
        rule_result = result.where_one(
            parser.Result.rule_name_in(list(rule_funcs.keys())))
        assert rule_result.rule_name is not None
        return rule_funcs[rule_result.rule_name](rule_result)

    return load_and(lexer_parser.apply(input))
