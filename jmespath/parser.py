import random

import ply.yacc
import ply.lex

from jmespath import ast
from jmespath import lexer
from jmespath.compat import with_str_method


@with_str_method
class ParseError(ValueError):
    def __init__(self, lex_position, token_value, token_type):
        super(ParseError, self).__init__(lex_position, token_value, token_type)
        self.lex_position = lex_position
        self.token_value = token_value
        self.token_type = token_type
        # Whatever catches the ParseError can fill in the full expression
        self.expression = None

    def __str__(self):
        # self.lex_position +1 to account for the starting double quote char.
        underline = ' ' * (self.lex_position + 1) + '^'
        return (
            'Invalid jmespath expression: Parse error at column %s near '
            'token "%s" (%s) for expression:\n"%s"\n%s' % (
                self.lex_position, self.token_value, self.token_type,
                self.expression, underline))


class IncompleteExpressionError(ParseError):
    def set_expression(self, expression):
        self.expression = expression
        self.lex_position = len(expression)
        self.token_type = None
        self.token_value = None

    def __str__(self):
        # self.lex_position +1 to account for the starting double quote char.
        underline = ' ' * (self.lex_position + 1) + '^'
        return (
            'Invalid jmespath expression: Incomplete expression:\n'
            '"%s"\n%s' % (self.expression, underline))



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
                        | LBRACKET RBRACKET
        """
        if len(p) == 3:
            p[0] = ast.ListElements()
        elif p[2] == '*':
            p[0] = ast.WildcardIndex()
        else:
            p[0] = ast.Index(p[2])

    def p_jmespath_identifier(self, p):
        """expression : IDENTIFIER
                      | NUMBER
        """
        p[0] = ast.Field(p[1])

    def p_jmespath_multiselect(self, p):
        """expression : LBRACE keyval-exprs RBRACE
        """
        p[0] = ast.MultiFieldDict(p[2])

    def p_jmespath_multiselect_list(self, p):
        """expression : LBRACKET expressions RBRACKET
        """
        p[0] = ast.MultiFieldList(p[2])

    def p_jmespath_keyval_exprs(self, p):
        """keyval-exprs : keyval-exprs COMMA keyval-expr
                        | keyval-expr
        """
        if len(p) == 2:
            p[0] = [p[1]]
        elif len(p) == 4:
            p[1].append(p[3])
            p[0] = p[1]

    def p_jmespath_keyval_expr(self, p):
        """keyval-expr : IDENTIFIER COLON expression
        """
        p[0] = ast.KeyValPair(p[1], p[3])

    def p_jmespath_multiple_expressions(self, p):
        """expressions : expressions COMMA expression
                       | expression
        """
        if len(p) == 2:
            p[0] = [p[1]]
        elif len(p) == 4:
            p[1].append(p[3])
            p[0] = p[1]

    def p_jmespath_or_expression(self, p):
        """expression : expression OR expression"""
        p[0] = ast.ORExpression(p[1], p[3])

    def p_error(self, t):
        if t is not None:
            raise ParseError(t.lexpos, t.value, t.type)
        else:
            raise IncompleteExpressionError(None, None, None)


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
        parsed = self._parse_expression(parser=parser, expression=expression,
                                        lexer_obj=lexer)
        self._cache[expression] = parsed
        if len(self._cache) > self._max_size:
            self._free_cache_entries()
        return parsed

    def _parse_expression(self, parser, expression, lexer_obj):
        try:
            parsed = parser.parse(input=expression, lexer=lexer_obj)
            return parsed
        except lexer.LexerError as e:
            e.expression = expression
            raise e
        except IncompleteExpressionError as e:
            e.set_expression(expression)
            raise e
        except ParseError as e:
            e.expression = expression
            raise e

    def _free_cache_entries(self):
        # This logic is borrowed from the new regex library which
        # uses similar eviction strategies.
        for key in random.sample(self._cache.keys(), int(self._max_size / 2)):
            del self._cache[key]

    @classmethod
    def purge(cls):
        """Clear the expression compilation cache."""
        cls._cache.clear()
