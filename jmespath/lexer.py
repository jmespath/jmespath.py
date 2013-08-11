import re

class LexerDefinition(object):
    reflags = re.DOTALL
    reserved = {}
    tokens = (
        'STAR',
        'DOT',
        'LBRACKET',
        'RBRACKET',
        'OR',
        'NUMBER',
        'IDENTIFIER',
    ) + tuple(reserved.values())

    t_STAR = r'\*'
    t_DOT = r'\.'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_OR = r'\|\|'
    t_ignore = ' '

    def t_NUMBER(self, t):
        r'-?\d+'
        t.value = int(t.value)
        return t

    def t_IDENTIFIER(self, t):
        r'(([a-zA-Z_][a-zA-Z_0-9]*)|("(\"|.)*"))'
        t.type = self.reserved.get(t.value, 'IDENTIFIER')
        i = 0
        if t.value[0] == '"' and t.value[-1] == '"':
            t.value = t.value[1:-1]
            if '\\"' in t.value:
                t.value = t.value.replace('\\"', '"')
            return t
        return t


    def t_error(self, t):
        raise ValueError("Illegal token value '%s'" % t.value)
