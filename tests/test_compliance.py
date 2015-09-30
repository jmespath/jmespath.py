import os
from pprint import pformat
from tests import OrderedDict
from tests import json

from nose.tools import assert_equal

import jmespath
from jmespath.visitor import TreeInterpreter, Options


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
COMPLIANCE_DIR = os.path.join(TEST_DIR, 'compliance')
LEGACY_DIR = os.path.join(TEST_DIR, 'legacy')
NOT_SPECIFIED = object()
OPTIONS = Options(dict_cls=OrderedDict)


def test_compliance():
    for full_path in _walk_files():
        if full_path.endswith('.json'):
            for given, expression, result, error in _load_cases(full_path):
                if error is NOT_SPECIFIED and result is not NOT_SPECIFIED:
                    yield (_test_expression, given, expression,
                        result, os.path.basename(full_path))
                elif result is NOT_SPECIFIED and error is not NOT_SPECIFIED:
                    yield (_test_error_expression, given, expression,
                           error, os.path.basename(full_path))
                else:
                    parts = (given, expression, result, error)
                    raise RuntimeError("Invalid test description: %s" % parts)


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


def _load_cases(full_path):
    all_test_data = json.load(open(full_path), object_pairs_hook=OrderedDict)
    for test_data in all_test_data:
        given = test_data['given']
        for case in test_data['cases']:
            yield (given, case['expression'],
                   case.get('result', NOT_SPECIFIED),
                   case.get('error', NOT_SPECIFIED))


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
    except ValueError as e:
        # Test passes, it raised a parse error as expected.
        pass
    else:
        error_msg = ("\n\n  (%s) The expression '%s' was suppose to be a "
                     "syntax error, but it successfully parsed as:\n\n%s" % (
                         filename, expression, pformat(parsed.parsed)))
        error_msg = error_msg.replace(r'\n', '\n')
        raise AssertionError(error_msg)
