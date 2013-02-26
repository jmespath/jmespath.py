import os
from pprint import pformat
from tests import OrderedDict
from tests import json

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
                    yield _test_expression, given, expression, result, filename


def _load_cases(full_path):
    all_test_data = json.load(open(full_path), object_pairs_hook=OrderedDict)
    for test_data in all_test_data:
        given = test_data['given']
        for case in test_data['cases']:
            yield given, case['expression'], case['result']


def _test_expression(given, expression, expected, filename):
    parsed = jamespath.compile(expression)
    actual = parsed.search(given)
    expected_repr = json.dumps(expected, indent=4)
    actual_repr = json.dumps(actual, indent=4)
    error_msg = ("\n(%s) The expression '%s' was suppose to give: %s.\n"
                 "Instead it matched: %s" % (filename, expression, expected_repr, actual_repr))
    assert_equal(actual, expected, error_msg)
