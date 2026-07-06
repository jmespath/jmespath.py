"""Top down operator precedence parser.

This is an implementation of Vaughan R. Pratt's
"Top Down Operator Precedence" parser.
(http://dl.acm.org/citation.cfm?doid=512927.512931).

These are some additional resources that help explain the
general idea behind a Pratt parser:

* http://effbot.org/zone/simple-top-down-parsing.htm
* http://javascript.crockford.com/tdop/tdop.html

A few notes on the implementation.

* All the nud/led tokens are on the Parser class itself, and are dispatched
  using getattr().  This keeps all the parsing logic contained to a single
  class.
* We use two passes through the data.  One to create a list of token,
  then one pass through the tokens to create the AST.  While the lexer actually
  yields tokens, we convert it to a list so we can easily implement two tokens
  of lookahead.  A previous implementation used a fixed circular buffer, but it
  was significantly slower.  Also, the average jmespath expression typically
  does not have a large amount of token so this is not an issue.  And
  interestingly enough, creating a token list first is actually faster than
  consuming from the token iterator one token at a time.

"""
from jmespath import lexer
from jmespath.compat import with_repr_method
from jmespath import ast
from jmespath import exceptions
from jmespath import visitor


class Parser(object):
    BINDING_POWER = {
        'eof': 0,
        'unquoted_identifier': 0,
        'quoted_identifier': 0,
        'literal': 0,
        'rbracket': 0,
        'rparen': 0,
        'comma': 0,
        'rbrace': 0,
        'number': 0,
        'current': 0,
        'expref': 0,
        'colon': 0,
        'pipe': 1,
        'or': 2,
        'and': 3,
        'eq': 5,
        'gt': 5,
        'lt': 5,
        'gte': 5,
        'lte': 5,
        'ne': 5,
        'flatten': 9,
        # Everything above stops a projection.
        'star': 20,
        'filter': 21,
        'dot': 40,
        'not': 45,
        'lbrace': 50,
        'lbracket': 55,
        'lparen': 60,
    }
    # The maximum binding power for a token that can stop
    # a projection.
    _PROJECTION_STOP = 10
    # The _MAX_SIZE most recent expressions are cached in
    # _CACHE dict.
    _CACHE = {}
    _MAX_SIZE = 512
    # Per-class nud/led dispatch tables ({token_type: function}),
    # built once per class on first instantiation.  Keyed by class so
    # subclasses overriding or adding token handlers work correctly.
    _DISPATCH_CACHE = {}

    def __init__(self, lookahead=2):
        self.tokenizer = None
        self._tokens = [None] * lookahead
        self._buffer_size = lookahead
        self._index = 0
        cls = type(self)
        dispatch = Parser._DISPATCH_CACHE.get(cls)
        if dispatch is None:
            nud = {}
            led = {}
            for name in dir(cls):
                if name.startswith('_token_nud_'):
                    nud[name[11:]] = getattr(cls, name)
                elif name.startswith('_token_led_'):
                    led[name[11:]] = getattr(cls, name)
            dispatch = (nud, led)
            Parser._DISPATCH_CACHE[cls] = dispatch
        self._NUD_DISPATCH, self._LED_DISPATCH = dispatch

    def parse(self, expression):
        # .get() rather than try/except KeyError: a raised exception
        # costs far more than the parse-cache lookup itself.
        parsed_result = self._CACHE.get(expression)
        if parsed_result is not None:
            return parsed_result
        parsed_result = self._do_parse(expression)
        if len(self._CACHE) >= self._MAX_SIZE:
            try:
                del self._CACHE[next(iter(self._CACHE))]
            except (KeyError, StopIteration, RuntimeError):
                # KeyError - Another thread else already deleted the key.
                # RuntimeError - Another modified the cache.
                # StopIteration - (Unlikely) Cache is empty.
                #
                # If we encounter an error we should NOT be adding to the
                # cache.  To ensure we do not exceed self._MAX_SIZE, we
                # can only add to the cache if we successfully removed
                # an element from the cache, otherwise this can grow
                # unbounded.
                return parsed_result
        self._CACHE[expression] = parsed_result
        return parsed_result

    def _do_parse(self, expression):
        try:
            return self._parse(expression)
        except exceptions.LexerError as e:
            e.expression = expression
            raise
        except exceptions.IncompleteExpressionError as e:
            e.set_expression(expression)
            raise
        except exceptions.ParseError as e:
            e.expression = expression
            raise

    def _parse(self, expression):
        self.tokenizer = None
        # The lexer returns a fully materialized token list, which we
        # can use directly for our two tokens of lookahead.
        self._tokens = lexer.Lexer().tokenize(expression)
        self._index = 0
        parsed = self._expression(binding_power=0)
        if not self._current_token() == 'eof':
            t = self._lookahead_token(0)
            raise exceptions.ParseError(t['start'], t['value'], t['type'],
                                        "Unexpected token: %s" % t['value'])
        return ParsedResult(expression, parsed)

    def _expression(self, binding_power=0):
        # This is the hot path of the parser, so the token stream
        # accesses (self._lookahead_token/_advance/_current_token) are
        # inlined and the nud/led handlers are resolved through the
        # precomputed dispatch tables built at the bottom of this
        # module rather than per-token getattr calls.
        tokens = self._tokens
        index = self._index
        left_token = tokens[index]
        self._index = index + 1
        nud_function = self._NUD_DISPATCH.get(left_token['type'])
        if nud_function is None:
            # No nud handler exists for this token type, so it cannot
            # start an expression.  The error handler is resolved on the
            # concrete class so a subclass override is honored.
            nud_function = type(self)._error_nud_token
        left = nud_function(self, left_token)
        binding_power_table = self.BINDING_POWER
        led_dispatch = self._LED_DISPATCH
        current_token = tokens[self._index]['type']
        while binding_power < binding_power_table[current_token]:
            led = led_dispatch.get(current_token)
            if led is None:
                # No led handler for a token the binding power let us
                # enter on: it can't continue an expression.
                self._error_led_token(tokens[self._index])
            else:
                self._index += 1
                left = led(self, left)
                current_token = tokens[self._index]['type']
        return left

    # The ast.* factory calls are inlined as dict literals in the
    # token handlers below: at a few hundred thousand nodes per
    # second the function call per node is a measurable share of the
    # parse time.

    def _token_nud_literal(self, token):
        return {'type': 'literal', 'value': token['value'], 'children': []}

    def _token_nud_unquoted_identifier(self, token):
        return {'type': 'field', 'children': [], 'value': token['value']}

    def _token_nud_quoted_identifier(self, token):
        field = {'type': 'field', 'children': [], 'value': token['value']}
        # You can't have a quoted identifier as a function
        # name.
        if self._tokens[self._index]['type'] == 'lparen':
            t = self._tokens[self._index]
            raise exceptions.ParseError(
                0, t['value'], t['type'],
                'Quoted identifier not allowed for function names.')
        return field

    def _token_nud_star(self, token):
        left = {'type': 'identity', 'children': []}
        if self._tokens[self._index]['type'] == 'rbracket':
            right = {'type': 'identity', 'children': []}
        else:
            right = self._parse_projection_rhs(self.BINDING_POWER['star'])
        return {'type': 'value_projection', 'children': [left, right]}

    def _token_nud_filter(self, token):
        return self._token_led_filter({'type': 'identity', 'children': []})

    def _token_nud_lbrace(self, token):
        return self._parse_multi_select_hash()

    def _token_nud_lparen(self, token):
        expression = self._expression()
        self._match('rparen')
        return expression

    def _token_nud_flatten(self, token):
        left = {'type': 'flatten',
                'children': [{'type': 'identity', 'children': []}]}
        right = self._parse_projection_rhs(
            self.BINDING_POWER['flatten'])
        return {'type': 'projection', 'children': [left, right]}

    def _token_nud_not(self, token):
        expr = self._expression(self.BINDING_POWER['not'])
        return {'type': 'not_expression', 'children': [expr]}

    def _token_nud_lbracket(self, token):
        current_token = self._tokens[self._index]['type']
        if current_token in ('number', 'colon'):
            right = self._parse_index_expression()
            # We could optimize this and remove the identity() node.
            # We don't really need an index_expression node, we can
            # just use emit an index node here if we're not dealing
            # with a slice.
            return self._project_if_slice(
                {'type': 'identity', 'children': []}, right)
        elif current_token == 'star' and \
                self._tokens[self._index + 1]['type'] == 'rbracket':
            self._index += 2
            right = self._parse_projection_rhs(self.BINDING_POWER['star'])
            return {'type': 'projection',
                    'children': [{'type': 'identity', 'children': []},
                                 right]}
        else:
            return self._parse_multi_select_list()

    def _parse_index_expression(self):
        # We're here:
        # [<current>
        #  ^
        #  | current token
        if (self._tokens[self._index]['type'] == 'colon' or
                self._tokens[self._index + 1]['type'] == 'colon'):
            return self._parse_slice_expression()
        else:
            # Parse the syntax [number]
            node = {'type': 'index', 'children': [],
                    'value': self._tokens[self._index]['value']}
            self._index += 1
            self._match('rbracket')
            return node

    def _parse_slice_expression(self):
        # [start:end:step]
        # Where start, end, and step are optional.
        # The last colon is optional as well.
        parts = [None, None, None]
        index = 0
        current_token = self._current_token()
        while not current_token == 'rbracket' and index < 3:
            if current_token == 'colon':
                index += 1
                if index == 3:
                    self._raise_parse_error_for_token(
                        self._lookahead_token(0), 'syntax error')
                self._advance()
            elif current_token == 'number':
                parts[index] = self._lookahead_token(0)['value']
                self._advance()
            else:
                self._raise_parse_error_for_token(
                    self._lookahead_token(0), 'syntax error')
            current_token = self._current_token()
        self._match('rbracket')
        return ast.slice(*parts)

    def _token_nud_current(self, token):
        return {'type': 'current', 'children': []}

    def _token_nud_expref(self, token):
        expression = self._expression(self.BINDING_POWER['expref'])
        return {'type': 'expref', 'children': [expression]}

    def _token_led_dot(self, left):
        if not self._tokens[self._index]['type'] == 'star':
            right = self._parse_dot_rhs(self.BINDING_POWER['dot'])
            if left['type'] == 'subexpression':
                left['children'].append(right)
                return left
            else:
                return {'type': 'subexpression', 'children': [left, right]}
        else:
            # We're creating a projection.
            self._index += 1
            right = self._parse_projection_rhs(
                self.BINDING_POWER['dot'])
            return {'type': 'value_projection', 'children': [left, right]}

    def _token_led_pipe(self, left):
        right = self._expression(self.BINDING_POWER['pipe'])
        return {'type': 'pipe', 'children': [left, right]}

    def _token_led_or(self, left):
        right = self._expression(self.BINDING_POWER['or'])
        return {'type': 'or_expression', 'children': [left, right]}

    def _token_led_and(self, left):
        right = self._expression(self.BINDING_POWER['and'])
        return {'type': 'and_expression', 'children': [left, right]}

    def _token_led_lparen(self, left):
        if left['type'] != 'field':
            #  0 - first func arg or closing paren.
            # -1 - '(' token
            # -2 - invalid function "name".
            prev_t = self._lookahead_token(-2)
            raise exceptions.ParseError(
                prev_t['start'], prev_t['value'], prev_t['type'],
                "Invalid function name '%s'" % prev_t['value'])
        name = left['value']
        args = []
        tokens = self._tokens
        while not tokens[self._index]['type'] == 'rparen':
            expression = self._expression()
            if tokens[self._index]['type'] == 'comma':
                self._index += 1
            args.append(expression)
        self._match('rparen')
        return {'type': 'function_expression', 'children': args,
                'value': name}

    def _token_led_filter(self, left):
        # Filters are projections.
        condition = self._expression(0)
        self._match('rbracket')
        if self._tokens[self._index]['type'] == 'flatten':
            right = {'type': 'identity', 'children': []}
        else:
            right = self._parse_projection_rhs(self.BINDING_POWER['filter'])
        return {'type': 'filter_projection',
                'children': [left, right, condition]}

    def _token_led_eq(self, left):
        return self._parse_comparator(left, 'eq')

    def _token_led_ne(self, left):
        return self._parse_comparator(left, 'ne')

    def _token_led_gt(self, left):
        return self._parse_comparator(left, 'gt')

    def _token_led_gte(self, left):
        return self._parse_comparator(left, 'gte')

    def _token_led_lt(self, left):
        return self._parse_comparator(left, 'lt')

    def _token_led_lte(self, left):
        return self._parse_comparator(left, 'lte')

    def _token_led_flatten(self, left):
        left = {'type': 'flatten', 'children': [left]}
        right = self._parse_projection_rhs(
            self.BINDING_POWER['flatten'])
        return {'type': 'projection', 'children': [left, right]}

    def _token_led_lbracket(self, left):
        token = self._tokens[self._index]
        if token['type'] in ('number', 'colon'):
            right = self._parse_index_expression()
            if left['type'] == 'index_expression':
                # Optimization: if the left node is an index expr,
                # we can avoid creating another node and instead just add
                # the right node as a child of the left.
                left['children'].append(right)
                return left
            else:
                return self._project_if_slice(left, right)
        else:
            # We have a projection
            self._match('star')
            self._match('rbracket')
            right = self._parse_projection_rhs(self.BINDING_POWER['star'])
            return {'type': 'projection', 'children': [left, right]}

    def _project_if_slice(self, left, right):
        index_expr = {'type': 'index_expression', 'children': [left, right]}
        if right['type'] == 'slice':
            return {'type': 'projection',
                    'children': [
                        index_expr,
                        self._parse_projection_rhs(
                            self.BINDING_POWER['star'])]}
        else:
            return index_expr

    def _parse_comparator(self, left, comparator):
        right = self._expression(self.BINDING_POWER[comparator])
        return {'type': 'comparator', 'children': [left, right],
                'value': comparator}

    def _parse_multi_select_list(self):
        expressions = []
        tokens = self._tokens
        while True:
            expression = self._expression()
            expressions.append(expression)
            if tokens[self._index]['type'] == 'rbracket':
                break
            else:
                self._match('comma')
        self._match('rbracket')
        return {'type': 'multi_select_list', 'children': expressions}

    def _parse_multi_select_hash(self):
        pairs = []
        tokens = self._tokens
        while True:
            key_token = tokens[self._index]
            # Before getting the token value, verify it's
            # an identifier.
            self._match_multiple_tokens(
                token_types=['quoted_identifier', 'unquoted_identifier'])
            key_name = key_token['value']
            self._match('colon')
            value = self._expression(0)
            node = {'type': 'key_val_pair', 'children': [value],
                    'value': key_name}
            pairs.append(node)
            if tokens[self._index]['type'] == 'comma':
                self._index += 1
            elif tokens[self._index]['type'] == 'rbrace':
                self._index += 1
                break
        return {'type': 'multi_select_dict', 'children': pairs}

    def _parse_projection_rhs(self, binding_power):
        # Parse the right hand side of the projection.
        current_token = self._tokens[self._index]['type']
        if self.BINDING_POWER[current_token] < self._PROJECTION_STOP:
            # BP of 10 are all the tokens that stop a projection.
            right = {'type': 'identity', 'children': []}
        elif current_token == 'lbracket':
            right = self._expression(binding_power)
        elif current_token == 'filter':
            right = self._expression(binding_power)
        elif current_token == 'dot':
            # inline'd self._match('dot'): the type was just checked.
            self._index += 1
            right = self._parse_dot_rhs(binding_power)
        else:
            self._raise_parse_error_for_token(self._tokens[self._index],
                                              'syntax error')
        return right

    def _parse_dot_rhs(self, binding_power):
        # From the grammar:
        # expression '.' ( identifier /
        #                  multi-select-list /
        #                  multi-select-hash /
        #                  function-expression /
        #                  *
        # In terms of tokens that means that after a '.',
        # you can have:
        lookahead = self._tokens[self._index]['type']
        # Common case "foo.bar", so first check for an identifier.
        if lookahead in ('quoted_identifier', 'unquoted_identifier', 'star'):
            return self._expression(binding_power)
        elif lookahead == 'lbracket':
            self._index += 1
            return self._parse_multi_select_list()
        elif lookahead == 'lbrace':
            self._index += 1
            return self._parse_multi_select_hash()
        else:
            t = self._tokens[self._index]
            allowed = ['quoted_identifier', 'unquoted_identifier',
                       'lbracket', 'lbrace']
            msg = (
                "Expecting: %s, got: %s" % (allowed, t['type'])
            )
            self._raise_parse_error_for_token(t, msg)

    def _error_nud_token(self, token):
        if token['type'] == 'eof':
            raise exceptions.IncompleteExpressionError(
                token['start'], token['value'], token['type'])
        self._raise_parse_error_for_token(token, 'invalid token')

    def _error_led_token(self, token):
        self._raise_parse_error_for_token(token, 'invalid token')

    def _match(self, token_type=None):
        # inline'd self._current_token() and self._advance()
        if self._tokens[self._index]['type'] == token_type:
            self._index += 1
        else:
            self._raise_parse_error_maybe_eof(
                token_type, self._tokens[self._index])

    def _match_multiple_tokens(self, token_types):
        if self._tokens[self._index]['type'] not in token_types:
            self._raise_parse_error_maybe_eof(
                token_types, self._tokens[self._index])
        self._index += 1

    def _advance(self):
        self._index += 1

    def _current_token(self):
        return self._tokens[self._index]['type']

    def _lookahead(self, number):
        return self._tokens[self._index + number]['type']

    def _lookahead_token(self, number):
        return self._tokens[self._index + number]

    def _raise_parse_error_for_token(self, token, reason):
        lex_position = token['start']
        actual_value = token['value']
        actual_type = token['type']
        raise exceptions.ParseError(lex_position, actual_value,
                                    actual_type, reason)

    def _raise_parse_error_maybe_eof(self, expected_type, token):
        lex_position = token['start']
        actual_value = token['value']
        actual_type = token['type']
        if actual_type == 'eof':
            raise exceptions.IncompleteExpressionError(
                lex_position, actual_value, actual_type)
        message = 'Expecting: %s, got: %s' % (expected_type,
                                              actual_type)
        raise exceptions.ParseError(
            lex_position, actual_value, actual_type, message)

    @classmethod
    def purge(cls):
        """Clear the expression compilation cache."""
        cls._CACHE.clear()


@with_repr_method
class ParsedResult(object):
    def __init__(self, expression, parsed):
        self.expression = expression
        self.parsed = parsed

    def search(self, value, options=None):
        if options is None:
            # A TreeInterpreter with default options is stateless
            # across searches, so a shared instance is used rather
            # than constructing an interpreter (and its Options and
            # Functions instances) on every search.  Its method cache
            # is fully pre-populated (see below) so concurrent default
            # searches only read from it -- no mutation, hence safe on
            # free-threaded builds.
            interpreter = _DEFAULT_INTERPRETER
        else:
            interpreter = visitor.TreeInterpreter(options)
        result = interpreter.visit(self.parsed, value)
        return result

    def _render_dot_file(self):
        """Render the parsed AST as a dot file.

        Note that this is marked as an internal method because
        the AST is an implementation detail and is subject
        to change.  This method can be used to help troubleshoot
        or for development purposes, but is not considered part
        of the public supported API.  Use at your own risk.

        """
        renderer = visitor.GraphvizVisitor()
        contents = renderer.visit(self.parsed)
        return contents

    def __repr__(self):
        return repr(self.parsed)


_DEFAULT_INTERPRETER = visitor.TreeInterpreter()


def _prewarm_default_interpreter():
    # Resolve every visit_* handler up front so the shared interpreter's
    # method cache is fully populated at import time and never written
    # to during a search.  A read-only cache lets concurrent default
    # searches share the interpreter safely, including on free-threaded
    # (no-GIL) CPython builds.
    for name in dir(visitor.TreeInterpreter):
        if name.startswith('visit_'):
            _DEFAULT_INTERPRETER._resolve_method(name[len('visit_'):])


_prewarm_default_interpreter()
