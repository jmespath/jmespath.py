import sys
import decimal
from tests import unittest, OrderedDict

import jmespath
import jmespath.functions


class TestSearchOptions(unittest.TestCase):
    def test_compiled_search_uses_each_calls_dict_class(self):
        expression = jmespath.compile('{outer: {value: value}}')
        data = {'value': 'kept'}
        ordered = jmespath.Options(dict_cls=OrderedDict)
        for options, expected_type in [(ordered, OrderedDict), (None, dict),
                                       (ordered, OrderedDict), (None, dict)]:
            result = expression.search(data, options=options)
            self.assertIs(type(result), expected_type)
            self.assertIs(type(result['outer']), expected_type)
            self.assertEqual(result, {'outer': {'value': 'kept'}})

    def test_compiled_search_keeps_custom_function_instances_separate(self):
        class CustomFunctions(jmespath.functions.Functions):
            def __init__(self, value):
                self.value = value

            @jmespath.functions.signature()
            def _func_custom_value(self):
                return self.value

        expression = jmespath.compile('custom_value()')
        first = jmespath.Options(custom_functions=CustomFunctions('first'))
        second = jmespath.Options(custom_functions=CustomFunctions('second'))
        self.assertEqual(expression.search({}, options=first), 'first')
        self.assertEqual(expression.search({}, options=second), 'second')
        with self.assertRaises(jmespath.exceptions.UnknownFunctionError):
            expression.search({})
        self.assertEqual(expression.search({}, options=first), 'first')

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
