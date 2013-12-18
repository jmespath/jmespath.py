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
