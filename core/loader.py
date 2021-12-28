from core import lexer, parser
from typing import MutableSequence, Sequence


def lexer_rule(input: str) -> lexer.Rule:
    operators = '()[]+?*-'
    operator_rules: Sequence[lexer.Rule] = [
        lexer.StartsWith(operator, operator) for operator in operators]
    operator_rule: lexer.Rule = lexer.Or('operator', operator_rules)
    not_operator_rule: lexer.Rule = lexer.Not('not_operator', operator_rule)
    lexer_rules: MutableSequence[lexer.Rule] = []
    lexer_rules.extend(operator_rules)
    lexer_rules.append(not_operator_rule)
    lexer_lexer = lexer.Lexer(lexer_rules)
    lexer_parser = parser.Parser(
        'root',
        [
            parser.UntilEmpty(
                None,
                parser.Or(
                    None,
                    parser.Literal('not_operator', 'not_operator')
                )
            )
        ],
        lexer_lexer
    )
