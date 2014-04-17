#!/usr/bin/env python

from tests import OrderedDict, unittest

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

    def test_wildcard_branches_with_index(self):
        # foo[*].bar
        child = ast.Projection(
            ast.Field('foo'), ast.Field('bar'))
        match = child.search(
            {'foo': [{'bar': 'one'}, {'bar': 'two'}]})
        self.assertTrue(isinstance(match, list))
        self.assertEqual(match, ['one', 'two'])

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

    def test_flattened_wildcard(self):
        # foo[].bar
        parsed = ast.Projection(ast.Flatten(ast.Field('foo')),
                                ast.Field('bar'))
        data = {'foo': [{'bar': 1}, {'bar': 2}, {'bar': 3}]}
        self.assertEqual(parsed.search(data), [1, 2, 3])

    def test_multiple_nested_wildcards(self):
        # foo[].bar[].baz
        parsed = ast.Projection(
            ast.Flatten(ast.Projection(ast.Flatten(ast.Field('foo')),
                                       ast.Field('bar'))),
            ast.Field('baz'))
        data = {
            "foo": [
                {"bar": [{"baz": 1}, {"baz": 2}]},
                {"bar": [{"baz": 3}, {"baz": 4}]},
            ]
        }
        self.assertEqual(parsed.search(data), [1, 2, 3, 4])

    def test_multiple_nested_wildcards_with_list_values(self):
        # foo[].bar[].baz
        parsed = ast.Projection(
            ast.Flatten(ast.Projection(ast.Flatten(ast.Field('foo')),
                                       ast.Field('bar'))),
            ast.Field('baz'))
        data = {
            "foo": [
                {"bar": [{"baz": [1]}, {"baz": [2]}]},
                {"bar": [{"baz": [3]}, {"baz": [4]}]},
            ]
        }
        self.assertEqual(parsed.search(data), [[1], [2], [3], [4]])

    def test_flattened_multiselect_list(self):
        # foo[].[bar,baz]
        field_bar = ast.Field('bar')
        field_baz = ast.Field('baz')
        multiselect = ast.MultiFieldList([field_bar, field_baz])
        projection = ast.Projection(
            ast.Flatten(ast.Field('foo')),
            multiselect)
        self.assertEqual(
            projection.search({'foo': [{'bar': 1, 'baz': 2, 'qux': 3}]}),
            [[1, 2]])

    def test_flattened_multiselect_with_none(self):
        # foo[].[bar,baz]
        field_bar = ast.Field('bar')
        field_baz = ast.Field('baz')
        multiselect = ast.MultiFieldList([field_bar, field_baz])
        projection = ast.Projection(
            ast.Flatten(ast.Field('foo')),
            multiselect)
        self.assertEqual(
            projection.search({'bar': [{'bar': 1, 'baz': 2, 'qux': 3}]}),
            None)

    def test_operator_eq(self):
        field_foo = ast.Field('foo')
        field_foo2 = ast.Field('foo')
        eq = ast.OPEquals(field_foo, field_foo2)
        self.assertTrue(eq.search({'foo': 'bar'}))

    def test_operator_not_equals(self):
        field_foo = ast.Field('foo')
        field_bar = ast.Field('bar')
        eq = ast.OPNotEquals(field_foo, field_bar)
        self.assertTrue(eq.search({'foo': '1', 'bar': '2'}))

    def test_operator_lt(self):
        field_foo = ast.Field('foo')
        field_bar = ast.Field('bar')
        eq = ast.OPLessThan(field_foo, field_bar)
        self.assertTrue(eq.search({'foo': 1, 'bar': 2}))

    def test_filter_expression(self):
        # foo[?bar==`yes`]
        field_foo = ast.Field('foo')
        field_bar = ast.Field('bar')
        literal = ast.Literal('yes')
        eq = ast.OPEquals(field_bar, literal)
        filter_expression = ast.FilterExpression(eq)
        full_expression = ast.SubExpression(field_foo, filter_expression)
        match = full_expression.search(
            {'foo': [{'bar': 'yes', 'v': 1},
                     {'bar': 'no', 'v': 2},
                     {'bar': 'yes', 'v': 3},]})
        self.assertEqual(match, [{'bar': 'yes', 'v': 1},
                                 {'bar': 'yes', 'v': 3}])

    def test_projection_simple(self):
        # foo[*].bar
        field_foo = ast.Field('foo')
        field_bar = ast.Field('bar')
        projection = ast.Projection(field_foo, field_bar)
        data = {'foo': [{'bar': 1}, {'bar': 2}, {'bar': 3}]}
        self.assertEqual(projection.search(data), [1, 2, 3])

    def test_projection_no_left(self):
        # [*].bar
        field_bar = ast.Field('bar')
        projection = ast.Projection(ast.Identity(), field_bar)
        data = [{'bar': 1}, {'bar': 2}, {'bar': 3}]
        self.assertEqual(projection.search(data), [1, 2, 3])

    def test_projection_no_right(self):
        # foo[*]
        field_foo = ast.Field('foo')
        projection = ast.Projection(field_foo, ast.Identity())
        data = {'foo': [{'bar': 1}, {'bar': 2}, {'bar': 3}]}
        self.assertEqual(projection.search(data),
                         [{'bar': 1}, {'bar': 2}, {'bar': 3}])

    def test_bare_projection(self):
        # [*]
        projection = ast.Projection(ast.Identity(), ast.Identity())
        data = [{'bar': 1}, {'bar': 2}, {'bar': 3}]
        self.assertEqual(projection.search(data), data)

    def test_base_projection_on_invalid_type(self):
        # [*]
        data = {'foo': [{'bar': 1}, {'bar': 2}, {'bar': 3}]}
        projection = ast.Projection(ast.Identity(), ast.Identity())
        # search() should return None because the evaluated
        # type is a dict, not a list.
        self.assertIsNone(projection.search(data))

    def test_multiple_projections(self):
        # foo[*].bar[*].baz
        field_foo = ast.Field('foo')
        field_bar = ast.Field('bar')
        field_baz = ast.Field('baz')
        second_projection = ast.Projection(field_bar, field_baz)
        first_projection = ast.Projection(field_foo, second_projection)
        data = {
            'foo': [
                {'bar': [{'baz': 1}, {'baz': 2}, {'baz': 3}],
                 'other': 1},
                {'bar': [{'baz': 4}, {'baz': 5}, {'baz': 6}],
                 'other': 2},
            ]
        }
        self.assertEqual(first_projection.search(data),
                         [[1, 2, 3], [4, 5, 6]])

    def test_values_projection(self):
        # foo.*.bar
        field_foo = ast.Field('foo')
        field_bar = ast.Field('bar')
        projection = ast.ValueProjection(field_foo, field_bar)
        data = {
            'foo': {
                'a': {'bar': 1},
                'b': {'bar': 2},
                'c': {'bar': 3},
            }

        }
        result = list(sorted(projection.search(data)))
        self.assertEqual(result, [1, 2, 3])

    def test_root_value_projection(self):
        # *
        projection = ast.ValueProjection(ast.Identity(), ast.Identity())
        data = {
            'a': 1,
            'b': 2,
            'c': 3,
        }
        result = list(sorted(projection.search(data)))
        self.assertEqual(result, [1, 2, 3])

    def test_no_left_node_value_projection(self):
        # *.bar
        field_bar = ast.Field('bar')
        projection = ast.ValueProjection(ast.Identity(), field_bar)
        data = {
            'a': {'bar': 1},
            'b': {'bar': 2},
            'c': {'bar': 3},
        }
        result = list(sorted(projection.search(data)))
        self.assertEqual(result, [1, 2, 3])

    def test_no_right_node_value_projection(self):
        # foo.*
        field_foo = ast.Field('foo')
        projection = ast.ValueProjection(field_foo, ast.Identity())
        data = {
            'foo': {
                'a': 1,
                'b': 2,
                'c': 3,
            }
        }
        result = list(sorted(projection.search(data)))
        self.assertEqual(result, [1, 2, 3])

    def test_filter_projection(self):
        # foo[?bar==`1`].baz
        field_foo = ast.Field('foo')
        field_bar = ast.Field('bar')
        field_baz = ast.Field('baz')
        literal = ast.Literal(1)
        comparator = ast.OPEquals(field_bar, literal)
        filter_projection = ast.FilterProjection(field_foo, field_baz, comparator)
        data = {
            'foo': [{'bar': 1}, {'bar': 2}, {'bar': 1, 'baz': 3}]
        }
        result = filter_projection.search(data)
        self.assertEqual(result, [3])

    def test_nested_filter_projection(self):
        data = {
            "reservations": [
                {
                    "instances": [
                        {
                            "foo": 1,
                            "bar": 2
                        },
                        {
                            "foo": 1,
                            "bar": 3
                        },
                        {
                            "foo": 1,
                            "bar": 2
                        },
                        {
                            "foo": 2,
                            "bar": 1
                        }
                    ]
                }
            ]
        }
        projection = ast.Projection(
            ast.Flatten(ast.Field('reservations')),
            ast.FilterProjection(
                ast.Field('instances'),
                ast.Identity(),
                ast.OPEquals(ast.Field('bar'), ast.Literal(1))))
        self.assertEqual(projection.search(data), [[{'bar': 1, 'foo': 2}]])


if __name__ == '__main__':
    unittest.main()
