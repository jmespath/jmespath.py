import sys
import decimal
import json
from tests import unittest, OrderedDict

import jmespath
import jmespath.functions


class TestSearchOptions(unittest.TestCase):
    def test_can_provide_dict_cls(self):
        result = jmespath.search(
            '{a: a, b: b, c: c}.*',
            {'c': 'c', 'b': 'b', 'a': 'a', 'd': 'd'},
            options=jmespath.Options(dict_cls=OrderedDict))
        self.assertEqual(result, ['a', 'b', 'c'])

    def test_can_provide_custom_functions(self):
        class CustomFunctions(jmespath.functions.Functions):
            @jmespath.functions.signature(
                {'types': ['number']},
                {'types': ['number']})
            def _func_custom_add(self, x, y):
                return x + y

            @jmespath.functions.signature(
                {'types': ['number']},
                {'types': ['number']})
            def _func_my_subtract(self, x, y):
                return x - y


        options = jmespath.Options(custom_functions=CustomFunctions())
        self.assertEqual(
            jmespath.search('custom_add(`1`, `2`)', {}, options=options),
            3
        )
        self.assertEqual(
            jmespath.search('my_subtract(`10`, `3`)', {}, options=options),
            7
        )
        # Should still be able to use the original functions without
        # any interference from the CustomFunctions class.
        self.assertEqual(
            jmespath.search('length(`[1, 2]`)', {}), 2
        )



class TestPythonSpecificCases(unittest.TestCase):
    def test_can_compare_strings(self):
        # This is python specific behavior that's not in the official spec
        # yet, but this was regression from 0.9.0 so it's been added back.
        self.assertTrue(jmespath.search('a < b', {'a': '2016', 'b': '2017'}))

    @unittest.skipIf(not hasattr(sys, 'maxint'), 'Test requires long() type')
    def test_can_handle_long_ints(self):
        result = sys.maxint + 1
        self.assertEqual(jmespath.search('[?a >= `1`].a', [{'a': result}]),
                         [result])

    def test_can_handle_decimals_as_numeric_type(self):
        result = decimal.Decimal('3')
        self.assertEqual(jmespath.search('[?a >= `1`].a', [{'a': result}]),
                         [result])


class TestSearchJson(unittest.TestCase):
    """search_json() takes a JSON string and returns the same value as search()."""

    def test_basic_field(self):
        self.assertEqual(
            jmespath.search_json('a.b', '{"a": {"b": "x"}}'),
            'x')

    def test_projection(self):
        self.assertEqual(
            jmespath.search_json('a[*].b', '{"a": [{"b": 1}, {"b": 2}]}'),
            [1, 2])

    def test_empty_doc(self):
        self.assertEqual(
            jmespath.search_json('a', '{}'),
            None)

    def test_invalid_json_raises(self):
        with self.assertRaises(ValueError):
            jmespath.search_json('a', '{not json}')

    def test_matches_search_on_parsed_doc(self):
        doc = '{"servers": [{"name": "x", "up": true}, {"name": "y", "up": false}]}'
        expr = 'servers[?up == `true`].name'
        self.assertEqual(
            jmespath.search_json(expr, doc),
            jmespath.search(expr, json.loads(doc)))

    def test_passes_options_through(self):
        self.assertEqual(
            jmespath.search_json('a.b', '{"a": {"b": "x"}}',
                                 options=jmespath.Options()),
            'x')
