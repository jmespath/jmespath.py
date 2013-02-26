class AST(object):
    def search(self, value):
        pass


class SubExpression(AST):
    def __init__(self, parent, child):
        self.parent = parent
        self.child = child

    def search(self, value):
        sub_value = self.parent.search(value)
        found = self.child.search(sub_value)
        return found

    def __repr__(self):
        return "SubExpression(%r, %s)" % (self.parent, self.child)


class Field(AST):
    def __init__(self, name):
        self.name = name

    def search(self, value):
        if value is None:
            return None
        try:
            return value.get(self.name)
        except AttributeError:
            return None
        else:
            return None

    def __repr__(self):
        return "Field(%s)" % self.name


class Index(AST):
    def __init__(self, index):
        self.index = index

    def search(self, value):
        # Even though we can index strings, we don't
        # want to support that.
        if isinstance(value, list):
            try:
                return value[self.index]
            except IndexError:
                return None
        else:
            return None

    def __repr__(self):
        return "Index(%s)" % self.index


class WildcardIndex(AST):
    def search(self, value):
        return _MultiMatch(value)

    def __repr__(self):
        return "WildcardIndex(*)"


class Wildcard(AST):
    def search(self, value):
        if isinstance(value, dict):
            return _MultiMatch(value.values())
        elif isinstance(value, _MultiMatch):
            return None
        else:
            return None

    def __repr__(self):
        return "Wildcard(*)"


class _MultiMatch(list):
    def __init__(self, elements):
        self.extend(elements)

    def get(self, value):
        results = []
        for element in self:
            result = element.get(value)
            if result is not None:
                results.append(result)
        return results
