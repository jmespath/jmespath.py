import operator
import math
import json

from jmespath.compat import with_repr_method
from jmespath.compat import string_type as STRING_TYPE
from jmespath.compat import zip_longest
from jmespath.exceptions import JMESPathTypeError, UnknownFunctionError


NUMBER_TYPE = (float, int)
_VARIADIC = object()


# python types -> jmespath types
TYPES_MAP = {
    'bool': 'boolean',
    'list': 'array',
    'dict': 'object',
    'NoneType': 'null',
    'unicode': 'string',
    'str': 'string',
    'float': 'number',
    'int': 'number',
    'OrderedDict': 'object',
    '_Projection': 'array',
    '_Expression': 'expref',
}


# jmespath types -> python types
REVERSE_TYPES_MAP = {
    'boolean': ('bool',),
    'array': ('list', '_Projection'),
    'object': ('dict', 'OrderedDict',),
    'null': ('None',),
    'string': ('unicode', 'str'),
    'number': ('float', 'int'),
    'expref': ('_Expression',),
}


class _Arg(object):
    __slots__ = ('types',)

    def __init__(self, types=None):
        self.types = types


@with_repr_method
class AST(object):

    def __init__(self):
        self.children = []

    def search(self, value):
        pass

    def pretty_print(self, indent=''):
        return super(AST, self).__repr__()

    def __repr__(self):
        return self.pretty_print()


class Identity(AST):
    def search(self, value):
        return value

    def pretty_print(self, indent=''):
        return "%sIdentity()" % indent


class SubExpression(AST):
    """Represents a subexpression match.

    A subexpression match has a parent and a child node.  A simple example
    would be something like 'foo.bar' which is represented as::

        SubExpression(Field(foo), Field(bar))

    """
    def __init__(self, parent, child):
        self.children = [parent, child]

    def search(self, value):
        # To evaluate a subexpression we first evaluate the parent object
        # and then feed the match of the parent node into the child node.
        sub_value = self.children[0].search(value)
        found = self.children[1].search(sub_value)
        return found

    def pretty_print(self, indent=''):
        sub_indent = indent + ' ' * 4
        return "%s%s(\n%s%s,\n%s%s)" % (
            indent, self.__class__.__name__,
            sub_indent, self.children[0].pretty_print(sub_indent),
            sub_indent, self.children[1].pretty_print(sub_indent))


# This is used just to differentiate between
# subexpressions and indexexpressions (wildcards can hang
# off of an indexexpression).
class IndexExpression(SubExpression):
    pass


class Field(AST):

    def __init__(self, name):
        self.name = name
        self.children = []

    def pretty_print(self, indent=''):
        return "%sField(%s)" % (indent, self.name)

    def search(self, value):
        if value is not None:
            try:
                return value.get(self.name)
            except AttributeError:
                return None


class BaseMultiField(AST):
    def __init__(self, nodes):
        self.children = list(nodes)

    def search(self, value):
        if value is None:
            return None
        return self._multi_get(value)

    def _multi_get(self, value):
        # Subclasses must define this method.
        raise NotImplementedError("_multi_get")

    def pretty_print(self, indent=''):
        return "%s%s(%s)" % (indent, self.__class__.__name__, self.children)


class MultiFieldDict(BaseMultiField):

    def _multi_get(self, value):
        collected = {}
        for node in self.children:
            collected[node.key_name] = node.search(value)
        return collected


class MultiFieldList(BaseMultiField):

    def _multi_get(self, value):
        collected = []
        for node in self.children:
            collected.append(node.search(value))
        return collected


class KeyValPair(AST):
    def __init__(self, key_name, node):
        self.key_name = key_name
        self.children = [node]

    def search(self, value):
        return self.children[0].search(value)

    def pretty_print(self, indent=''):
        return "%sKeyValPair(key_name=%s, node=%s)" % (
            indent, self.key_name, self.children[0])


class Index(AST):

    def __init__(self, index):
        super(Index, self).__init__()
        self.index = index

    def pretty_print(self, indent=''):
        return "%sIndex(%s)" % (indent, self.index)

    def search(self, value):
        # Even though we can index strings, we don't
        # want to support that.
        if not isinstance(value, list):
            return None
        try:
            return value[self.index]
        except IndexError:
            return None


class ORExpression(AST):
    def __init__(self, first, remaining):
        self.children = [first, remaining]

    def search(self, value):
        matched = self.children[0].search(value)
        if self._is_false(matched):
            matched = self.children[1].search(value)
        return matched

    def _is_false(self, value):
        # This looks weird, but we're explicitly using equality checks
        # because the truth/false values are different between
        # python and jmespath.
        return (value == '' or value == [] or value == {} or value is None or
                value == False)

    def pretty_print(self, indent=''):
        return "%sORExpression(%s, %s)" % (indent, self.children[0],
                                           self.children[1])


class FilterExpression(AST):

    def __init__(self, expression):
        self.children = [expression]

    def search(self, value):
        if not isinstance(value, list):
            return None
        result = []
        for element in value:
            if self.children[0].search(element):
                result.append(element)
        return result

    def pretty_print(self, indent=''):
        return '%sFilterExpression(%s)' % (indent, self.children[0])


class Literal(AST):

    def __init__(self, literal_value):
        super(Literal, self).__init__()
        self.literal_value = literal_value

    def search(self, value):
        return self.literal_value

    def pretty_print(self, indent=''):
        return '%sLiteral(%s)' % (indent, self.literal_value)


class Comparator(AST):
    # Subclasses must define the operation function.
    operation = None

    def __init__(self, first, second):
        self.children = [first, second]

    def search(self, data):
        return self.operation(self.children[0].search(data),
                              self.children[1].search(data))

    def pretty_print(self, indent=''):
        return '%s%s(%s, %s)' % (indent, self.__class__.__name__,
                                 self.children[0], self.children[1])


class OPEquals(Comparator):
    def _equals(self, first, second):
        if self._is_special_integer_case(first, second):
            return False
        else:
            return first == second

    def _is_special_integer_case(self, first, second):
        # We need to special case comparing 0 or 1 to
        # True/False.  While normally comparing any
        # integer other than 0/1 to True/False will always
        # return False.  However 0/1 have this:
        # >>> 0 == True
        # False
        # >>> 0 == False
        # True
        # >>> 1 == True
        # True
        # >>> 1 == False
        # False
        #
        # Also need to consider that:
        # >>> 0 in [True, False]
        # True
        if first is 0 or first is 1:
            return second is True or second is False
        elif second is 0 or second is 1:
            return first is True or first is False

    operation = _equals


class OPNotEquals(OPEquals):
    def _not_equals(self, first, second):
        return not super(OPNotEquals, self)._equals(first, second)

    operation = _not_equals


class OPLessThan(Comparator):
    operation = operator.lt


class OPLessThanEquals(Comparator):
    operation = operator.le


class OPGreaterThan(Comparator):
    operation = operator.gt


class OPGreaterThanEquals(Comparator):
    operation = operator.ge


class CurrentNode(AST):
    def search(self, value):
        return value


class FunctionExpression(AST):

    def __init__(self, name, args):
        self.name = name
        # The .children attribute is to support homogeneous
        # children nodes, but .args is a better name for all the
        # code that uses the children, so we support both.
        self.children = args
        self.args = args
        try:
            self.function = getattr(self, '_func_%s' % name)
        except AttributeError:
            raise UnknownFunctionError("Unknown function: %s" % self.name)
        self.arity = self.function.arity
        self.variadic = self.function.variadic
        self.function = self._resolve_arguments_wrapper(self.function)

    def pretty_print(self, indent=''):
        return "%sFunctionExpression(name=%s, args=%s)" % (
            indent, self.name, self.args)

    def search(self, value):
        return self.function(value)

    def _resolve_arguments_wrapper(self, function):
        def _call_with_resolved_args(value):
            # Before calling the function, we have two things to do:
            # 1. Resolve the arguments (evaluate the arg expressions
            #    against the passed in input.
            # 2. Type check the arguments
            resolved_args = []
            for arg_expression, arg_spec in zip_longest(
                    self.args, function.argspec,
                    fillvalue=function.argspec[-1]):
                # 1. Resolve the arguments.
                current = arg_expression.search(value)
                # 2. Type check (provided we have type information).
                if arg_spec.types is not None:
                    _type_check(arg_spec.types, current)
                resolved_args.append(current)
            return function(*resolved_args)

        def _get_allowed_pytypes(types):
            allowed_types = []
            allowed_subtypes = []
            for t in types:
                type_ = t.split('-', 1)
                if len(type_) == 2:
                    type_, subtype = type_
                    allowed_subtypes.append(REVERSE_TYPES_MAP[subtype])
                else:
                    type_ = type_[0]
                allowed_types.extend(REVERSE_TYPES_MAP[type_])
            return allowed_types, allowed_subtypes

        def _type_check(types, current):
            # Type checking involves checking the top level type,
            # and in the case of arrays, potentially checking the types
            # of each element.
            allowed_types, allowed_subtypes = _get_allowed_pytypes(types)
            # We're not using isinstance() on purpose.
            # The type model for jmespath does not map
            # 1-1 with python types (booleans are considered
            # integers in python for example).
            actual_typename = type(current).__name__
            if actual_typename not in allowed_types:
                raise JMESPathTypeError(self.name, current,
                                        TYPES_MAP.get(actual_typename,
                                                      'unknown'),
                                        types)
            # If we're dealing with a list type, we can have
            # additional restrictions on the type of the list
            # elements (for example a function can require a
            # list of numbers or a list of strings).
            # Arrays are the only types that can have subtypes.
            if allowed_subtypes:
                _subtype_check(current, allowed_subtypes, types)

        def _subtype_check(current, allowed_subtypes, types):
            if len(allowed_subtypes) == 1:
                # The easy case, we know up front what type
                # we need to validate.
                allowed_subtypes = allowed_subtypes[0]
                for element in current:
                    actual_typename = type(element).__name__
                    if actual_typename not in allowed_subtypes:
                        raise JMESPathTypeError(self.name, element,
                                                actual_typename,
                                                types)
            elif len(allowed_subtypes) > 1 and current:
                # Dynamic type validation.  Based on the first
                # type we see, we validate that the remaining types
                # match.
                first = type(current[0]).__name__
                for subtypes in allowed_subtypes:
                    if first in subtypes:
                        allowed = subtypes
                        break
                else:
                    raise JMESPathTypeError(self.name, current[0],
                                            first, types)
                for element in current:
                    actual_typename = type(element).__name__
                    if actual_typename not in allowed:
                        raise JMESPathTypeError(self.name, element,
                                                actual_typename,
                                                types)

        return _call_with_resolved_args

    def signature(*arguments, **kwargs):
        def _record_arity(func):
            func.arity = len(arguments)
            func.variadic = kwargs.get('variadic', False)
            func.argspec = arguments
            return func
        return _record_arity

    @signature(_Arg(), variadic=True)
    def _func_not_null(self, *arguments):
        for argument in arguments:
            if argument is not None:
                return argument

    @signature(_Arg(types=['number']))
    def _func_abs(self, arg):
        return abs(arg)

    @signature(_Arg(types=['array-number']))
    def _func_avg(self, arg):
        return sum(arg) / float(len(arg))

    @signature(_Arg())
    def _func_to_string(self, arg):
        if isinstance(arg, STRING_TYPE):
            return arg
        else:
            return json.dumps(arg)

    @signature(_Arg())
    def _func_to_number(self, arg):
        if isinstance(arg, (list, dict, bool)):
            return None
        elif arg is None:
            return None
        elif isinstance(arg, (int, float)):
            return arg
        else:
            try:
                if '.' in arg:
                    return float(arg)
                else:
                    return int(arg)
            except ValueError:
                return None

    @signature(_Arg(types=['array', 'string']), _Arg())
    def _func_contains(self, subject, search):
        return search in subject

    @signature(_Arg(types=['string', 'array', 'object']))
    def _func_length(self, arg):
        return len(arg)

    @signature(_Arg(types=['number']))
    def _func_ceil(self, arg):
        return math.ceil(arg)

    @signature(_Arg(types=['number']))
    def _func_floor(self, arg):
        return math.floor(arg)

    @signature(_Arg(types=['string']), _Arg(types=['array-string']))
    def _func_join(self, separator, array):
        return separator.join(array)

    @signature(_Arg(types=['array-number']))
    def _func_max(self, arg):
        if arg:
            return max(arg)
        else:
            return None

    @signature(_Arg(types=['array-number']))
    def _func_min(self, arg):
        if arg:
            return min(arg)
        else:
            return None

    @signature(_Arg(types=['array-string', 'array-number']))
    def _func_sort(self, arg):
        return list(sorted(arg))

    @signature(_Arg(types=['array-number']))
    def _func_sum(self, arg):
        return sum(arg)

    @signature(_Arg(types=['object']))
    def _func_keys(self, arg):
        # To be consistent with .values()
        # should we also return the indices of a list?
        return list(arg.keys())

    @signature(_Arg(types=['object']))
    def _func_values(self, arg):
        return list(arg.values())

    @signature(_Arg())
    def _func_type(self, arg):
        if isinstance(arg, STRING_TYPE):
            return "string"
        elif isinstance(arg, bool):
            return "boolean"
        elif isinstance(arg, list):
            return "array"
        elif isinstance(arg, dict):
            return "object"
        elif isinstance(arg, (float, int)):
            return "number"
        elif arg is None:
            return "null"

    def _create_key_func(self, expression, allowed_types):
        py_types = []
        for type_ in allowed_types:
            py_types.extend(REVERSE_TYPES_MAP[type_])
        def keyfunc(x):
            result = expression.search(x)
            type_name = type(result).__name__
            if type_name not in py_types:
                raise JMESPathTypeError(self.name,
                                        result,
                                        type_name,
                                        allowed_types)
            return result
        return keyfunc

    @signature(_Arg(types=['array']), _Arg(types=['expref']))
    def _func_sort_by(self, array, expref):
        # sort_by allows for the expref to be either a number of
        # a string, so we have some special logic to handle this.
        # We evaluate the first array element and verify that it's
        # either a string of a number.  We then create a key function
        # that validates that type, which requires that remaining array
        # elements resolve to the same type as the first element.
        if not array:
            return array
        required_type = TYPES_MAP.get(
            type(expref.search(array[0])).__name__)
        if required_type not in ['number', 'string']:
            raise JMESPathTypeError(self.name,
                                    array[0],
                                    required_type,
                                    ['string', 'number'])
        keyfunc = self._create_key_func(expref, [required_type])
        return list(sorted(array, key=keyfunc))

    @signature(_Arg(types=['array']), _Arg(types=['expref']))
    def _func_max_by(self, array, expref):
        keyfunc = self._create_key_func(expref, ['number'])
        return max(array, key=keyfunc)

    @signature(_Arg(types=['array']), _Arg(types=['expref']))
    def _func_min_by(self, array, expref):
        keyfunc = self._create_key_func(expref, ['number'])
        return min(array, key=keyfunc)


class ExpressionReference(AST):
    def __init__(self, expression):
        self.children = [expression]

    def search(self, value):
        return _Expression(self.children[0])


class _Expression(AST):
    def __init__(self, expression):
        self.expression = expression

    def search(self, value):
        return self.expression.search(value)


class Pipe(AST):
    def __init__(self, parent, child):
        self.children = [parent, child]

    def search(self, value):
        left = self.children[0].search(value)
        return self.children[1].search(left)

    def pretty_print(self, indent=''):
        sub_indent = indent + ' ' * 4
        return "%s%s(\n%s%s,\n%s%s)" % (
            indent, self.__class__.__name__,
            sub_indent, self.children[0].pretty_print(sub_indent),
            sub_indent, self.children[1].pretty_print(sub_indent))


class Projection(AST):
    def __init__(self, left, right):
        self.children = [left, right]

    def search(self, value):
        base = self._evaluate_left_child(value)
        if base is None:
            return None
        else:
            collected = self._evaluate_right_child(base)
            return collected

    def _evaluate_left_child(self, value):
        base = self.children[0].search(value)
        if isinstance(base, list):
            return base
        else:
            # Invalid type, so we return None.
            return None

    def _evaluate_right_child(self, value):
        collected = []
        for element in value:
            current = self.children[1].search(element)
            if current is not None:
                collected.append(current)
        return collected

    def pretty_print(self, indent=''):
        sub_indent = indent + ' ' * 4
        return "%s%s(\n%s%s,\n%s%s)" % (
            indent, self.__class__.__name__,
            sub_indent, self.children[0].pretty_print(sub_indent),
            sub_indent, self.children[1].pretty_print(sub_indent))


class ValueProjection(Projection):
    def _evaluate_left_child(self, value):
        base_hash = self.children[0].search(value)
        try:
            return base_hash.values()
        except AttributeError:
            return None


class FilterProjection(Projection):
    # A filter projection is a left projection that
    # filter elements against an expression before allowing
    # them to be right evaluated.
    def __init__(self, left, right, comparator):
        self.children = [left, right, comparator]

    def _evaluate_right_child(self, value):
        result = []
        for element in value:
            if self.children[2].search(element):
                result.append(element)
        return super(FilterProjection, self)._evaluate_right_child(result)

    def pretty_print(self, indent=''):
        sub_indent = indent + ' ' * 4
        return "%s%s(\n%s%s,\n%s%s,\n%s%s)" % (
            indent, self.__class__.__name__,
            sub_indent, self.children[0].pretty_print(sub_indent),
            sub_indent, self.children[2].pretty_print(sub_indent),
            sub_indent, self.children[1].pretty_print(sub_indent),
        )


class Flatten(AST):
    def __init__(self, element):
        self.children = [element]

    def pretty_print(self, indent=''):
        return "%s%s(%s)" % (
            indent, self.__class__.__name__,
            self.children[0].pretty_print(indent).lstrip())

    def search(self, value):
        original = self.children[0].search(value)
        if not isinstance(original, list):
            return None
        merged_list = []
        for element in original:
            if isinstance(element, list):
                merged_list.extend(element)
            else:
                merged_list.append(element)
        return merged_list
