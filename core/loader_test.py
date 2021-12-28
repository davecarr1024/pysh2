import unittest

from core import lexer, loader, parser

if 'unittest.util' in __import__('sys').modules:
    # Show full diff in self.assertEqual.
    __import__('sys').modules['unittest.util']._MAX_LENGTH = 999999999


class LoaderTest(unittest.TestCase):
    def test_load_lexer_rule(self):
        input: str
        rule: lexer.Rule
        for input, rule in [
            (
                'a',
                lexer.And([
                    lexer.Literal('a'),
                ])
            ),
            (
                'ab',
                lexer.And([
                    lexer.Literal('a'),
                    lexer.Literal('b'),
                ])
            ),
            (
                '(a)',
                lexer.And([
                    lexer.And([
                        lexer.Literal('a'),
                    ])
                ])
            ),
            (
                '(ab)',
                lexer.And([
                    lexer.And([
                        lexer.Literal('a'),
                        lexer.Literal('b'),
                    ])
                ])
            ),
            ('a*', lexer.And([lexer.ZeroOrMore(lexer.Literal('a'))])),
            ('a+', lexer.And([lexer.OneOrMore(lexer.Literal('a'))])),
            ('a?', lexer.And([lexer.ZeroOrOne(lexer.Literal('a'))])),
            ('a!', lexer.And([lexer.UntilEmpty(lexer.Literal('a'))])),
            ('^a', lexer.And([lexer.Not(lexer.Literal('a'))])),
            ('[a-z]', lexer.And([lexer.Class('a', 'z')])),
            ('(a|b)', lexer.And(
                [lexer.Or([lexer.Literal('a'), lexer.Literal('b')])])),
            ('\\(', lexer.And([lexer.Literal('(')])),
            ('\\\\', lexer.And([lexer.Literal('\\')])),
            ('\\w', lexer.And(
                [lexer.Or([lexer.Literal(c) for c in ' \n\t'])])),
            ('\\n', lexer.And([lexer.Literal('\n')])),
        ]:
            with self.subTest((input, rule)):
                self.assertEqual(rule, loader.load_lexer_rule(input))

    def test_load_parser(self):
        input: str
        parser_: parser.Parser
        for input, parser_ in [
            (
                r'''
                    a -> b;
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.Ref('b'),
                    },
                    loader.load_lexer({})
                )
            ),
            (
                r'''
                    lexer_rule = "abc";
                    a -> lexer_rule;
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.Literal('lexer_rule'),
                    },
                    loader.load_lexer({
                        'lexer_rule': 'abc',
                    })
                )
            ),
            (
                r'''
                    a -> b c;
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.And([parser.Ref('b'), parser.Ref('c')]),
                    },
                    loader.load_lexer({})
                )
            ),
            (
                r'''
                    a -> b | c;
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.Or([parser.Ref('b'), parser.Ref('c')]),
                    },
                    loader.load_lexer({})
                )
            ),
            (
                r'''
                    a -> (b);
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.Ref('b'),
                    },
                    loader.load_lexer({})
                )
            ),
            (
                r'''
                    a -> (b c);
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.And([parser.Ref('b'), parser.Ref('c')]),
                    },
                    loader.load_lexer({})
                )
            ),
            (
                r'''
                    a -> (b | c);
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.Or([parser.Ref('b'), parser.Ref('c')]),
                    },
                    loader.load_lexer({})
                )
            ),
            (
                r'''
                    a -> ((b) (c));
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.And([parser.Ref('b'), parser.Ref('c')]),
                    },
                    loader.load_lexer({})
                )
            ),
            (
                r'''
                    a -> ((b) | (c));
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.Or([parser.Ref('b'), parser.Ref('c')]),
                    },
                    loader.load_lexer({})
                )
            ),
            (
                r'''
                    a -> b*;
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.ZeroOrMore(parser.Ref('b')),
                    },
                    loader.load_lexer({})
                )
            ),
            (
                r'''
                    a -> b+;
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.OneOrMore(parser.Ref('b')),
                    },
                    loader.load_lexer({})
                )
            ),
            (
                r'''
                    a -> b?;
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.ZeroOrOne(parser.Ref('b')),
                    },
                    loader.load_lexer({})
                )
            ),
            (
                r'''
                    a -> b!;
                ''',
                parser.Parser(
                    'a',
                    {
                        'a': parser.UntilEmpty(parser.Ref('b')),
                    },
                    loader.load_lexer({})
                )
            ),
        ]:
            with self.subTest((input, parser_)):
                self.assertEqual(parser_, loader.load_parser(input))
