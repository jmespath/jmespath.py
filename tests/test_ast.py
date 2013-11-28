#!/usr/bin/env python

import unittest
from tests import OrderedDict

from jmespath import ast


class TestAST(unittest.TestCase):
    def setUp(self):
        pass

    def test_field(self):
        # jmespath: foo
        field = ast.Field('foo')
        match = field.search({'foo': 'bar'})
        self.assertEqual(match, 'bar')

    def test_field_no_match(self):
        # jmespath: foo
        field = ast.Field('foo')
        match = field.search({'bar': 'bar'})
        self.assertEqual(match, None)

    def test_field_when_dict(self):
        # jmespath: foo
        field = ast.Field('foo')
        match = field.search({'foo': {'bar': 'baz'}})
        self.assertEqual(match, {'bar': 'baz'})

    def test_field_when_list(self):
        # jmespath: foo
        field = ast.Field('foo')
        match = field.search({'foo': ['bar', 'baz']})
        self.assertEqual(match, ['bar', 'baz'])

    def test_dot_syntax(self):
        # jmespath: foo.bar
        child = ast.SubExpression(ast.Field('foo'), ast.Field('bar'))
        match = child.search({'foo': {'bar': 'correct', 'baz': 'wrong'}})
        self.assertEqual(match, 'correct')

    def test_multiple_nestings(self):
        # jmespath: foo.bar.baz
        child = ast.SubExpression(
            ast.Field('foo'),
            ast.SubExpression(ast.Field('bar'), ast.Field('baz')))
        match = child.search(
            {'foo': {'bar': {'baz': 'correct'}}})
        self.assertEqual(match, 'correct')

        self.assertEqual(
            child.search({'foo': {'bar': {'wrong': 'wrong'}}}), None)
        self.assertEqual(child.search({}), None)
        self.assertEqual(child.search([]), None)
        self.assertEqual(child.search(''), None)

    def test_index(self):
        # jmespath: foo[1]
        child = ast.SubExpression(ast.Field('foo'), ast.Index(1))
        match = child.search(
            {'foo': ['one', 'two', 'three']})
        self.assertEqual(match, 'two')

    def test_bad_index(self):
        # jmespath: foo[100]
        child = ast.SubExpression(ast.Field('foo'), ast.Index(100))
        match = child.search(
            {'foo': ['one', 'two', 'three']})
        self.assertEqual(match, None)

    def test_negative_index(self):
        # jmespath: foo[-1]
        child = ast.SubExpression(ast.Field('foo'), ast.Index(-1))
        match = child.search(
            {'foo': ['one', 'two', 'last']})
        self.assertEqual(match, 'last')

    def test_index_with_children(self):
        # jmespath: foo.bar[-1]
        child = ast.SubExpression(
            ast.Field('foo'),
            ast.SubExpression(ast.Field('bar'), ast.Index(-1)))
        match = child.search(
            {'foo': {'bar': ['first', 'middle', 'last']}})
        self.assertEqual(match, 'last')

    def test_multiple_indices(self):
        # jmespath: foo[1].bar[1]
        child = ast.SubExpression(
            ast.SubExpression(
                ast.Field('foo'), ast.Index(1)),
            ast.SubExpression(
                ast.Field('bar'), ast.Index(1)))
        match = child.search(
            {'foo': ['one', {'bar': ['zero', 'one']}]})
        self.assertEqual(match, 'one')

    def test_index_with_star(self):
        # jmespath: foo[*]
        child = ast.SubExpression(ast.Field('foo'), ast.WildcardIndex())
        match = child.search({'foo': ['one', 'two']})
        self.assertEqual(match, ['one', 'two'])

    def test_associative(self):
        data = {'foo': {'bar': ['one']}}
        # jmespath: foo.bar[0]
        first = ast.SubExpression(
            ast.Field('foo'),
            ast.SubExpression(ast.Field('bar'), ast.Index(0)))
        second = ast.SubExpression(
            ast.SubExpression(ast.Field('foo'), ast.Field('bar')),
            ast.Index(0))
        self.assertEqual(first.search(data), 'one')
        self.assertEqual(second.search(data), 'one')

    def test_wildcard_branches_on_dict_values(self):
        data = {'foo': {'bar': {'get': 'one'}, 'baz': {'get': 'two'}}}
        # ast for "foo.*.get"
        expression = ast.SubExpression(
            ast.SubExpression(ast.Field('foo'), ast.WildcardValues()),
            ast.Field('get'))
        match = expression.search(data)
        self.assertEqual(sorted(match), ['one', 'two'])
        self.assertEqual(expression.search({'foo': [{'bar': 'one'}]}), None)

    def test_wildcard_dot_wildcard(self):
        _ = OrderedDict
        data = _([(
            "top1", _({
                "sub1": _({"foo": "one"})
            })),
            ("top2", _({
                "sub1": _({"foo": "two"})
            })),
            ("top3", _({
                "sub3": _({"notfoo": "notfoo"})
            }))
        ])
        # ast for "*.*"
        expression = ast.SubExpression(
            ast.WildcardValues(), ast.WildcardValues())
        match = expression.search(data)
        self.assertEqual(match, [[{'foo': 'one'}], [{'foo': 'two'}],
                                 [{'notfoo': 'notfoo'}]])

    def test_wildcard_with_field_node(self):
        data = {
            "top1": {
                "sub1": {"foo": "one"}
            },
            "top2": {
                "sub1": {"foo": "two"}
            },
            "top3": {
                "sub3": {"notfoo": "notfoo"}
            }
        }
        # ast for "*.*.foo"
        expression = ast.SubExpression(
            ast.WildcardValues(), ast.SubExpression(ast.WildcardValues(),
                                                    ast.Field('foo')))
        match = expression.search(data)
        self.assertEqual(sorted(match), sorted([[],
                                                ['one'],
                                                ['two']]))

    def test_wildcard_branches_with_index(self):
        # foo[*].bar
        child = ast.SubExpression(
            ast.SubExpression(ast.Field('foo'), ast.WildcardIndex()),
            ast.Field('bar')
        )
        match = child.search(
            {'foo': [{'bar': 'one'}, {'bar': 'two'}]})
        self.assertTrue(isinstance(match, list))
        self.assertEqual(match, ['one', 'two'])

    def test_index_with_multi_match(self):
        # foo[*].bar[0]
        child = ast.SubExpression(
            ast.SubExpression(ast.Field('foo'), ast.WildcardIndex()),
            ast.SubExpression(
                ast.Field('bar'),
                ast.Index(0)))
        data = {'foo': [{'bar': ['one', 'two']}, {'bar': ['three', 'four']}]}
        match = child.search(data)
        self.assertEqual(match, ['one', 'three'])

    def test_or_expression(self):
        # foo or bar
        field_foo = ast.Field('foo')
        field_bar = ast.Field('bar')
        or_expression = ast.ORExpression(field_foo, field_bar)
        self.assertEqual(or_expression.search({'foo': 'foo'}), 'foo')
        self.assertEqual(or_expression.search({'bar': 'bar'}), 'bar')
        self.assertEqual(or_expression.search(
            {'foo': 'foo', 'bar': 'bar'}), 'foo')

    def test_multiselect_dict(self):
        # foo.{bar,baz
        field_foo = ast.KeyValPair(key_name='foo', node=ast.Field('foo'))
        field_bar = ast.KeyValPair(key_name='bar', node=ast.Field('bar'))
        field_baz = ast.KeyValPair(key_name='baz', node=ast.Field('baz'))
        multiselect = ast.MultiFieldDict([field_bar, field_baz])
        subexpr = ast.SubExpression(field_foo, multiselect)
        self.assertEqual(
            subexpr.search({'foo': {'bar': 1, 'baz': 2, 'qux': 3}}),
            {'bar': 1, 'baz': 2})

    def test_multiselect_different_key_names(self):
        field_foo = ast.KeyValPair(key_name='arbitrary', node=ast.Field('foo'))
        field_bar = ast.KeyValPair(key_name='arbitrary2', node=ast.Field('bar'))
        multiselect = ast.MultiFieldDict([field_foo, field_bar])
        self.assertEqual(multiselect.search({'foo': 'value1', 'bar': 'value2'}),
                         {'arbitrary': 'value1', 'arbitrary2': 'value2'})

    def test_multiselect_list(self):
        # foo.[bar,baz]
        field_foo = ast.Field('foo')
        field_bar = ast.Field('bar')
        field_baz = ast.Field('baz')
        multiselect = ast.MultiFieldList([field_bar, field_baz])
        subexpr = ast.SubExpression(field_foo, multiselect)
        self.assertEqual(
            subexpr.search({'foo': {'bar': 1, 'baz': 2, 'qux': 3}}),
            [1, 2])

    def test_multiselect_list_wildcard(self):
        data = {
            'foo': {
                'ignore1': {
                    'one': 1, 'two': 2, 'three': 3,
                },
                'ignore2': {
                    'one': 1, 'two': 2, 'three': 3,
                },
            }
        }
        expr = ast.SubExpression(
            ast.Field("foo"),
            ast.SubExpression(
                ast.WildcardValues(),
                ast.MultiFieldList([ast.Field("one"), ast.Field("two")])))
        self.assertEqual(expr.search(data), [[1, 2], [1, 2]])

    def test_wildcard_values_index_not_a_list(self):
        parsed = ast.SubExpression(
            ast.WildcardValues(),
            ast.SubExpression(ast.Field("foo"), ast.Index(0)))
        data = {"a": {"foo": 1}, "b": {"foo": 1}, "c": {"bar": 1}}
        self.assertEqual(parsed.search(data), [])

    def test_wildcard_values_index_does_exist(self):
        parsed = ast.SubExpression(
            ast.WildcardValues(),
            ast.SubExpression(ast.Field("foo"), ast.Index(0)))
        data = {"a": {"foo": [1]}, "b": {"foo": 1}, "c": {"bar": 1}}
        self.assertEqual(parsed.search(data), [1])

    def test_flattened_wildcard(self):
        parsed = ast.SubExpression(
            # foo[].bar
            ast.SubExpression(ast.Field("foo"), ast.ListElements()),
            ast.Field("bar"))
        data = {'foo': [{'bar': 1}, {'bar': 2}, {'bar': 3}]}
        self.assertEqual(parsed.search(data), [1, 2, 3])

    def test_multiple_nested_wildcards(self):
        # foo[].bar[].baz
        parsed = ast.SubExpression(
                ast.SubExpression(
                        ast.Field("foo"),
                        ast.ListElements()),
                ast.SubExpression(
                        ast.SubExpression(
                                ast.Field("bar"),
                                ast.ListElements()),
                        ast.Field("baz")))
        data = {
            "foo": [
                {"bar": [{"baz": 1}, {"baz": 2}]},
                {"bar": [{"baz": 3}, {"baz": 4}]},
            ]
        }
        self.assertEqual(parsed.search(data), [1, 2, 3, 4])

    def test_multiple_nested_wildcards_with_list_values(self):
        parsed = ast.SubExpression(
                ast.SubExpression(
                        ast.Field("foo"),
                        ast.ListElements()),
                ast.SubExpression(
                        ast.SubExpression(
                                ast.Field("bar"),
                                ast.ListElements()),
                        ast.Field("baz")))
        data = {
            "foo": [
                {"bar": [{"baz": [1]}, {"baz": [2]}]},
                {"bar": [{"baz": [3]}, {"baz": [4]}]},
            ]
        }
        self.assertEqual(parsed.search(data), [[1], [2], [3], [4]])

    def test_flattened_multiselect_list(self):
        # foo[].[bar,baz]
        field_foo = ast.Field('foo')
        parent = ast.SubExpression(field_foo, ast.ListElements())
        field_bar = ast.Field('bar')
        field_baz = ast.Field('baz')
        multiselect = ast.MultiFieldList([field_bar, field_baz])
        subexpr = ast.SubExpression(parent, multiselect)
        self.assertEqual(
            subexpr.search({'foo': [{'bar': 1, 'baz': 2, 'qux': 3}]}),
            [[1, 2]])


if __name__ == '__main__':
    unittest.main()
