#!/usr/bin/env python

from tests import unittest

from jmespath import parser


class TestParser(unittest.TestCase):
    def setUp(self):
        self.parser = parser.Parser()

    def test_field(self):
        parsed = self.parser.parse('foo')
        self.assertEqual(parsed.search({'foo': 'bar'}), 'bar')

    def test_dot_syntax(self):
        parsed = self.parser.parse('foo.bar')
        self.assertEqual(parsed.search({'foo': {'bar': 'baz'}}), 'baz')

    def test_multiple_dots(self):
        parsed = self.parser.parse('foo.bar.baz')
        self.assertEqual(
            parsed.search({'foo': {'bar': {'baz': 'correct'}}}), 'correct')

    def test_index(self):
        parsed = self.parser.parse('foo[1]')
        self.assertEqual(
            parsed.search({'foo': ['zero', 'one', 'two']}),
            'one')

    def test_wildcard(self):
        parsed = self.parser.parse('foo[*]')
        self.assertEqual(
            parsed.search({'foo': ['zero', 'one', 'two']}),
            ['zero', 'one', 'two'])

    def test_wildcard_with_children(self):
        parsed = self.parser.parse('foo[*].bar')
        self.assertEqual(
            parsed.search({'foo': [{'bar': 'one'}, {'bar': 'two'}]}),
            ['one', 'two'])

    def test_or_expression(self):
        parsed = self.parser.parse('foo || bar')
        self.assertEqual(parsed.search({'foo': 'foo'}), 'foo')
        self.assertEqual(parsed.search({'bar': 'bar'}), 'bar')
        self.assertEqual(parsed.search({'foo': 'foo', 'bar': 'bar'}), 'foo')
        self.assertEqual(parsed.search({'bad': 'bad'}), None)

    def test_complex_or_expression(self):
        parsed = self.parser.parse('foo.foo || foo.bar')
        self.assertEqual(parsed.search({'foo': {'foo': 'foo'}}), 'foo')
        self.assertEqual(parsed.search({'foo': {'bar': 'bar'}}), 'bar')
        self.assertEqual(parsed.search({'foo': {'baz': 'baz'}}), None)

    def test_or_repr(self):
        parsed = self.parser.parse('foo || bar')
        self.assertEqual(repr(parsed), 'ORExpression(Field(foo), Field(bar))')

    def test_bad_parse(self):
        with self.assertRaises(ValueError):
            parsed = self.parser.parse('foo]baz')


class TestParserWildcards(unittest.TestCase):
    def setUp(self):
        self.parser = parser.Parser()
        self.data = {
            'foo': [
                {'bar': [{'baz': 'one'}, {'baz': 'two'}]},
                {'bar': [{'baz': 'three'}, {'baz': 'four'}, {'baz': 'five'}]},
            ]
        }

    def test_multiple_index_wildcards(self):
        parsed = self.parser.parse('foo[*].bar[*].baz')
        self.assertEqual(parsed.search(self.data),
                         [['one', 'two'], ['three', 'four', 'five']])

    def test_wildcard_mix_with_indices(self):
        parsed = self.parser.parse('foo[*].bar[0].baz')
        self.assertEqual(parsed.search(self.data),
                         ['one', 'three'])

    def test_wildcard_mix_last(self):
        parsed = self.parser.parse('foo[0].bar[*].baz')
        self.assertEqual(parsed.search(self.data),
                         ['one', 'two'])

    def test_indices_out_of_bounds(self):
        parsed = self.parser.parse('foo[*].bar[2].baz')
        self.assertEqual(parsed.search(self.data),
                         ['five'])

    def test_root_indices(self):
        parsed = self.parser.parse('[0]')
        self.assertEqual(parsed.search(['one', 'two']), 'one')

    def test_root_wildcard(self):
        parsed = self.parser.parse('*.foo')
        data = {'top1': {'foo': 'bar'}, 'top2': {'foo': 'baz'},
                'top3': {'notfoo': 'notfoo'}}
        # Sorted is being used because the order of the keys are not
        # required to be in any specific order.
        self.assertEqual(sorted(parsed.search(data)), sorted(['bar', 'baz']))
        self.assertEqual(sorted(self.parser.parse('*.notfoo').search(data)),
                         sorted(['notfoo']))

    def test_only_wildcard(self):
        parsed = self.parser.parse('*')
        data = {'foo': 'a', 'bar': 'b', 'baz': 'c'}
        self.assertEqual(sorted(parsed.search(data)), sorted(['a', 'b', 'c']))

    def test_escape_sequences(self):
        self.assertEqual(self.parser.parse('"foo\tbar"').search(
            {'foo\tbar': 'baz'}), 'baz')
        self.assertEqual(self.parser.parse('"foo\nbar"').search(
            {'foo\nbar': 'baz'}), 'baz')
        self.assertEqual(self.parser.parse('"foo\bbar"').search(
            {'foo\bbar': 'baz'}), 'baz')
        self.assertEqual(self.parser.parse('"foo\fbar"').search(
            {'foo\fbar': 'baz'}), 'baz')
        self.assertEqual(self.parser.parse('"foo\rbar"').search(
            {'foo\rbar': 'baz'}), 'baz')

    def test_consecutive_escape_sequences(self):
        parsed = self.parser.parse('"foo\\nbar"')
        self.assertEqual(parsed.search({'foo\\nbar': 'baz'}), 'baz')

        parsed = self.parser.parse('"foo\n\t\rbar"')
        self.assertEqual(parsed.search({'foo\n\t\rbar': 'baz'}), 'baz')

    def test_escape_sequence_at_end_of_string_not_allowed(self):
        with self.assertRaises(ValueError):
            parsed = self.parser.parse('foobar\\')


class TestParserCaching(unittest.TestCase):
    def test_compile_lots_of_expressions(self):
        # We have to be careful here because this is an implementation detail
        # that should be abstracted from the user, but we need to make sure we
        # exercise the code and that it doesn't blow up.
        p = parser.Parser()
        compiled = []
        compiled2 = []
        for i in range(parser.Parser._max_size + 1):
            compiled.append(p.parse('foo%s' % i))
        # Rerun the test and half of these entries should be from the
        # cache but they should still be equal to compiled.
        for i in range(parser.Parser._max_size + 1):
            compiled2.append(p.parse('foo%s' % i))
        self.assertEqual(compiled, compiled2)


if __name__ == '__main__':
    unittest.main()
