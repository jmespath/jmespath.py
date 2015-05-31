import string
import warnings
from json import loads

from jmespath.exceptions import LexerError, EmptyExpressionError


VALID_NUMBER = set(string.digits)
VALID_IDENTIFIER = set(string.ascii_letters + string.digits + '_')
STATE_IDENTIFIER = 0;
STATE_NUMBER = 1;
STATE_SINGLE_CHAR = 2;
STATE_WHITESPACE = 3;
STATE_STRING_LITERAL = 4;
STATE_QUOTED_STRING = 5;
STATE_JSON_LITERAL = 6;
STATE_LBRACKET = 7;
STATE_PIPE = 8;
STATE_LT = 9;
STATE_GT = 10;
STATE_EQ = 11;
STATE_NOT = 12;
TRANSITION_TABLE = {
    '<': STATE_LT,
    '>': STATE_GT,
    '=': STATE_EQ,
    '!': STATE_NOT,
    '[': STATE_LBRACKET,
    '|': STATE_PIPE,
    '`': STATE_JSON_LITERAL,
    '"': STATE_QUOTED_STRING,
    "'": STATE_STRING_LITERAL,
    '-': STATE_NUMBER,
    '0': STATE_NUMBER,
    '1': STATE_NUMBER,
    '2': STATE_NUMBER,
    '3': STATE_NUMBER,
    '4': STATE_NUMBER,
    '5': STATE_NUMBER,
    '6': STATE_NUMBER,
    '7': STATE_NUMBER,
    '8': STATE_NUMBER,
    '9': STATE_NUMBER,
    '.': STATE_SINGLE_CHAR,
    '*': STATE_SINGLE_CHAR,
    ']': STATE_SINGLE_CHAR,
    ',': STATE_SINGLE_CHAR,
    ':': STATE_SINGLE_CHAR,
    '@': STATE_SINGLE_CHAR,
    '&': STATE_SINGLE_CHAR,
    '(': STATE_SINGLE_CHAR,
    ')': STATE_SINGLE_CHAR,
    '{': STATE_SINGLE_CHAR,
    '}': STATE_SINGLE_CHAR,
    '_': STATE_IDENTIFIER,
    'A': STATE_IDENTIFIER,
    'B': STATE_IDENTIFIER,
    'C': STATE_IDENTIFIER,
    'D': STATE_IDENTIFIER,
    'E': STATE_IDENTIFIER,
    'F': STATE_IDENTIFIER,
    'G': STATE_IDENTIFIER,
    'H': STATE_IDENTIFIER,
    'I': STATE_IDENTIFIER,
    'J': STATE_IDENTIFIER,
    'K': STATE_IDENTIFIER,
    'L': STATE_IDENTIFIER,
    'M': STATE_IDENTIFIER,
    'N': STATE_IDENTIFIER,
    'O': STATE_IDENTIFIER,
    'P': STATE_IDENTIFIER,
    'Q': STATE_IDENTIFIER,
    'R': STATE_IDENTIFIER,
    'S': STATE_IDENTIFIER,
    'T': STATE_IDENTIFIER,
    'U': STATE_IDENTIFIER,
    'V': STATE_IDENTIFIER,
    'W': STATE_IDENTIFIER,
    'X': STATE_IDENTIFIER,
    'Y': STATE_IDENTIFIER,
    'Z': STATE_IDENTIFIER,
    'a': STATE_IDENTIFIER,
    'b': STATE_IDENTIFIER,
    'c': STATE_IDENTIFIER,
    'd': STATE_IDENTIFIER,
    'e': STATE_IDENTIFIER,
    'f': STATE_IDENTIFIER,
    'g': STATE_IDENTIFIER,
    'h': STATE_IDENTIFIER,
    'i': STATE_IDENTIFIER,
    'j': STATE_IDENTIFIER,
    'k': STATE_IDENTIFIER,
    'l': STATE_IDENTIFIER,
    'm': STATE_IDENTIFIER,
    'n': STATE_IDENTIFIER,
    'o': STATE_IDENTIFIER,
    'p': STATE_IDENTIFIER,
    'q': STATE_IDENTIFIER,
    'r': STATE_IDENTIFIER,
    's': STATE_IDENTIFIER,
    't': STATE_IDENTIFIER,
    'u': STATE_IDENTIFIER,
    'v': STATE_IDENTIFIER,
    'w': STATE_IDENTIFIER,
    'x': STATE_IDENTIFIER,
    'y': STATE_IDENTIFIER,
    'z': STATE_IDENTIFIER,
    ' ': STATE_WHITESPACE,
    "\t": STATE_WHITESPACE,
    "\n": STATE_WHITESPACE,
    "\r": STATE_WHITESPACE
}
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

    def in_delimter(self, delimiter):
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
            if not scanner.current in TRANSITION_TABLE:
                # The current char must be in the transition table to
                # be valid.
                yield {'type': 'unknown', 'value': scanner.current,
                       'start': scanner.pos, 'end': scanner.pos}
                scanner.next()
                continue
            state = TRANSITION_TABLE[scanner.current]
            if state == STATE_SINGLE_CHAR:
                yield {'type': SIMPLE_TOKENS[scanner.current],
                       'value': scanner.current,
                       'start': scanner.pos, 'end': scanner.pos}
                scanner.next()
            elif state == STATE_IDENTIFIER:
                start = scanner.pos
                buffer = scanner.current
                while scanner.next() in VALID_IDENTIFIER:
                    buffer += scanner.current
                yield {'type': 'identifier', 'value': buffer,
                       'start': start, 'end': len(buffer)}
            elif state == STATE_WHITESPACE:
                scanner.next()
            elif state == STATE_LBRACKET:
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
            elif state == STATE_STRING_LITERAL:
                yield self._consume_raw_string_literal(scanner)
            elif state == STATE_PIPE:
                yield self._match_or_else(scanner, '|', 'or', 'pipe')
            elif state == STATE_JSON_LITERAL:
                yield self._consume_literal(scanner)
            elif state == STATE_NUMBER:
                start = scanner.pos
                buffer = scanner.current
                while scanner.next() in VALID_NUMBER:
                    buffer += scanner.current
                yield {'type': 'number', 'value': int(buffer),
                       'start': start, 'end': len(buffer)}
            elif state == STATE_QUOTED_STRING:
                yield self._consume_quoted_identifier(scanner)
            elif state == STATE_LT:
                yield self._match_or_else(scanner, '=', 'lte', 'lt')
            elif state == STATE_GT:
                yield self._match_or_else(scanner, '=', 'gte', 'gt')
            elif state == STATE_EQ:
                yield self._match_or_else(scanner, '=', 'eq', 'unknown')
            elif state == STATE_NOT:
                yield self._match_or_else(scanner, '=', 'ne', 'unknown')
        yield {'type': 'eof', 'value': '',
               'start': len(expression), 'end': len(expression)}

    def _consume_literal(self, scanner):
        start = scanner.pos
        lexeme = scanner.in_delimter('`')
        try:
            # Assume it is valid JSON and attempt to parse.
            parsed_json = loads(lexeme)
        except ValueError:
            try:
                # Invalid JSON values should be converted to quoted
                # JSON strings during the JEP-12 deprecation period.
                parsed_json = loads('"%s"' % lexeme)
                warnings.warn("deprecated string literal syntax",
                              PendingDeprecationWarning)
            except ValueError:
                raise LexerError(lexer_position=start,
                                 lexer_value=lexeme,
                                 message="Bad token %s" % value)
        return {'type': 'literal', 'value': parsed_json,
                'start': start, 'end': len(lexeme)}

    def _consume_quoted_identifier(self, scanner):
        start = scanner.pos
        lexeme = scanner.in_delimter('"')
        try:
            return {'type': 'identifier', 'value': loads(lexeme),
                    'start': start, 'end': len(lexeme)}
        except ValueError as e:
            error_message = str(e).split(':')[0]
            raise LexerError(lexer_position=start,
                             lexer_value=lexeme,
                             message=error_message)

    def _consume_raw_string_literal(self, scanner):
        start = scanner.pos
        lexeme = scanner.in_delimter("'")
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
