class Visitor(object):
    def visit(self, node, *args, **kwargs):
        method = getattr(
            self, 'visit_%s' % node.__class__.__name__.lower(),
            self.default_visit)
        return method(node, *args, **kwargs)

    def default_visit(self, node, *args, **kwargs):
        pass


class TreeInterpreter(Visitor):
    def __init__(self, starting_data):
        self.result = starting_data

    def visit_subexpression(self, node):
        self.visit(node.parent)
        self.visit(node.child)

    def visit_field(self, node):
        try:
            self.result = self.result.get(node.name)
        except AttributeError:
            self.result = None

    def visit_multifielddict(self, node):
        value = self.result
        if value is not None:
            method = getattr(value, 'multi_get', None)
            if method is not None:
                self.result = method(node.nodes)
            else:
                collected = {}
                original = value
                for node in node.nodes:
                    self.result = original
                    self.visit(node)
                    collected[node.key_name] = self.result
                self.result = collected

    def visit_multifieldlist(self, node):
        value = self.result
        if value is not None:
            method = getattr(value, 'multi_get_list', None)
            if method is not None:
                self.result = method(node.nodes)
            else:
                collected = []
                original = value
                for node in node.nodes:
                    self.result = original
                    self.visit(node)
                    collected.append(self.result)
                self.result = collected

    def visit_keyvalpair(self, node):
        self.visit(node.node)

    def visit_index(self, node):
        value = self.result
        # Even though we can index strings, we don't
        # want to support that.
        if not isinstance(value, list):
            self.result = None
        else:
            method = getattr(value, 'get_index',
                             getattr(value, '__getitem__'))
            if method is not None:
                try:
                    self.result = method(node.index)
                except IndexError:
                    self.result = None

    def visit_wildcardindex(self, node):
        self.result = _Projection(self.result)

    def visit_wildcardvalues(self, node):
        try:
            self.result = _Projection(self.result.values())
        except AttributeError:
            self.result = None

    def visit_listelements(self, node):
        value = self.result
        if isinstance(value, list):
            # reduce inner list elements into
            # a single list.
            merged_list = []
            for element in value:
                if isinstance(element, list):
                    merged_list.extend(element)
                else:
                    merged_list.append(element)
            self.result = _Projection(merged_list)
        else:
            self.result = _Projection(value)

    def visit_orexpression(self, node):
        original = self.result
        self.visit(node.first)
        if self.result is None:
            self.result = original
            self.visit(node.remaining)


class PrintVisitor(Visitor):
    def visit_subexpression(self, node, indent=''):
        sub_indent = indent + ' ' * 4
        return "%s%s(\n%s%s,\n%s%s)" % (
            indent, node.__class__.__name__,
            sub_indent, self.visit(node.parent, sub_indent),
            sub_indent, self.visit(node.child, sub_indent))

    def visit_field(self, node, indent=''):
        return "%s%s(%s)" % (indent, node.__class__.__name__, node.name)

    def visit_multifielddict(self, node, indent=''):
        return "%s%s(%s)" % (indent, node.__class__.__name__, node.nodes)

    def visit_multifieldlist(self, node, indent=''):
        return "%s%s(%s)" % (indent, node.__class__.__name__, node.nodes)

    def visit_keyvalpair(self, node, indent=''):
        return "%sKeyValPair(key_name=%s, node=%s)" % (indent, node.key_name,
                                                       node.node)

    def visit_index(self, node, indent=''):
        return "%sIndex(%s)" % (indent, node.index)

    def visit_wildcardindex(self, node, indent=''):
        return "%sIndex(*)" % (indent,)

    def visit_wildcardvalues(self, node, indent=''):
        return "%sWildcardValues()" % (indent,)

    def visit_listelements(self, node, indent=''):
        return "%sListElements()" % indent

    def visit_orexpression(self, node, indent=''):
        return "%sORExpression(%s, %s)" % (indent, node.first,
                                           node.remaining)


class AST(object):
    def search(self, value):
        interpreter = TreeInterpreter(value)
        interpreter.visit(self)
        return interpreter.result

    def __repr__(self):
        printer = PrintVisitor()
        return printer.visit(self)

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


class Field(AST):
    def __init__(self, name):
        self.name = name


class BaseMultiField(AST):
    def __init__(self, nodes):
        self.nodes = nodes


class MultiFieldDict(BaseMultiField):
    pass


class MultiFieldList(BaseMultiField):
    pass


class KeyValPair(AST):
    def __init__(self, key_name, node):
        self.key_name = key_name
        self.node = node


class Index(AST):
    def __init__(self, index):
        self.index = index


class WildcardIndex(AST):
    """Represents a wildcard index.

    For example::

        foo[*] -> SubExpression(Field(foo), WildcardIndex())

    """
    pass


class WildcardValues(AST):
    """Represents a wildcard on the values of a JSON object.

    For example::

        foo.* -> SubExpression(Field(foo), WildcardValues())

    """
    pass


class ListElements(AST):
    pass


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
