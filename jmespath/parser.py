import random

import ply.yacc
import ply.lex

from jmespath import ast
from jmespath import lexer


class Grammar(object):
    precedence = (
        ('right', 'DOT', 'LBRACKET'),
    )

    def p_jmespath_subexpression(self, p):
        """ expression : expression DOT expression
                       | STAR
        """
        if len(p) == 2:
            # Then this is the STAR rule.
            p[0] = ast.WildcardValues()
        else:
            # This is the expression DOT expression rule.
            p[0] = ast.SubExpression(p[1], p[3])

    def p_jmespath_index(self, p):
        """expression : expression bracket-spec
                      | bracket-spec
        """
        if len(p) == 3:
            p[0] = ast.SubExpression(p[1], p[2])
        elif len(p) == 2:
            # Otherwise this is just a bracket-spec, which is valid as a root
            # level node (e.g. [2]) so we just assign the root node to the
            # bracket-spec.
            p[0] = p[1]

    def p_jmespath_bracket_specifier(self, p):
        """bracket-spec : LBRACKET STAR RBRACKET
                        | LBRACKET NUMBER RBRACKET
        """
        if p[2] == '*':
            p[0] = ast.WildcardIndex()
        else:
            p[0] = ast.Index(p[2])

    def p_jmespath_identifier(self, p):
        """expression : IDENTIFIER
                      | NUMBER
        """
        p[0] = ast.Field(str(p[1]))

    def p_jmespath_or_expression(self, p):
        """expression : expression OR expression"""
        p[0] = ast.ORExpression(p[1], p[3])

    def p_error(self, t):
        raise ValueError(
            'Parse error at column %s near token %s (%s)' % (
                t.lexpos, t.value, t.type))


class Parser(object):
    # The _max_size most recent expressions are cached in
    # _cache dict.
    _cache = {}
    _max_size = 64

    def __init__(self, lexer_definition=None, grammar=None,
                 debug=False):
        if lexer_definition is None:
            lexer_definition = lexer.LexerDefinition
        if grammar is None:
            grammar = Grammar
        self._lexer_definition = lexer_definition
        self._grammar = grammar
        self.tokens = self._lexer_definition.tokens
        self._debug = debug

    def parse(self, expression):
        cached = self._cache.get(expression)
        if cached is not None:
            return cached
        lexer = ply.lex.lex(module=self._lexer_definition(),
                            debug=self._debug,
                            reflags=self._lexer_definition.reflags)
        grammar = self._grammar()
        grammar.tokens = self._lexer_definition.tokens
        parser = ply.yacc.yacc(module=grammar, debug=self._debug,
                               write_tables=False)
        parsed = parser.parse(input=expression, lexer=lexer)
        self._cache[expression] = parsed
        if len(self._cache) > self._max_size:
            self._free_cache_entries()
        return parsed

    def _free_cache_entries(self):
        # This logic is borrowed from the new regex library which
        # uses similar eviction strategies.
        for key in random.sample(self._cache.keys(), int(self._max_size / 2)):
            del self._cache[key]

    @classmethod
    def purge(cls):
        """Clear the expression compilation cache."""
        cls._cache.clear()
