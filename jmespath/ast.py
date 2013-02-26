class AST(object):
    def search(self, value):
        pass

    def pretty_print(self, indent=''):
        pass

    def __repr__(self):
        return self.pretty_print()


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
    def __init__(self, name):
        self.name = name

    def pretty_print(self, indent=''):
        return "%sField(%s)" % (indent, self.name)

    def search(self, value):
        if value is None:
            return None
        try:
            return value.get(self.name)
        except AttributeError:
            return None
        else:
            return None


class Index(AST):
    def __init__(self, index):
        self.index = index

    def pretty_print(self, indent=''):
        return "%sIndex(%s)" % (indent, self.index)

    def search(self, value):
        # Even though we can index strings, we don't
        # want to support that.
        if isinstance(value, _MultiMatch):
            try:
                return _MultiMatch([el[self.index] for el in value])
            except IndexError:
                return None
        elif isinstance(value, list):
            try:
                return value[self.index]
            except IndexError:
                return None
        else:
            return None


class WildcardIndex(AST):
    def search(self, value):
        return _MultiMatch(value)

    def pretty_print(self, indent=''):
        return "%sWildcardIndent(*)" % indent


class Wildcard(AST):
    def search(self, value):
        if isinstance(value, dict):
            return _MultiMatch(value.values())
        elif isinstance(value, _MultiMatch):
            return None
        else:
            return None

    def pretty_print(self, indent=''):
        return "%sWildcard(*)" % indent


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
