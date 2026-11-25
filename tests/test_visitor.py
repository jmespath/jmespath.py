import gc
import platform
from types import MethodType
import unittest
from unittest import mock
import weakref

import jmespath
from jmespath import functions
from jmespath.visitor import Options, TreeInterpreter, Visitor
from tests import OrderedDict


@unittest.skipUnless(platform.python_implementation() == 'CPython',
                     'Immediate reference-counting cleanup requires CPython')
class TestVisitorLifetime(unittest.TestCase):
    def setUp(self):
        self.gc_enabled = gc.isenabled()
        gc.disable()

    def tearDown(self):
        gc.collect()
        if self.gc_enabled:
            gc.enable()

    def test_visitor_is_released_without_cyclic_gc(self):
        interpreter = TreeInterpreter()
        ref = weakref.ref(interpreter)
        self.assertEqual(
            interpreter.visit({'type': 'field', 'value': 'name'},
                              {'name': 'value'}), 'value')
        del interpreter
        self.assertIsNone(ref())

    def test_public_searches_release_each_interpreter(self):
        refs = []
        original_init = TreeInterpreter.__init__

        def tracking_init(interpreter, options=None):
            original_init(interpreter, options)
            refs.append(weakref.ref(interpreter))

        expression = jmespath.compile('items[].name')
        data = {'items': [{'name': 'one'}, {'name': 'two'}]}
        with mock.patch.object(TreeInterpreter, '__init__', tracking_init):
            for _ in range(100):
                self.assertEqual(expression.search(data), ['one', 'two'])
        self.assertEqual(len(refs), 100)
        self.assertTrue(all(ref() is None for ref in refs))

    def test_search_releases_options_and_custom_functions(self):
        class CustomFunctions(functions.Functions):
            @functions.signature({'types': ['string']})
            def _func_custom(self, value):
                return value.upper()

        custom_functions = CustomFunctions()
        options = Options(dict_cls=OrderedDict,
                          custom_functions=custom_functions)
        options_ref = weakref.ref(options)
        functions_ref = weakref.ref(custom_functions)
        result = jmespath.search('{name: custom(name)}', {'name': 'one'},
                                 options=options)
        self.assertIsInstance(result, OrderedDict)
        self.assertEqual(list(result.items()), [('name', 'ONE')])
        del options, custom_functions
        self.assertIsNone(options_ref())
        self.assertIsNone(functions_ref())

    def test_failed_search_releases_interpreter(self):
        interpreter = TreeInterpreter()
        ref = weakref.ref(interpreter)
        with self.assertRaisesRegex(NotImplementedError, 'unknown'):
            interpreter.visit({'type': 'unknown'}, {})
        del interpreter
        self.assertIsNone(ref())


class TestVisitorDispatch(unittest.TestCase):
    def test_subclass_override(self):
        class CustomInterpreter(TreeInterpreter):
            def visit_field(self, node, value):
                return value[node['value']].upper()

        interpreter = CustomInterpreter()
        node = {'type': 'field', 'value': 'name'}
        for _ in range(2):
            self.assertEqual(interpreter.visit(node, {'name': 'one'}), 'ONE')

    def test_instance_bound_method(self):
        interpreter = TreeInterpreter()

        def visit_field(self, node, value):
            self.last_value = value
            return value[node['value']].upper()

        interpreter.visit_field = MethodType(visit_field, interpreter)
        node = {'type': 'field', 'value': 'name'}
        for _ in range(2):
            self.assertEqual(interpreter.visit(node, {'name': 'one'}), 'ONE')
            self.assertEqual(interpreter.last_value, {'name': 'one'})

    def test_instance_callable(self):
        class Handler:
            def __call__(self, node, value):
                return value[node['value']].upper()

        interpreter = TreeInterpreter()
        interpreter.visit_field = Handler()
        node = {'type': 'field', 'value': 'name'}
        for _ in range(2):
            self.assertEqual(interpreter.visit(node, {'name': 'one'}), 'ONE')

    def test_method_bound_to_another_instance(self):
        class Handler:
            def visit_field(self, node, value):
                return value[node['value']].upper()

        interpreter = TreeInterpreter()
        interpreter.visit_field = Handler().visit_field
        node = {'type': 'field', 'value': 'name'}
        for _ in range(2):
            self.assertEqual(interpreter.visit(node, {'name': 'one'}), 'ONE')

    def test_static_method_and_keyword_arguments(self):
        class CustomVisitor(Visitor):
            @staticmethod
            def visit_custom(node, value, suffix=None):
                return value + suffix

        visitor = CustomVisitor()
        for _ in range(2):
            self.assertEqual(visitor.visit({'type': 'custom'}, 'one',
                                          suffix='two'), 'onetwo')

    def test_custom_default_method(self):
        visitor = Visitor()
        visitor.default_visit = lambda node, value: node['type'] + value
        for _ in range(2):
            self.assertEqual(visitor.visit({'type': 'custom'}, 'value'),
                             'customvalue')
