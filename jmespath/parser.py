import random

import ply.yacc
import ply.lex

from jmespath import ast
from jmespath import lexer
from jmespath.compat import with_str_method
from jmespath.compat import with_repr_method
from jmespath.compat import LR_TABLE


@with_str_method
class ParseError(ValueError):
    _ERROR_MESSAGE = 'Invalid jmespath expression'
    def __init__(self, lex_position, token_value, token_type,
                 msg=_ERROR_MESSAGE):
        super(ParseError, self).__init__(lex_position, token_value, token_type)
        self.lex_position = lex_position
        self.token_value = token_value
        self.token_type = token_type
        self.msg = msg
        # Whatever catches the ParseError can fill in the full expression
        self.expression = None

    def __str__(self):
        # self.lex_position +1 to account for the starting double quote char.
        underline = ' ' * (self.lex_position + 1) + '^'
        return (
            '%s: Parse error at column %s near '
            'token "%s" (%s) for expression:\n"%s"\n%s' % (
                self.msg, self.lex_position, self.token_value, self.token_type,
                self.expression, underline))


@with_str_method
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


@with_str_method
class ArityError(ParseError):
    def __init__(self, function_node):
        self.expected_arity = function_node.arity
        self.actual_arity = len(function_node.args)
        self.function_name = function_node.name
        self.expression = None

    def __str__(self):
        return ("Expected %s arguments for function %s, "
                "received %s" % (self.expected_arity,
                                 self.function_name,
                                 self.actual_arity))

@with_str_method
class VariadictArityError(ArityError):
    def __str__(self):
        return ("Expected at least %s arguments for function %s, "
                "received %s" % (self.expected_arity,
                                 self.function_name,
                                 self.actual_arity))


class Grammar(object):
    precedence = (
        ('left', 'OR'),
        ('right', 'DOT', 'STAR'),
        ('left', 'LT', 'LTE', 'GT', 'GTE', 'EQ'),
        ('right', 'LBRACKET', 'RBRACKET'),
    )

    def p_jmespath_subexpression(self, p):
        """expression : expression DOT multi-select-list
                      | expression DOT multi-select-hash
                      | STAR
        """
        if len(p) == 2:
            # Then this is the STAR rule.
            p[0] = ast.WildcardValues()
        else:
            # This is the expression DOT expression rule.
            p[0] = ast.SubExpression(p[1], p[3])

    def p_jmespath_subexpression_identifier(self, p):
        """expression : expression DOT identifier
        """
        p[0] = ast.SubExpression(p[1], ast.Field(p[3]))

    def p_jmespath_subexpression_wildcard(self, p):
        """expression : expression DOT STAR
        """
        p[0] = ast.SubExpression(p[1], ast.WildcardValues())

    def p_jmespath_subexpression_function(self, p):
        """expression : expression DOT function-expression
        """
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

    def p_jmespath_bracket_specifier_filter(self, p):
        """bracket-spec : FILTER filter-expression RBRACKET
        """
        p[0] = ast.FilterExpression(p[2])

    def p_jmespath_filter_expression(self, p):
        """filter-expression : expression comparator expression
        """
        # p[2] is a class object (from p_jmespath_comparator), so we
        # instantiate with the the left hand expression and the right hand
        # expression (p[1] and p[3] respectively).
        p[0] = p[2](p[1], p[3])

    def p_jmespath_comparator(self, p):
        """comparator : LT
                      | LTE
                      | GT
                      | GTE
                      | EQ
                      | NE
        """
        op_map = {
            '<': ast.OPLessThan,
            '<=': ast.OPLessThanEquals,
            '==': ast.OPEquals,
            '>': ast.OPGreaterThan,
            '>=': ast.OPGreaterThanEquals,
            '!=': ast.OPNotEquals,
        }
        p[0] = op_map[p[1]]

    def p_jmespath_identifier_expr(self, p):
        """expression : identifier"""
        p[0] = ast.Field(p[1])

    def p_jmespath_identifier(self, p):
        """identifier : UNQUOTED_IDENTIFIER
                      | QUOTED_IDENTIFIER
        """
        p[0] = p[1]

    def p_jmespath_multiselect_expressions(self, p):
        """expression : multi-select-hash
                      | multi-select-list
        """
        p[0] = p[1]

    def p_jmespath_multiselect(self, p):
        """multi-select-hash : LBRACE keyval-exprs RBRACE
        """
        p[0] = ast.MultiFieldDict(p[2])

    def p_jmespath_multiselect_list(self, p):
        """multi-select-list : LBRACKET expressions RBRACKET
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
        """keyval-expr : identifier COLON expression
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

    def p_jmespath_literal_expression(self, p):
        """expression : LITERAL"""
        p[0] = ast.Literal(p[1])

    def p_jmespath_function(self, p):
        """expression : function-expression"""
        p[0] = p[1]

    def p_jmespath_function_expression(self, p):
        """function-expression : UNQUOTED_IDENTIFIER LPAREN function-args RPAREN
                               | UNQUOTED_IDENTIFIER LPAREN RPAREN
        """
        if len(p) == 5:
            args = p[3]
        else:
            args = []
        function_node = ast.FunctionExpression(p[1], args)
        if function_node.variadic:
            if len(function_node.args) < function_node.arity:
                raise VariadictArityError(function_node)
        elif function_node.arity != len(function_node.args):
            raise ArityError(function_node)
        p[0] = function_node

    def p_jmespath_function_args(self, p):
        """function-args : function-args COMMA function-arg
                         | function-arg
        """
        if len(p) == 2:
            p[0] = [p[1]]
        elif len(p) == 4:
            p[1].append(p[3])
            p[0] = p[1]

    def p_jmespath_function_arg(self, p):
        """function-arg : expression
                        | CURRENT
                        | EXPREF expression
        """
        if len(p) == 3:
            p[0] = ast.ExpressionReference(p[2])
        elif p[1] == '@':
            p[0] = ast.CurrentNode()
        else:
            p[0] = p[1]

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
    _table_module = LR_TABLE

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
                               tabmodule=self._table_module,
                               write_tables=False)
        parsed = self._parse_expression(parser=parser, expression=expression,
                                        lexer_obj=lexer)
        parsed_result = ParsedResult(expression, parsed)
        self._cache[expression] = parsed_result
        if len(self._cache) > self._max_size:
            self._free_cache_entries()
        return parsed_result

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


@with_repr_method
class ParsedResult(object):
    def __init__(self, expression, parsed):
        self.expression = expression
        self.parsed = parsed

    def search(self, value):
        return self.parsed.search(value)

    def pretty_print(self, indent=''):
        return self.parsed.pretty_print(indent=indent)

    def __repr__(self):
        return repr(self.parsed)

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

