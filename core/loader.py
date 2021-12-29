from core import lexer, parser, processor
from typing import Callable, Mapping, MutableMapping, MutableSequence, Optional, OrderedDict, Sequence


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
        value = result.where_one(
            parser.Result.rule_name_is('special_value')).get_value().value
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
    try:
        parser_lexer: lexer.Lexer = load_lexer({
            '_ws': r'\w+',
            '=': '=',
            ';': ';',
            '->': r'\->',
            '|': r'\|',
            '(': r'\(',
            ')': r'\)',
            '*': r'\*',
            '+': r'\+',
            '?': r'\?',
            '!': r'\!',
            'id': '(_|[a-z]|[A-Z]|[0-9])+',
            'str': '"(^")+"',
        })
    except processor.Error as error:
        raise processor.Error(
            msg='failed to load parser lexer', children=[error])

    parser_parser: parser.Parser = parser.Parser(
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
                parser.Ref('or'),
                parser.Ref('and'),
                parser.Ref('operand'),
            ]),
            'ref': parser.Literal('id'),
            'and': parser.And([
                parser.Ref('operand'),
                parser.OneOrMore(parser.Ref('operand')),
            ]),
            'operand': parser.Or([
                parser.Ref('unary_operation'),
                parser.Ref('unary_operand'),
            ]),
            'unary_operand': parser.Or([
                parser.Ref('ref'),
                parser.Ref('paren_rule'),
                parser.Ref('lexer_literal'),
            ]),
            'or': parser.And([
                parser.Ref('operand'),
                parser.OneOrMore(
                    parser.And([
                        parser.Literal('|'),
                        parser.Ref('operand'),
                    ])
                ),
            ]),
            'paren_rule': parser.And([
                parser.Literal('('),
                parser.Ref('rule'),
                parser.Literal(')'),
            ]),
            'unary_operation': parser.Or([
                parser.Ref('zero_or_more'),
                parser.Ref('one_or_more'),
                parser.Ref('zero_or_one'),
                parser.Ref('until_empty'),
            ]),
            'zero_or_more': parser.And([
                parser.Ref('unary_operand'),
                parser.Literal('*'),
            ]),
            'one_or_more': parser.And([
                parser.Ref('unary_operand'),
                parser.Literal('+'),
            ]),
            'zero_or_one': parser.And([
                parser.Ref('unary_operand'),
                parser.Literal('?'),
            ]),
            'until_empty': parser.And([
                parser.Ref('unary_operand'),
                parser.Literal('!'),
            ]),
            'lexer_literal': parser.Literal('str'),
        },
        parser_lexer
    )

    try:
        result: parser.Result = parser_parser.apply(input)
    except processor.Error as error:
        raise processor.Error(msg='failed to load parser', children=[error])

    lexer_rules: OrderedDict[str, lexer.Rule] = OrderedDict()
    parser_rules: MutableMapping[str, parser.Rule] = {}
    root_rule_name: Optional[str] = None

    def load_lexer_literal(result: parser.Result) -> parser.Rule:
        value: str = result.where_one(
            parser.Result.rule_name_is('str')).get_value().value.strip('"')
        if value in lexer_rules:
            assert lexer_rules[value] == load_lexer_rule(
                value), (value, lexer_rules[value])
        else:
            lexer_rules[value] = load_lexer_rule(value)
            lexer_rules.move_to_end(value, False)
        return parser.Literal(value)

    def load_unary_operation(factory: Callable[[parser.Rule], parser.Rule]) -> Callable[[parser.Result], parser.Rule]:
        return lambda result: factory(load_rule(result.where_one(parser.Result.rule_name_is('unary_operand'))))

    load_zero_or_more = load_unary_operation(parser.ZeroOrMore)
    load_one_or_more = load_unary_operation(parser.OneOrMore)
    load_zero_or_one = load_unary_operation(parser.ZeroOrOne)
    load_until_empty = load_unary_operation(parser.UntilEmpty)

    def load_operation(factory: Callable[[Sequence[parser.Rule]], parser.Rule]) -> Callable[[parser.Result], parser.Rule]:
        def closure(result: parser.Result) -> parser.Rule:
            return factory([load_rule(rule) for rule in result.where(parser.Result.rule_name_is('operand'))])
        return closure

    load_or = load_operation(parser.Or)
    load_and = load_operation(parser.And)

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
            'and': load_and,
            'or': load_or,
            'zero_or_more': load_zero_or_more,
            'one_or_more': load_one_or_more,
            'zero_or_one': load_zero_or_one,
            'until_empty': load_until_empty,
            'lexer_literal': load_lexer_literal,
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
        lexer_rules.move_to_end(rule_name)

    def load_rule_decl(result: parser.Result) -> None:
        rule_loaders: Mapping[str, Callable[[parser.Result], None]] = {
            'lexer_rule_decl': load_lexer_rule_decl,
            'parser_rule_decl': load_parser_rule_decl,
        }
        rule_result = result.where_one(
            parser.Result.rule_name_in(list(rule_loaders.keys())))
        assert rule_result.rule_name is not None
        rule_loaders[rule_result.rule_name](rule_result)

    for rule_decl in result.where(parser.Result.rule_name_is('rule_decl')):
        try:
            load_rule_decl(rule_decl)
        except processor.Error as error:
            raise processor.Error(
                msg=f'failed to {rule_decl}', children=[error])

    assert root_rule_name is not None, 'no root rule name'

    return parser.Parser(root_rule_name, parser_rules, lexer.Lexer(lexer_rules))
