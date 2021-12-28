from core import lexer, parser, processor_test

if 'unittest.util' in __import__('sys').modules:
    # Show full diff in self.assertEqual.
    __import__('sys').modules['unittest.util']._MAX_LENGTH = 999999999


ApplyEqualsCase = processor_test.ApplyEqualsCase[parser.ResultValue,
                                                 parser.StateValue]
ApplyRaisesCase = processor_test.ApplyRaisesCase[parser.StateValue]
ResultAndStateMatcher = processor_test.ResultAndStateMatcher[parser.ResultValue,
                                                             parser.StateValue]
ResultMatcher = processor_test.ResultMatcher[parser.ResultValue]


class ParserTest(processor_test.ProcessorTest[parser.ResultValue, parser.StateValue]):
    def test_literal_match(self):
        self.assertApplyEqualsCases(
            parser.Parser(
                'a',
                {
                    'a': parser.Literal('int'),
                },
                lexer.Lexer({})
            ),
            [
                ApplyEqualsCase(
                    parser.StateValue([lexer.Token('int', '1')]),
                    ResultAndStateMatcher(
                        ResultMatcher(
                            rule_name='a',
                            value=parser.ResultValue('int', '1'),
                        )
                    )
                ),
                ApplyEqualsCase(
                    parser.StateValue(
                        [
                            lexer.Token('int', '1'),
                            lexer.Token('int', '2'),
                        ]
                    ),
                    ResultAndStateMatcher(
                        ResultMatcher(
                            rule_name='a',
                            value=parser.ResultValue('int', '1'),
                        ),
                        parser.StateValue([lexer.Token('int', '2')])
                    )
                ),
            ]
        )

    def test_literal_mismatch(self):
        self.assertApplyRaisesCases(
            parser.Parser(
                'a',
                {
                    'a': parser.Literal('int'),
                },
                lexer.Lexer({})
            ),
            [
                ApplyRaisesCase(
                    parser.StateValue([]),
                    parser.Error(
                        msg='state empty',
                        rule_name='a',
                    )
                ),
                ApplyRaisesCase(
                    parser.StateValue([lexer.Token('str', 'abc')]),
                    parser.Error(
                        msg='literal mismatch expected int got str',
                        rule_name='a',
                    )
                ),
            ]
        )
