import re
from json import loads

from jmespath.compat import with_str_method

@with_str_method
class LexerError(ValueError):
    def __init__(self, lexer_position, lexer_value, message):
        self.lexer_position = lexer_position
        self.lexer_value = lexer_value
        self.message = message
        super(LexerError, self).__init__(lexer_position,
                                         lexer_value,
                                         message)
        # Whatever catches LexerError can set this.
        self.expression = None

    def __str__(self):
        underline = ' ' * self.lexer_position + '^'
        return 'Bad jmespath expression: %s:\n%s\n%s' % (
            self.message, self.expression, underline)


class LexerDefinition(object):
    reflags = re.DOTALL
    reserved = {}
    tokens = (
        'STAR',
        'DOT',
        'FILTER',
        'LBRACKET',
        'RBRACKET',
        'LBRACE',
        'RBRACE',
        'OR',
        'NUMBER',
        'IDENTIFIER',
        'COMMA',
        'COLON',
        'LT',
        'LTE',
        'GT',
        'GTE',
        'EQ',
        'NE',
        'LITERAL',
    ) + tuple(reserved.values())

    t_STAR = r'\*'
    t_DOT = r'\.'
    t_FILTER = r'\[\?'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_LBRACE = r'\{'
    t_RBRACE = r'\}'
    t_OR = r'\|\|'
    t_COMMA = r','
    t_COLON = r':'
    t_LT = r'<'
    t_LTE = r'<='
    t_GT = r'>'
    t_GTE = r'>='
    t_EQ = r'=='
    t_NE = r'!='
    t_ignore = ' '

    def t_NUMBER(self, t):
        r'-?\d+'
        t.value = int(t.value)
        return t

    def t_IDENTIFIER(self, t):
        r'(([a-zA-Z_][a-zA-Z_0-9]*)|("(?:\\"|[^"])*"))'
        t.type = self.reserved.get(t.value, 'IDENTIFIER')
        i = 0
        if t.value[0] == '"' and t.value[-1] == '"':
            try:
                t.value = loads(t.value)
            except ValueError as e:
                error_message = str(e).split(':')[0]
                raise LexerError(lexer_position=t.lexpos,
                                 lexer_value=t.value,
                                 message=error_message)
            return t
        return t

    def t_LITERAL(self, t):
        r'(`(?:\\`|[^`])*`)'
        actual_value = t.value[1:-1]
        if actual_value not in ('true', 'false', 'null') and (
                not self._looks_like_json(actual_value)):
            # There's a shortcut syntax where string literals
            # don't have to be quoted.  This is only true if the
            # string doesn't start with chars that could start a valid
            # JSON value.
            actual_value = '"%s"' % actual_value
        try:
            actual_value = actual_value.replace('\\`', '`')
            t.value = loads(actual_value)
        except ValueError:
            raise LexerError(lexer_position=t.lexpos,
                             lexer_value=t.value,
                             message=("Bad token %s" % t.value))
        return t

    def _looks_like_json(self, value):
        # Figure out if the string "value" starts with something
        # that looks like json.
        if value and value[0] in ['"', '{', '[', '-', '0', '1', '2',
                                  '3', '4', '5', '6', '7', '8', '9']:
            # Then this is JSON, return True.
            return True
        else:
            return False

    def t_error(self, t):
        # Try to be helpful in the case where they have a missing
        # quote char.
        if t.value.startswith('"'):
            raise LexerError(
                lexer_position=t.lexpos,
                lexer_value=t.value,
                message=("Bad token '%s': starting quote is missing "
                         "the ending quote" % t.value))
        raise ValueError("Illegal token value '%s'" % t.value)
