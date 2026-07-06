import string
import warnings
from json import loads

from jmespath.exceptions import LexerError, EmptyExpressionError


class Lexer(object):
    START_IDENTIFIER = frozenset(string.ascii_letters + '_')
    VALID_IDENTIFIER = frozenset(string.ascii_letters + string.digits + '_')
    VALID_NUMBER = frozenset(string.digits)
    WHITESPACE = frozenset(" \t\n\r")
    SIMPLE_TOKENS = {
        '.': 'dot',
        '*': 'star',
        ']': 'rbracket',
        ',': 'comma',
        ':': 'colon',
        '@': 'current',
        '(': 'lparen',
        ')': 'rparen',
        '{': 'lbrace',
        '}': 'rbrace',
    }

    def tokenize(self, expression):
        # This scans with a local position index instead of the
        # char-by-char self._next() approach: avoiding a method call
        # and several attribute accesses per character makes
        # tokenization substantially faster.  Runs of identifier,
        # number, and string characters are sliced out of the
        # expression rather than accumulated one char at a time.
        if not expression:
            raise EmptyExpressionError()
        tokens = []
        append = tokens.append
        simple_tokens = self.SIMPLE_TOKENS
        start_identifier = self.START_IDENTIFIER
        valid_identifier = self.VALID_IDENTIFIER
        valid_number = self.VALID_NUMBER
        whitespace = self.WHITESPACE
        length = len(expression)
        pos = 0
        while pos < length:
            char = expression[pos]
            simple_type = simple_tokens.get(char)
            if simple_type is not None:
                append({'type': simple_type, 'value': char,
                        'start': pos, 'end': pos + 1})
                pos += 1
            elif char in start_identifier:
                start = pos
                pos += 1
                while pos < length and expression[pos] in valid_identifier:
                    pos += 1
                append({'type': 'unquoted_identifier',
                        'value': expression[start:pos],
                        'start': start, 'end': pos})
            elif char in whitespace:
                pos += 1
                while pos < length and expression[pos] in whitespace:
                    pos += 1
            elif char == '[':
                next_char = expression[pos + 1] if pos + 1 < length else ''
                if next_char == ']':
                    append({'type': 'flatten', 'value': '[]',
                            'start': pos, 'end': pos + 2})
                    pos += 2
                elif next_char == '?':
                    append({'type': 'filter', 'value': '[?',
                            'start': pos, 'end': pos + 2})
                    pos += 2
                else:
                    append({'type': 'lbracket', 'value': '[',
                            'start': pos, 'end': pos + 1})
                    pos += 1
            elif char in valid_number:
                start = pos
                pos += 1
                while pos < length and expression[pos] in valid_number:
                    pos += 1
                append({'type': 'number', 'value': int(expression[start:pos]),
                        'start': start, 'end': pos})
            elif char == "'":
                token, pos = self._consume_raw_string_literal(
                    expression, pos)
                append(token)
            elif char == '|':
                token, pos = self._match_or_else(
                    expression, pos, '|', 'or', 'pipe')
                append(token)
            elif char == '&':
                token, pos = self._match_or_else(
                    expression, pos, '&', 'and', 'expref')
                append(token)
            elif char == '`':
                token, pos = self._consume_literal(expression, pos)
                append(token)
            elif char == '-':
                # Negative number.
                start = pos
                pos += 1
                while pos < length and expression[pos] in valid_number:
                    pos += 1
                buff = expression[start:pos]
                if len(buff) > 1:
                    append({'type': 'number', 'value': int(buff),
                            'start': start, 'end': start + len(buff)})
                else:
                    raise LexerError(lexer_position=start,
                                     lexer_value=buff,
                                     message="Unknown token '%s'" % buff)
            elif char == '"':
                token, pos = self._consume_quoted_identifier(expression, pos)
                append(token)
            elif char == '<':
                token, pos = self._match_or_else(
                    expression, pos, '=', 'lte', 'lt')
                append(token)
            elif char == '>':
                token, pos = self._match_or_else(
                    expression, pos, '=', 'gte', 'gt')
                append(token)
            elif char == '!':
                token, pos = self._match_or_else(
                    expression, pos, '=', 'ne', 'not')
                append(token)
            elif char == '=':
                if pos + 1 < length and expression[pos + 1] == '=':
                    append({'type': 'eq', 'value': '==',
                            'start': pos, 'end': pos + 1})
                    pos += 2
                else:
                    raise LexerError(
                        lexer_position=pos,
                        lexer_value='=',
                        message="Unknown token '='")
            else:
                raise LexerError(lexer_position=pos,
                                 lexer_value=char,
                                 message="Unknown token %s" % char)
        append({'type': 'eof', 'value': '',
                'start': length, 'end': length})
        return tokens

    def _consume_until(self, expression, start, delimiter):
        # Consume until the delimiter is reached, allowing for the
        # delimiter to be escaped with "\".  ``start`` points at the
        # opening delimiter.  Returns the consumed string (escaping
        # backslashes preserved, as before) and the position of the
        # first character after the closing delimiter.
        pos = start + 1
        chunks = []
        while True:
            delim_index = expression.find(delimiter, pos)
            if delim_index == -1:
                # We're at the EOF.
                raise LexerError(lexer_position=start,
                                 lexer_value=expression[start:],
                                 message="Unclosed %s delimiter" % delimiter)
            backslash_index = expression.find('\\', pos)
            if backslash_index == -1 or delim_index < backslash_index:
                chunks.append(expression[pos:delim_index])
                # Skip the closing delimiter.
                return ''.join(chunks), delim_index + 1
            # An escape: consume the backslash and the following
            # character (whatever it is, including the delimiter).
            if backslash_index + 2 > len(expression):
                raise LexerError(lexer_position=start,
                                 lexer_value=expression[start:],
                                 message="Unclosed %s delimiter" % delimiter)
            chunks.append(expression[pos:backslash_index + 2])
            pos = backslash_index + 2

    def _token_end_position(self, expression, pos):
        # The historical scanner never advanced past the final
        # character of the expression, so a token whose closing
        # delimiter is the last character reports its end position
        # one short.  Preserved for compatibility.
        if pos >= len(expression):
            return len(expression) - 1
        return pos

    def _consume_literal(self, expression, start):
        lexeme, pos = self._consume_until(expression, start, '`')
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
                                 lexer_value=expression[start:],
                                 message="Bad token %s" % lexeme)
        token_len = self._token_end_position(expression, pos) - start
        return ({'type': 'literal', 'value': parsed_json,
                 'start': start, 'end': token_len}, pos)

    def _consume_quoted_identifier(self, expression, start):
        consumed, pos = self._consume_until(expression, start, '"')
        lexeme = '"' + consumed + '"'
        try:
            token_len = self._token_end_position(expression, pos) - start
            return ({'type': 'quoted_identifier', 'value': loads(lexeme),
                     'start': start, 'end': token_len}, pos)
        except ValueError as e:
            error_message = str(e).split(':')[0]
            raise LexerError(lexer_position=start,
                             lexer_value=lexeme,
                             message=error_message)

    def _consume_raw_string_literal(self, expression, start):
        consumed, pos = self._consume_until(expression, start, "'")
        lexeme = consumed.replace("\\'", "'")
        token_len = self._token_end_position(expression, pos) - start
        return ({'type': 'literal', 'value': lexeme,
                 'start': start, 'end': token_len}, pos)

    def _match_or_else(self, expression, start, expected, match_type,
                       else_type):
        current = expression[start]
        if start + 1 < len(expression) and expression[start + 1] == expected:
            return ({'type': match_type, 'value': current + expected,
                     'start': start, 'end': start + 1}, start + 2)
        return ({'type': else_type, 'value': current,
                 'start': start, 'end': start}, start + 1)
