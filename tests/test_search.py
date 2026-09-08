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


class TestNestedEquality(unittest.TestCase):
    def test_nested_booleans_are_not_numbers(self):
        for left, right in [
                ([True], [1]),
                ([False], [0]),
                ({'value': True}, {'value': 1}),
                ({'value': [False]}, {'value': [0]}),
                ([{'value': True}], [{'value': 1.0}])]:
            for a, b in [(left, right), (right, left)]:
                data = {'a': a, 'b': b}
                self.assertFalse(jmespath.search('a == b', data))
                self.assertTrue(jmespath.search('a != b', data))

    def test_nested_equality_preserves_json_semantics(self):
        cases = [
            ([1], [1.0], True),
            ({'a': [True, 1]}, {'a': [True, 1.0]}, True),
            ({'a': 1, 'b': 2}, {'b': 2, 'a': 1}, True),
            ([1], [1, 2], False),
            ({'a': None}, {'b': None}, False),
            ([], {}, False),
            ([], [], True),
            ({}, {}, True),
        ]
        for a, b, expected in cases:
            self.assertEqual(jmespath.search('a == b', {'a': a, 'b': b}),
                             expected)

    def test_filter_rejects_nested_boolean_number_matches(self):
        data = [{'value': [True]}, {'value': [1]}, {'value': [1.0]}]
        self.assertEqual(jmespath.search('[?value == `[1]`]', data),
                         data[1:])


    def test_deeply_nested_json_equality(self):
        for opening, closing in [('[', ']'), ('{"value":', '}')]:
            for left, right, expected in [
                    ('1', '1.0', True),
                    ('true', '1', False),
                    ('1', '2', False),
                    ('[]', '{}', False)]:
                a = json.loads(opening * 600 + left + closing * 600)
                b = json.loads(opening * 600 + right + closing * 600)
                self.assertIsNot(a, b)
                data = {'a': a, 'b': b}
                self.assertEqual(jmespath.search('a == b', data), expected)
                self.assertEqual(jmespath.search('a != b', data), not expected)
