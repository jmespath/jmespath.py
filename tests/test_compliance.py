import os
import re
from pprint import pformat

import six

from tests import OrderedDict
from tests import json
from tests import unittest

from future.utils import with_metaclass
from nose.tools import assert_equal

from jmespath.visitor import Options

if six.PY2:
    from io import open

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
COMPLIANCE_DIR = os.path.join(TEST_DIR, 'compliance')
LEGACY_DIR = os.path.join(TEST_DIR, 'legacy')
NOT_SPECIFIED = object()
OPTIONS = Options(dict_cls=OrderedDict)


def _walk_files():
    # Check for a shortcut when running the tests interactively.
    # If a JMESPATH_TEST is defined, that file is used as the
    # only test to run.  Useful when doing feature development.
    single_file = os.environ.get('JMESPATH_TEST')
    if single_file is not None:
        yield os.path.abspath(single_file)
    else:
        for root, dirnames, filenames in os.walk(TEST_DIR):
            for filename in filenames:
                yield os.path.join(root, filename)
        for root, dirnames, filenames in os.walk(LEGACY_DIR):
            for filename in filenames:
                yield os.path.join(root, filename)


def load_cases(full_path):
    all_test_data = json.load(open(full_path, encoding='utf-8'), object_pairs_hook=OrderedDict)
    for test_data in all_test_data:
        given = test_data['given']
        for case in test_data['cases']:
            if 'result' in case:
                test_type = 'result'
            elif 'error' in case:
                test_type = 'error'
            elif 'bench' in case:
                test_type = 'bench'
            else:
                raise RuntimeError("Unknown test type: %s" % json.dumps(case))
            yield given, test_type, case


def _test_expression(given, expression, expected, filename):
    import jmespath.parser
    try:
        parsed = jmespath.compile(expression)
    except ValueError as e:
        raise AssertionError(
            'jmespath expression failed to compile: "%s", error: %s"' %
            (expression, e))
    actual = parsed.search(given, options=OPTIONS)
    expected_repr = json.dumps(expected, indent=4)
    actual_repr = json.dumps(actual, indent=4)
    error_msg = ("\n\n  (%s) The expression '%s' was suppose to give:\n%s\n"
                 "Instead it matched:\n%s\nparsed as:\n%s\ngiven:\n%s" % (
                     filename, expression, expected_repr,
                     actual_repr, pformat(parsed.parsed),
                     json.dumps(given, indent=4)))
    error_msg = error_msg.replace(r'\n', '\n')
    assert_equal(actual, expected, error_msg)


def _test_error_expression(given, expression, error, filename):
    import jmespath.parser
    if error not in ('syntax', 'invalid-type',
                     'unknown-function', 'invalid-arity', 'invalid-value'):
        raise RuntimeError("Unknown error type '%s'" % error)
    try:
        parsed = jmespath.compile(expression)
        parsed.search(given)
    except ValueError:
        # Test passes, it raised a parse error as expected.
        pass
    except Exception as e:
        # Failure because an unexpected exception was raised.
        error_msg = ("\n\n  (%s) The expression '%s' was suppose to be a "
                     "syntax error, but it raised an unexpected error:\n\n%s" % (
                         filename, expression, e))
        error_msg = error_msg.replace(r'\n', '\n')
        raise AssertionError(error_msg)
    else:
        error_msg = ("\n\n  (%s) The expression '%s' was suppose to be a "
                     "syntax error, but it successfully parsed as:\n\n%s" % (
                         filename, expression, pformat(parsed.parsed)))
        error_msg = error_msg.replace(r'\n', '\n')
        raise AssertionError(error_msg)


# Generate and run test functions from json dataset
class GeneratorTestJsonComplianceMeta(type):
    dict_key_increment = 0

    def __new__(mcs, name, bases, dict):

        # Load dataset from json files
        def compile_tests():
            for full_path in _walk_files():
                if full_path.endswith('.json'):
                    for given, test_type, test_data in load_cases(full_path):
                        t = test_data
                        # Benchmark tests aren't run as part of the normal
                        # test suite, so we only care about 'result' and
                        # 'error' test_types.
                        if test_type == 'result':
                            yield (_test_expression, given, t['expression'],
                                   t['result'], full_path)
                        elif test_type == 'error':
                            yield (_test_error_expression, given, t['expression'],
                                   t['error'], full_path)

        # Generate test function executor
        def gen_test(function, given_arg, expression_arg, expected_result, json_filename):
            def test(self):
                function(given_arg, expression_arg, expected_result, json_filename)

            return test

        # Compile all tests from json files
        for (f, given_json, expression, expected, file_path) in compile_tests():
            parent_dir = os.path.basename(os.path.dirname(file_path))
            filename = os.path.basename(file_path)
            # Create test function name, remove '.', '\' and '/' from path
            test_name = "test_%s" % re.sub(r"[\\./]", "_", parent_dir + "_" + filename)

            if test_name in dict:
                # If this name is exist, add incremented number to name and try to check it again
                while test_name in dict:
                    mcs.dict_key_increment += 1
                    test_name = test_name + str(mcs.dict_key_increment)

                dict[test_name] = gen_test(f, given_json, expression, expected, filename)
            else:
                mcs.dict_key_increment = 0
                dict[test_name] = gen_test(f, given_json, expression, expected, filename)

        return type.__new__(mcs, name, bases, dict)


# Use with_metaclass() for Python 2 and 3 compatibility
class TestJsonCompliance(with_metaclass(GeneratorTestJsonComplianceMeta, unittest.TestCase)):
    pass


if __name__ == '__main__':
    unittest.main()
