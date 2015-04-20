import re
import warnings
from json import loads

from jmespath.exceptions import LexerError, EmptyExpressionError


class Lexer(object):
    TOKENS = (
        r'(?P<number>-?\d+)|'
        r'(?P<unquoted_identifier>([a-zA-Z_][a-zA-Z_0-9]*))|'
        r'(?P<quoted_identifier>("(?:\\\\|\\"|[^"])*"))|'
        r'(?P<string_literal>(\'(?:\\\\|\\\'|[^\'])*\'))|'
        r'(?P<literal>(`(?:\\\\|\\`|[^`])*`))|'
        r'(?P<filter>\[\?)|'
        r'(?P<or>\|\|)|'
        r'(?P<pipe>\|)|'
        r'(?P<ne>!=)|'
        r'(?P<rbrace>\})|'
        r'(?P<eq>==)|'
        r'(?P<dot>\.)|'
        r'(?P<star>\*)|'
        r'(?P<gte>>=)|'
        r'(?P<lparen>\()|'
        r'(?P<lbrace>\{)|'
        r'(?P<lte><=)|'
        r'(?P<flatten>\[\])|'
        r'(?P<rbracket>\])|'
        r'(?P<lbracket>\[)|'
        r'(?P<rparen>\))|'
        r'(?P<comma>,)|'
        r'(?P<colon>:)|'
        r'(?P<lt><)|'
        r'(?P<expref>&)|'
        r'(?P<gt>>)|'
        r'(?P<current>@)|'
        r'(?P<skip>[ \t]+)'
    )

    def __init__(self):
        self.master_regex = re.compile(self.TOKENS)

    def tokenize(self, expression):
        if not expression:
            raise EmptyExpressionError()
        previous_column = 0
        for match in self.master_regex.finditer(expression):
            value = match.group()
            start = match.start()
            end = match.end()
            if match.lastgroup == 'skip':
                # Ignore whitespace.
                previous_column = end
                continue
            if start != previous_column:
                bad_value = expression[previous_column:start]
                # Try to give a good error message.
                if bad_value == '"':
                    raise LexerError(
                        lexer_position=previous_column,
                        lexer_value=value,
                        message='Starting quote is missing the ending quote',
                        expression=expression)
                raise LexerError(lexer_position=previous_column,
                                 lexer_value=value,
                                 message='Unknown character',
                                 expression=expression)
            previous_column = end
            token_type = match.lastgroup
            handler = getattr(self, '_token_%s' % token_type.lower(), None)
            if handler is not None:
                value = handler(value, start, end)
            yield {'type': token_type, 'value': value,
                   'start': start, 'end': end}
        # At the end of the loop make sure we've consumed all the input.
        # If we haven't then we have unidentified characters.
        if end != len(expression):
            msg = "Unknown characters at the end of the expression"
            raise LexerError(lexer_position=end,
                             lexer_value='',
                             message=msg, expression=expression)
        else:
            yield {'type': 'eof', 'value': '',
                   'start': len(expression), 'end': len(expression)}

    def _token_number(self, value, start, end):
        return int(value)

    def _token_quoted_identifier(self, value, start, end):
        try:
            return loads(value)
        except ValueError as e:
            error_message = str(e).split(':')[0]
            raise LexerError(lexer_position=start,
                             lexer_value=value,
                             message=error_message)

    def _token_string_literal(self, value, start, end):
        return value[1:-1]

    def _token_literal(self, value, start, end):
        actual_value = value[1:-1]
        actual_value = actual_value.replace('\\`', '`').lstrip()
        # First, if it looks like JSON then we parse it as
        # JSON and any json parsing errors propogate as lexing
        # errors.
        if self._looks_like_json(actual_value):
            try:
                return loads(actual_value)
            except ValueError:
                raise LexerError(lexer_position=start,
                                 lexer_value=value,
                                 message="Bad token %s" % value)
        else:
            potential_value = '"%s"' % actual_value
            try:
                # There's a shortcut syntax where string literals
                # don't have to be quoted.  This is only true if the
                # string doesn't start with chars that could start a valid
                # JSON value.
                value = loads(potential_value)
                warnings.warn("deprecated string literal syntax",
                              PendingDeprecationWarning)
                return value
            except ValueError:
                raise LexerError(lexer_position=start,
                                 lexer_value=value,
                                 message="Bad token %s" % value)

    def _looks_like_json(self, value):
        # Figure out if the string "value" starts with something
        # that looks like json.
        if not value:
            return False
        elif value[0] in ['"', '{', '[']:
            return True
        elif value in ['true', 'false', 'null']:
            return True
        elif value[0] in ['-', '0', '1', '2', '3', '4', '5',
                          '6', '7', '8', '9']:
            # Then this is JSON, return True.
            try:
                loads(value)
                return True
            except ValueError:
                return False
        else:
            return False
