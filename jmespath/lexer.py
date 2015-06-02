import string
import warnings
from json import loads

from jmespath.exceptions import LexerError, EmptyExpressionError


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
        buff = ''
        self.next()
        while self.current != delimiter:
            if self.current == '\\':
                buff += '\\'
                self.next()
            if self.current is None:
                raise LexerError(lexer_position=start,
                                 lexer_value=self.expression,
                                 message="Unclosed %s delimiter" % delimiter)
            buff += self.current
            self.next()
        # Skip the closing delimiter.
        self.next()
        return buff


class Lexer(object):
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

    def tokenize(self, expression):
        scanner = Scanner(expression)
        while scanner.current is not None:
            if scanner.current in self.SIMPLE_TOKENS:
                yield {'type': self.SIMPLE_TOKENS[scanner.current],
                       'value': scanner.current,
                       'start': scanner.pos, 'end': scanner.pos + 1}
                scanner.next()
            elif scanner.current in self.START_IDENTIFIER:
                start = scanner.pos
                buff = scanner.current
                while scanner.next() in self.VALID_IDENTIFIER:
                    buff += scanner.current
                yield {'type': 'unquoted_identifier', 'value': buff,
                       'start': start, 'end': start + len(buff)}
            elif scanner.current in self.WHITESPACE:
                scanner.next()
            elif scanner.current == '[':
                start = scanner.pos
                next_char = scanner.next()
                if next_char == ']':
                    scanner.next()
                    yield {'type': 'flatten', 'value': '[]',
                           'start': start, 'end': start + 2}
                elif next_char == '?':
                    scanner.next()
                    yield {'type': 'filter', 'value': '[?',
                           'start': start, 'end': start + 2}
                else:
                    yield {'type': 'lbracket', 'value': '[',
                           'start': start, 'end': start + 1}
            elif scanner.current == "'":
                yield self._consume_raw_string_literal(scanner)
            elif scanner.current == '|':
                yield self._match_or_else(scanner, '|', 'or', 'pipe')
            elif scanner.current == '`':
                yield self._consume_literal(scanner)
            elif scanner.current in self.START_NUMBER:
                start = scanner.pos
                buff = scanner.current
                while scanner.next() in self.VALID_NUMBER:
                    buff += scanner.current
                yield {'type': 'number', 'value': int(buff),
                       'start': start, 'end': start + len(buff)}
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
                raise LexerError(lexer_position=scanner.pos,
                                 lexer_value=scanner.current,
                                 message="Unknown token %s" % scanner.current)
        yield {'type': 'eof', 'value': '',
               'start': len(expression), 'end': len(expression)}

    def _consume_literal(self, scanner):
        start = scanner.pos
        lexeme = scanner.in_delimiter('`')
        lexeme = lexeme.replace('\\`', '`')
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
        token_len = scanner.pos - start
        return {'type': 'literal', 'value': parsed_json,
                'start': start, 'end': token_len}

    def _consume_quoted_identifier(self, scanner):
        start = scanner.pos
        lexeme = '"' + scanner.in_delimiter('"') + '"'
        try:
            token_len = scanner.pos - start
            return {'type': 'quoted_identifier', 'value': loads(lexeme),
                    'start': start, 'end': token_len}
        except ValueError as e:
            error_message = str(e).split(':')[0]
            raise LexerError(lexer_position=start,
                             lexer_value=lexeme,
                             message=error_message)

    def _consume_raw_string_literal(self, scanner):
        start = scanner.pos
        lexeme = scanner.in_delimiter("'")
        token_len = scanner.pos - start
        return {'type': 'literal', 'value': lexeme,
                'start': start, 'end': token_len}

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
