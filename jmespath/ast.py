class AST(object):
    VALUE_METHODS = []

    def search(self, value):
        pass

    def _get_value_method(self, value):
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
    def __init__(self, parent, child):
        self.parent = parent
        self.child = child

    def search(self, value):
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


class ValuesBranch(AST):
    def __init__(self, node):
        self.node = node

    def pretty_print(self, indent=''):
        return "%sValuesBranch(%s)" % (indent, self.node)

    def search(self, value):
        response = self.node.search(value)
        try:
            return _MultiMatch(response.values())
        except AttributeError:
            return None


class ElementsBranch(AST):
    def __init__(self, node):
        self.node = node

    def pretty_print(self, indent=''):
        return "%sElementsBranch(%s)" % (indent, self.node)

    def search(self, value):
        response = self.node.search(value)
        return _MultiMatch(response)


class _MultiMatch(list):
    def __init__(self, elements):
        self.extend(elements)

    def get(self, value):
        results = _MultiMatch([])
        for element in self:
            result = element.get(value)
            if result is not None:
                if isinstance(result, list):
                    result = _MultiMatch(result)
                results.append(result)
        return results

    def get_index(self, index):
        matches = []
        for el in self:
            try:
                matches.append(el[index])
            except IndexError:
                pass
        if matches:
            return _MultiMatch(matches)


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
