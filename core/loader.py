from core import lexer, parser
from typing import Callable, Mapping, MutableMapping, MutableSequence, Optional


def load_lexer_rule(input: str) -> lexer.Rule:
    operators = '()[-]+?*!^|\\'
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
                parser.Ref('not'),
            ]),
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
                parser.Literal('literal'),
                parser.Ref('class'),
                parser.Ref('special'),
            ]),
            'class': parser.And([
                parser.Literal('['),
                parser.Literal('literal'),
                parser.Literal('-'),
                parser.Literal('literal'),
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
            'special': parser.And([
                parser.Literal('\\'),
                parser.Ref('special_value'),
            ]),
            'special_value': parser.Any(),
        },
        lexer_lexer
    )

    def load_literal(result: parser.Result) -> lexer.Rule:
        assert result.rule_name == 'literal' and result.value is not None, result
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

    def load_special(result: parser.Result) -> lexer.Rule:
        value_result = result.where_one(
            parser.Result.rule_name_is('special_value'))
        assert value_result.value is not None
        value = value_result.value.value
        values: Mapping[str, lexer.Rule] = {
            'n': lexer.Literal('\n'),
            'w': lexer.Or([lexer.Literal(c) for c in ' \n\t']),
        }
        if value in values:
            return values[value]
        return lexer.Literal(value)

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
        'special': load_special,
    }

    def load_rule(result: parser.Result) -> lexer.Rule:
        rule_result = result.where_one(
            parser.Result.rule_name_in(list(rule_funcs.keys())))
        assert rule_result.rule_name is not None
        return rule_funcs[rule_result.rule_name](rule_result)

    return load_and(lexer_parser.apply(input))


def load_lexer(rules: Mapping[str, str]) -> lexer.Lexer:
    return lexer.Lexer({name: load_lexer_rule(value) for name, value in rules.items()})


def load_parser(input: str) -> parser.Parser:
    result = parser.Parser(
        'root',
        {
            'root': parser.UntilEmpty(parser.Ref('line')),
            'line': parser.And([parser.Ref('rule_decl'), parser.Literal(';')]),
            'rule_decl': parser.Or([
                parser.Ref('lexer_rule_decl'),
                parser.Ref('parser_rule_decl'),
            ]),
            'lexer_rule_decl': parser.And([
                parser.Literal('id'),
                parser.Literal('='),
                parser.Literal('str'),
            ]),
            'parser_rule_decl': parser.And([
                parser.Ref('parser_rule_decl_name'),
                parser.Literal('->'),
                parser.Ref('rule'),
            ]),
            'parser_rule_decl_name': parser.Literal('id'),
            'rule': parser.Or([
                parser.Ref('ref'),
            ]),
            'ref': parser.Literal('id'),
        },
        load_lexer({
            '_ws': r'\w+',
            '=': '=',
            ';': ';',
            '->': r'\->',
            'id': '(_|[a-z]|[A-Z]|[0-9])+',
            'str': '"(^")+"',
        })
    ).apply(input)

    lexer_rules: MutableMapping[str, lexer.Rule] = {}
    parser_rules: MutableMapping[str, parser.Rule] = {}
    root_rule_name: Optional[str] = None

    def load_ref(result: parser.Result) -> parser.Rule:
        rule_name: str = result.where_one(
            parser.Result.rule_name_is('id')).get_value().value
        if rule_name in lexer_rules:
            return parser.Literal(rule_name)
        else:
            return parser.Ref(rule_name)

    def load_rule(result: parser.Result) -> parser.Rule:
        rule_loaders: Mapping[str, Callable[[parser.Result], parser.Rule]] = {
            'ref': load_ref,
        }
        rule_result = result.where_one(
            parser.Result.rule_name_in(list(rule_loaders.keys())))
        assert rule_result.rule_name is not None
        return rule_loaders[rule_result.rule_name](rule_result)

    def load_parser_rule_decl(result: parser.Result) -> None:
        rule_name: str = (
            result
            .where_one(parser.Result.rule_name_is('parser_rule_decl_name'))
            .where_one(parser.Result.rule_name_is('id'))
            .get_value().value)
        assert rule_name not in lexer_rules and rule_name not in parser_rules, rule_name
        rule: parser.Rule = load_rule(
            result.where_one(parser.Result.rule_name_is('rule')))
        parser_rules[rule_name] = rule
        nonlocal root_rule_name
        if root_rule_name is None:
            root_rule_name = rule_name

    def load_lexer_rule_decl(result: parser.Result) -> None:
        rule_name: str = result.where_one(
            parser.Result.rule_name_is('id')).get_value().value
        assert rule_name not in lexer_rules and rule_name not in parser_rules, rule_name
        rule_def: str = result.where_one(
            parser.Result.rule_name_is('str')).get_value().value.strip('"')
        lexer_rules[rule_name] = load_lexer_rule(rule_def)

    def load_rule_decl(result: parser.Result) -> None:
        rule_loaders: Mapping[str, Callable[[parser.Result], None]] = {
            'lexer_rule_decl': load_lexer_rule_decl,
            'parser_rule_decl': load_parser_rule_decl,
        }
        rule_result = result.where_one(
            parser.Result.rule_name_in(list(rule_loaders.keys())))
        assert rule_result.rule_name is not None
        rule_loaders[rule_result.rule_name](rule_result)

    for rule_result in result.where(parser.Result.rule_name_is('rule_decl')):
        load_rule_decl(rule_result)

    assert root_rule_name is not None, (lexer_rules, parser_rules)

    return parser.Parser(root_rule_name, parser_rules, lexer.Lexer(lexer_rules))
