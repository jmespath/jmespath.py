import operator
from jmespath.compat import with_repr_method


@with_repr_method
class AST(object):
    VALUE_METHODS = []

    def search(self, value):
        pass

    def _get_value_method(self, value):
        # This will find the appropriate getter method
        # based on the passed in value.
        for method_name in self.VALUE_METHODS:
            method = getattr(value, method_name, None)
            if method is not None:
                return method

    def pretty_print(self, indent=''):
        return super(AST, self).__repr__()

    def __repr__(self):
        return self.pretty_print()

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)


class SubExpression(AST):
    """Represents a subexpression match.

    A subexpression match has a parent and a child node.  A simple example
    would be something like 'foo.bar' which is represented as::

        SubExpression(Field(foo), Field(bar))

    """
    def __init__(self, parent, child):
        self.parent = parent
        self.child = child

    def search(self, value):
        # To evaluate a subexpression we first evaluate the parent object
        # and then feed the match of the parent node into the child node.
        sub_value = self.parent.search(value)
        found = self.child.search(sub_value)
        return found

    def pretty_print(self, indent=''):
        sub_indent = indent + ' ' * 4
        return "%sSubExpression(\n%s%s,\n%s%s)" % (
            indent,
            sub_indent, self.parent.pretty_print(sub_indent),
            sub_indent, self.child.pretty_print(sub_indent))


class Field(AST):
    VALUE_METHODS = ['get']

    def __init__(self, name):
        self.name = name

    def pretty_print(self, indent=''):
        return "%sField(%s)" % (indent, self.name)

    def search(self, value):
        method = self._get_value_method(value)
        if method is not None:
            return method(self.name)


class BaseMultiField(AST):
    def __init__(self, nodes):
        self.nodes = nodes

    def search(self, value):
        if value is None:
            return None
        method = self._get_value_method(value)
        if method is not None:
            return method(self.nodes)
        else:
            return self._multi_get(value)

    def _multi_get(self, value):
        # Subclasses must define this method.
        raise NotImplementedError("_multi_get")

    def pretty_print(self, indent=''):
        return "%s%s(%s)" % (indent, self.__class__.__name__, self.nodes)


class MultiFieldDict(BaseMultiField):
    VALUE_METHODS = ['multi_get']

    def _multi_get(self, value):
        collected = {}
        for node in self.nodes:
            collected[node.key_name] = node.search(value)
        return collected


class MultiFieldList(BaseMultiField):
    VALUE_METHODS = ['multi_get_list']

    def _multi_get(self, value):
        collected = []
        for node in self.nodes:
            collected.append(node.search(value))
        return collected


class KeyValPair(AST):
    def __init__(self, key_name, node):
        self.key_name = key_name
        self.node = node

    def search(self, value):
        return self.node.search(value)

    def pretty_print(self, indent=''):
        return "%sKeyValPair(key_name=%s, node=%s)" % (indent, self.key_name,
                                                       self.node)


class Index(AST):
    VALUE_METHODS = ['get_index', '__getitem__']

    def __init__(self, index):
        self.index = index

    def pretty_print(self, indent=''):
        return "%sIndex(%s)" % (indent, self.index)

    def search(self, value):
        # Even though we can index strings, we don't
        # want to support that.
        if not isinstance(value, list):
            return None
        method = self._get_value_method(value)
        if method is not None:
            try:
                return method(self.index)
            except IndexError:
                pass


class WildcardIndex(AST):
    """Represents a wildcard index.

    For example::

        foo[*] -> SubExpression(Field(foo), WildcardIndex())

    """
    def search(self, value):
        if not isinstance(value, list):
            return None
        return _Projection(value)

    def pretty_print(self, indent=''):
        return "%sIndex(*)" % indent


class WildcardValues(AST):
    """Represents a wildcard on the values of a JSON object.

    For example::

        foo.* -> SubExpression(Field(foo), WildcardValues())

    """
    def search(self, value):
        try:
            return _Projection(value.values())
        except AttributeError:
            return None

    def pretty_print(self, indent=''):
        return "%sWildcardValues()" % indent


class ListElements(AST):
    def search(self, value):
        if isinstance(value, list):
            # reduce inner list elements into
            # a single list.
            merged_list = []
            for element in value:
                if isinstance(element, list):
                    merged_list.extend(element)
                else:
                    merged_list.append(element)
            return _Projection(merged_list)
        else:
            return None

    def pretty_print(self, indent=''):
        return "%sListElements()" % indent


class ORExpression(AST):
    def __init__(self, first, remaining):
        self.first = first
        self.remaining = remaining

    def search(self, value):
        matched = self.first.search(value)
        if matched is None:
            matched = self.remaining.search(value)
        return matched

    def pretty_print(self, indent=''):
        return "%sORExpression(%s, %s)" % (indent, self.first,
                                           self.remaining)


class FilterExpression(AST):
    VALUE_METHODS = ['multi_filter']

    def __init__(self, expression):
        self.expression = expression

    def search(self, value):
        if not isinstance(value, list):
            return None
        method = self._get_value_method(value)
        if method is not None:
            return method(self.expression)
        else:
            result = []
            for element in value:
                if self.expression.search(element):
                    result.append(element)
            return _Projection(result)

    def pretty_print(self, indent=''):
        return '%sFilterExpression(%s)' % (indent, self.expression)


class Literal(AST):
    VALUE_METHODS = ['get_literal']
    def __init__(self, literal_value):
        self.literal_value = literal_value

    def search(self, value):
        method = self._get_value_method(value)
        if method is not None:
            return method(self.literal_value)
        else:
            return self.literal_value

    def pretty_print(self, indent=''):
        return '%sLiteral(%s)' % (indent, self.literal_value)


class Comparator(AST):
    # Subclasses must define the operation function.
    operation = None

    def __init__(self, first, second):
        self.first = first
        self.second = second

    def search(self, data):
        return self.operation(self.first.search(data),
                              self.second.search(data))

    def pretty_print(self, indent=''):
        return '%s%s(%s, %s)' % (indent, self.__class__.__name__,
                                 self.first, self.second)


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


class _Projection(list):
    def __init__(self, elements):
        self.extend(elements)

    def get(self, value):
        results = self.__class__([])
        for element in self:
            try:
                result = element.get(value)
            except AttributeError:
                continue
            if result is not None:
                if isinstance(result, list):
                    result = self.__class__(result)
                results.append(result)
        return results

    def get_index(self, index):
        matches = []
        for el in self:
            if not isinstance(el, list):
                continue
            try:
                matches.append(el[index])
            except (IndexError, TypeError):
                pass
        return self.__class__(matches)

    def multi_get(self, nodes):
        results = self.__class__([])
        for element in self:
            if isinstance(element, self.__class__):
                result = element.multi_get(nodes)
            else:
                result = {}
                for node in nodes:
                    result[node.key_name] = node.search(element)
            results.append(result)
        return results

    def multi_get_list(self, nodes):
        results = self.__class__([])
        for element in self:
            if isinstance(element, self.__class__):
                result = element.multi_get_list(nodes)
            else:
                result = []
                for node in nodes:
                    result.append(node.search(element))
            results.append(result)
        return results

    def values(self):
        results = self.__class__([])
        for element in self:
            try:
                current = self.__class__(element.values())
                results.append(current)
            except AttributeError:
                continue
        return results

    def get_literal(self, literal_value):
        # To adhere to projection semantics, a literal value is projected for
        # each element of the list.
        results = self.__class__([])
        for element in self:
            if isinstance(element, self.__class__):
                results.append(element.get_literal(literal_value))
            else:
                results.append(literal_value)
        return results

    def multi_filter(self, expression):
        results = self.__class__([])
        for element in self:
            if isinstance(element, self.__class__):
                sub_results = element.multi_filter(expression)
                results.append(sub_results)
            else:
                if expression.search(element):
                    results.append(element)
        return results
