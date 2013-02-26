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

    def test_bad_parse(self):
        with self.assertRaises(ValueError):
            parsed = self.parser.parse('foo]baz')



class TestParserWildcards(unittest.TestCase):
    def setUp(self):
        self.parser = parser.Parser()
        self.data = {
            'foo': [
                {'bar': [{'baz': 'one'}, {'baz': 'two'}]},
                {'bar': [{'baz': 'three'}, {'baz': 'four'}]},
            ]
        }

    def test_multiple_index_wildcards(self):
        parsed = self.parser.parse('foo[*].bar[*].baz')
        self.assertEqual(parsed.search(self.data),
                         [['one', 'two'], ['three', 'four']])

    def test_wildcard_mix_with_indices(self):
        parsed = self.parser.parse('foo[*].bar[0].baz')
        self.assertEqual(parsed.search(self.data),
                         ['one', 'three'])

    def test_wildcard_mix_last(self):
        parsed = self.parser.parse('foo[0].bar[*].baz')
        self.assertEqual(parsed.search(self.data),
                         ['one', 'two'])


if __name__ == '__main__':
    unittest.main()
