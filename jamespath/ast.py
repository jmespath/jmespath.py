class AST(object):
    def search(self):
        pass


class SubExpression(object):
    def __init__(self, parent, child):
        self.parent = parent
        self.child = child

    def search(self, value):
        sub_value = self.parent.search(value)
        found = []
        for child in sub_value:
            found.extend(self.child.search(child))
        return found

    def __repr__(self):
        return "Child(%r, %s)" % (self.parent, self.child)


class Field(object):
    def __init__(self, name):
        self.name = name

    def search(self, value):
        if self.name in value:
            try:
                return [value.get(self.name)]
            except AttributeError:
                return []
        else:
            return []

    def __repr__(self):
        return "Field(%s)" % self.name


class Index(object):
    def __init__(self, index):
        self.index = index

    def search(self, value):
        # Even though we can index strings, we don't
        # want to support that.
        if isinstance(value, list):
            try:
                return [value[self.index]]
            except IndexError:
                return []
        else:
            return []

    def __repr__(self):
        return "Index(%s)" % self.index


class WildcardIndex(object):
    def search(self, value):
        return value

    def __repr__(self):
        return "WildcardIndex(*)"
