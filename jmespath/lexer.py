class LexerDefinition(object):
    reserved = {
        'or': 'OR',
    }

    tokens = (
        'STAR',
        'DOT',
        'LBRACKET',
        'RBRACKET',
        'NUMBER',
        'IDENTIFIER',
    ) + tuple(reserved.values())

    t_STAR = r'\*'
    t_DOT = r'\.'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_ignore = ' '

    def t_NUMBER(self, t):
        r'-?\d+'
        t.value = int(t.value)
        return t

    def t_IDENTIFIER(self, t):
        r'[a-zA-Z_][a-zA-Z_0-9]*'
        t.type = self.reserved.get(t.value, 'IDENTIFIER')
        return t

    def t_error(self, t):
        raise ValueError("Illegal token value '%s'" % t.value)
