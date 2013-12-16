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
        'LBRACKET',
        'RBRACKET',
        'LBRACE',
        'RBRACE',
        'OR',
        'NUMBER',
        'IDENTIFIER',
        'COMMA',
        'COLON',
    ) + tuple(reserved.values())

    t_STAR = r'\*'
    t_DOT = r'\.'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_LBRACE = r'\{'
    t_RBRACE = r'\}'
    t_OR = r'\|\|'
    t_COMMA = r','
    t_COLON = r':'
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
            t.value = loads(t.value)
            return t
        return t

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
