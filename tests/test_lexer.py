import warnings
from tests import unittest

from jmespath import lexer
from jmespath.exceptions import LexerError, EmptyExpressionError


class TestRegexLexer(unittest.TestCase):

    def setUp(self):
        self.lexer = lexer.Lexer()

    def assert_tokens(self, actual, expected):
        # The expected tokens only need to specify the
        # type and value.  The line/column numbers are not
        # checked, and we use assertEqual for the tests
        # that check those line numbers.
        stripped = []
        for item in actual:
            stripped.append({'type': item['type'], 'value': item['value']})
        # Every tokenization should end in eof, so we automatically
        # check that value, strip it off the end, and then
        # verify the remaining tokens against the expected.
        # That way the tests don't need to add eof to every
        # assert_tokens call.
        self.assertEqual(stripped[-1]['type'], 'eof')
        stripped.pop()
        self.assertEqual(stripped, expected)

    def test_empty_string(self):
        with self.assertRaises(EmptyExpressionError):
            list(self.lexer.tokenize(''))

    def test_field(self):
        tokens = list(self.lexer.tokenize('foo'))
        self.assert_tokens(tokens, [{'type': 'unquoted_identifier',
                                     'value': 'foo'}])

    def test_number(self):
        tokens = list(self.lexer.tokenize('24'))
        self.assert_tokens(tokens, [{'type': 'number',
                                     'value': 24}])

    def test_negative_number(self):
        tokens = list(self.lexer.tokenize('-24'))
        self.assert_tokens(tokens, [{'type': 'number',
                                     'value': -24}])

    def test_quoted_identifier(self):
        tokens = list(self.lexer.tokenize('"foobar"'))
        self.assert_tokens(tokens, [{'type': 'quoted_identifier',
                                     'value': "foobar"}])

    def test_json_escaped_value(self):
        tokens = list(self.lexer.tokenize('"\u2713"'))
        self.assert_tokens(tokens, [{'type': 'quoted_identifier',
                                     'value': u"\u2713"}])

    def test_number_expressions(self):
        tokens = list(self.lexer.tokenize('foo.bar.baz'))
        self.assert_tokens(tokens, [
            {'type': 'unquoted_identifier', 'value': 'foo'},
            {'type': 'dot', 'value': '.'},
            {'type': 'unquoted_identifier', 'value': 'bar'},
            {'type': 'dot', 'value': '.'},
            {'type': 'unquoted_identifier', 'value': 'baz'},
        ])

    def test_space_separated(self):
        tokens = list(self.lexer.tokenize('foo.bar[*].baz | a || b'))
        self.assert_tokens(tokens, [
            {'type': 'unquoted_identifier', 'value': 'foo'},
            {'type': 'dot', 'value': '.'},
            {'type': 'unquoted_identifier', 'value': 'bar'},
            {'type': 'lbracket', 'value': '['},
            {'type': 'star', 'value': '*'},
            {'type': 'rbracket', 'value': ']'},
            {'type': 'dot', 'value': '.'},
            {'type': 'unquoted_identifier', 'value': 'baz'},
            {'type': 'pipe', 'value': '|'},
            {'type': 'unquoted_identifier', 'value': 'a'},
            {'type': 'or', 'value': '||'},
            {'type': 'unquoted_identifier', 'value': 'b'},
        ])

    def test_literal(self):
        tokens = list(self.lexer.tokenize('`[0, 1]`'))
        self.assert_tokens(tokens, [
            {'type': 'literal', 'value': [0, 1]},
        ])

    def test_literal_string(self):
        tokens = list(self.lexer.tokenize('`foobar`'))
        self.assert_tokens(tokens, [
            {'type': 'literal', 'value': "foobar"},
        ])

    def test_literal_number(self):
        tokens = list(self.lexer.tokenize('`2`'))
        self.assert_tokens(tokens, [
            {'type': 'literal', 'value': 2},
        ])

    def test_literal_with_invalid_json(self):
        with self.assertRaises(LexerError):
            list(self.lexer.tokenize('`foo"bar`'))

    def test_literal_with_empty_string(self):
        tokens = list(self.lexer.tokenize('``'))
        self.assert_tokens(tokens, [{'type': 'literal', 'value': ''}])

    def test_position_information(self):
        tokens = list(self.lexer.tokenize('foo'))
        self.assertEqual(
            tokens,
            [{'type': 'unquoted_identifier', 'value': 'foo',
              'start': 0, 'end': 3},
              {'type': 'eof', 'value': '', 'start': 3, 'end': 3}]
        )

    def test_position_multiple_tokens(self):
        tokens = list(self.lexer.tokenize('foo.bar'))
        self.assertEqual(
            tokens,
            [{'type': 'unquoted_identifier', 'value': 'foo',
              'start': 0, 'end': 3},
             {'type': 'dot', 'value': '.',
              'start': 3, 'end': 4},
             {'type': 'unquoted_identifier', 'value': 'bar',
              'start': 4, 'end': 7},
             {'type': 'eof', 'value': '',
              'start': 7, 'end': 7},
             ]
        )

    def test_adds_quotes_when_invalid_json(self):
        tokens = list(self.lexer.tokenize('`{{}`'))
        self.assertEqual(
            tokens,
            [{'type': 'literal', 'value': '{{}',
              'start': 0, 'end': 4},
             {'type': 'eof', 'value': '',
              'start': 5, 'end': 5}
             ]
        )

    def test_unknown_character(self):
        with self.assertRaises(LexerError) as e:
            tokens = list(self.lexer.tokenize('foo[0^]'))

    def test_bad_first_character(self):
        with self.assertRaises(LexerError):
            tokens = list(self.lexer.tokenize('^foo[0]'))

    def test_unknown_character_with_identifier(self):
        with self.assertRaisesRegex(LexerError, "Unknown token"):
            list(self.lexer.tokenize('foo-bar'))

    def test_raw_string_literal(self):
        tokens = list(self.lexer.tokenize("'foo'"))
        self.assert_tokens(tokens, [{'type': 'literal', 'value': 'foo'}])

    def test_raw_string_literal_with_spaces(self):
        tokens = list(self.lexer.tokenize("'  foo  '"))
        self.assert_tokens(tokens, [{'type': 'literal', 'value': '  foo  '}])

    def test_raw_string_literal_escaped_quote(self):
        # A backslash-escaped single quote inside a raw literal becomes a
        # plain single quote in the result value.
        tokens = list(self.lexer.tokenize(r"'foo\'bar'"))
        self.assert_tokens(tokens, [{'type': 'literal', 'value': "foo'bar"}])

    def test_raw_string_literal_backslash_not_before_quote(self):
        # A backslash not followed by a single quote is kept as-is.
        tokens = list(self.lexer.tokenize(r"'\z'"))
        self.assert_tokens(tokens, [{'type': 'literal', 'value': r'\z'}])

    def test_lone_dash_raises_lexer_error(self):
        # A bare '-' with no digits following it is not a valid token.
        with self.assertRaises(LexerError):
            list(self.lexer.tokenize('-'))

    def test_single_equals_raises_lexer_error(self):
        # '=' is only valid as part of '=='; a lone '=' should error.
        with self.assertRaises(LexerError):
            list(self.lexer.tokenize('foo=bar'))

    def test_equals_at_eof_raises_lexer_error(self):
        # '=' at the very end of the expression (no following char) also
        # has a separate position-calculation branch that should still raise.
        with self.assertRaises(LexerError):
            list(self.lexer.tokenize('='))

    def test_deprecated_backtick_string_emits_warning(self):
        # A bare word inside backticks is invalid JSON; the lexer falls back
        # to wrapping it in quotes (deprecated JEP-12 syntax) and must emit
        # a PendingDeprecationWarning.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            list(self.lexer.tokenize('`foobar`'))
        self.assertEqual(len(caught), 1)
        self.assertTrue(issubclass(caught[0].category, PendingDeprecationWarning))
        self.assertIn("deprecated", str(caught[0].message).lower())


if __name__ == '__main__':
    unittest.main()
