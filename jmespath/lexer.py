import ply.lex

class LexerDefinition(object):
    tokens = (
        'STAR',
        'DOT',
        'LBRACKET',
        'RBRACKET',
        'NUMBER',
        'IDENTIFIER',
    )

    reserved = {}
    t_STAR = r'\*'
    t_DOT = r'\.'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'

    def t_NUMBER(self, t):
        r'-?\d+'
        t.value = int(t.value)
        return t

    def t_IDENTIFIER(self, t):
        r'[a-zA-Z_][a-zA-Z_0-9]*'
        t.type = self.reserved.get(t.value, 'IDENTIFIER')
        return t

    def t_error(self, t):
        raise ValueError("Illegal character '%s'" % t.value[0])


def create_lexer(definition=None, debug=False):
    if definition is None:
        definition = LexerDefinition()
    lexer = ply.lex.lex(module=definition, debug=debug)
    return lexer
