import random

import ply.yacc

from jmespath import ast
from jmespath import lexer


class Parser(object):
    precedence = (
        ('left', 'DOT', 'LBRACKET'),
    )
    _cache = {}
    _max_size = 64

    def __init__(self, lexer_definition=None, debug=False):
        if lexer_definition is None:
            lexer_definition = lexer.LexerDefinition
        self._lexer_definition = lexer_definition
        self.tokens = self._lexer_definition.tokens
        self._debug = debug

    def parse(self, expression):
        cached = self._cache.get(expression)
        if cached is not None:
            return cached
        lexer = ply.lex.lex(module=self._lexer_definition(),
                            debug=self._debug)
        parser = ply.yacc.yacc(module=self, debug=self._debug,
                               write_tables=False)
        parsed = parser.parse(input=expression, lexer=lexer)
        self._cache[expression] = parsed
        if len(self._cache) > self._max_size:
            self._free_cache_entries()
        return parsed

    def _free_cache_entries(self):
        for key in random.sample(self._cache.keys(), self._max_size / 2):
            del self._cache[key]

    def p_jmespath_expression(self, p):
        """ expression : expression DOT expression"""
        p[0] = ast.SubExpression(p[1], p[3])

    def p_jmespath_index(self, p):
        """expression : expression LBRACKET NUMBER RBRACKET
                     | expression LBRACKET STAR RBRACKET
        """
        if p[3] == '*':
            p[0] = ast.SubExpression(p[1], ast.WildcardIndex())
        else:
            p[0] = ast.SubExpression(p[1], ast.Index(p[3]))

    def p_jmespath_wildcard(self, p):
        """expression : expression DOT STAR"""
        p[0] = ast.SubExpression(p[1], ast.Wildcard())

    def p_jmespath_identifier(self, p):
        """expression : IDENTIFIER
                      | NUMBER
        """
        p[0] = ast.Field(str(p[1]))

    def p_error(self, t):
        raise ValueError(
            'Parse error at column %s near token %s (%s)' % (
                t.lexpos, t.value, t.type))

    @classmethod
    def purge(cls):
        cls._cache.clear()
