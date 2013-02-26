#!/usr/bin/env python

from tests import unittest

from jamespath import parser


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


if __name__ == '__main__':
    unittest.main()
