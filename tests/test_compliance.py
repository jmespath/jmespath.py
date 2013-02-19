import os
import json

from nose.tools import assert_equal

import jamespath


TEST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'compliance')


def test_compliance():
    for root, dirnames, filenames in os.walk(TEST_DIR):
        for filename in filenames:
            if filename.endswith('.json'):
                full_path = os.path.join(root, filename)
                for given, expression, result in _load_cases(full_path):
                    yield _test_expression, given, expression, result


def _load_cases(full_path):
    all_test_data = json.load(open(full_path))
    for test_data in all_test_data:
        given = test_data['given']
        for case in test_data['cases']:
            yield given, case['expression'], case['result']


def _test_expression(given, expression, expected):
    parsed = jamespath.compile(expression)
    actual = parsed.search(given)
    error_msg = ("\nThe expression '%s' was suppose to give: %s.\n"
                 "Instead it matched: %s" % (expression, expected, actual))
    assert_equal(actual, expected, error_msg)
