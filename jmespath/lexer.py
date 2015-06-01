import string
import warnings
from json import loads

from jmespath.exceptions import LexerError, EmptyExpressionError


START_IDENTIFIER = set(string.ascii_letters + '_')
VALID_IDENTIFIER = set(string.ascii_letters + string.digits + '_')
START_NUMBER = set(string.digits + '-')
VALID_NUMBER = set(string.digits)
WHITESPACE = set(" \t\n\r")
SIMPLE_TOKENS = {
    '.': 'dot',
    '*': 'star',
    ']': 'rbracket',
    ',': 'comma',
    ':': 'colon',
    '@': 'current',
    '&': 'expref',
    '(': 'lparen',
    ')': 'rparen',
    '{': 'lbrace',
    '}': 'rbrace'
}


class Scanner(object):
    def __init__(self, expression):
        if not expression:
            raise EmptyExpressionError()
        self.expression = expression
        self.pos = 0
        self.chars = list(self.expression)
        self.len = len(self.expression)
        self.current = self.chars[self.pos]

    def next(self):
        if self.pos == self.len - 1:
            self.current = None
        else:
            self.pos += 1
            self.current = self.chars[self.pos]
        return self.current

    def in_delimiter(self, delimiter):
        start = self.pos
        buffer = ''
        self.next()
        while self.current != delimiter:
            if self.current == '\\':
                buffer += '\\'
                self.next()
            if self.current is None:
                print(buffer)
                raise LexerError(lexer_position=start,
                                 lexer_value=self.expression,
                                 message="Unclosed delimiter: %s" % buffer)
            buffer += self.current
            self.next()
        self.next()
        return buffer


class Lexer(object):
    def tokenize(self, expression):
        scanner = Scanner(expression)
        while scanner.current is not None:
            if scanner.current in SIMPLE_TOKENS:
                yield {'type': SIMPLE_TOKENS[scanner.current],
                       'value': scanner.current,
                       'start': scanner.pos, 'end': scanner.pos}
                scanner.next()
            elif scanner.current in START_IDENTIFIER:
                start = scanner.pos
                buffer = scanner.current
                while scanner.next() in VALID_IDENTIFIER:
                    buffer += scanner.current
                yield {'type': 'unquoted_identifier', 'value': buffer,
                       'start': start, 'end': len(buffer)}
            elif scanner.current in WHITESPACE:
                scanner.next()
            elif scanner.current == '[':
                start = scanner.pos
                next_char = scanner.next()
                if next_char == ']':
                    scanner.next()
                    yield {'type': 'flatten', 'value': '[]',
                           'start': start, 'end': start + 1}
                elif next_char == '?':
                    scanner.next()
                    yield {'type': 'filter', 'value': '[?',
                           'start': start, 'end': start + 1}
                else:
                    yield {'type': 'lbracket', 'value': '[',
                           'start': start, 'end': start}
            elif scanner.current == "'":
                yield self._consume_raw_string_literal(scanner)
            elif scanner.current == '|':
                yield self._match_or_else(scanner, '|', 'or', 'pipe')
            elif scanner.current == '`':
                yield self._consume_literal(scanner)
            elif scanner.current in START_NUMBER:
                start = scanner.pos
                buffer = scanner.current
                while scanner.next() in VALID_NUMBER:
                    buffer += scanner.current
                yield {'type': 'number', 'value': int(buffer),
                       'start': start, 'end': len(buffer)}
            elif scanner.current == '"':
                yield self._consume_quoted_identifier(scanner)
            elif scanner.current == '<':
                yield self._match_or_else(scanner, '=', 'lte', 'lt')
            elif scanner.current == '>':
                yield self._match_or_else(scanner, '=', 'gte', 'gt')
            elif scanner.current == '!':
                yield self._match_or_else(scanner, '=', 'ne', 'unknown')
            elif scanner.current == '=':
                yield self._match_or_else(scanner, '=', 'eq', 'unknown')
            else:
                yield {'type': 'unknown', 'value': scanner.current,
                       'start': scanner.pos, 'end': scanner.pos}
                scanner.next()
        yield {'type': 'eof', 'value': '',
               'start': len(expression), 'end': len(expression)}

    def _consume_literal(self, scanner):
        start = scanner.pos
        lexeme = scanner.in_delimiter('`')
        try:
            # Assume it is valid JSON and attempt to parse.
            parsed_json = loads(lexeme)
        except ValueError:
            try:
                # Invalid JSON values should be converted to quoted
                # JSON strings during the JEP-12 deprecation period.
                parsed_json = loads('"%s"' % lexeme.lstrip())
                warnings.warn("deprecated string literal syntax",
                              PendingDeprecationWarning)
            except ValueError:
                raise LexerError(lexer_position=start,
                                 lexer_value=lexeme,
                                 message="Bad token %s" % lexeme)
        return {'type': 'literal', 'value': parsed_json,
                'start': start, 'end': len(lexeme)}

    def _consume_quoted_identifier(self, scanner):
        start = scanner.pos
        lexeme = scanner.in_delimiter('"')
        try:
            return {'type': 'quoted_identifier', 'value': loads(lexeme),
                    'start': start, 'end': len(lexeme)}
        except ValueError as e:
            error_message = str(e).split(':')[0]
            raise LexerError(lexer_position=start,
                             lexer_value=lexeme,
                             message=error_message)

    def _consume_raw_string_literal(self, scanner):
        start = scanner.pos
        lexeme = scanner.in_delimiter("'")
        return {'type': 'literal', 'value': lexeme,
                'start': start, 'end': len(lexeme)}

    def _match_or_else(self, scanner, expected, match_type, else_type):
        start = scanner.pos
        current = scanner.current
        next_char = scanner.next()
        if next_char == expected:
            scanner.next()
            return {'type': match_type, 'value': current + next_char,
                    'start': start, 'end': start + 1}
        return {'type': else_type, 'value': current,
                'start': start, 'end': start}
