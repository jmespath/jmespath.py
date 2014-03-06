#!/usr/bin/env python
"""JMESPath compliance test runner.

This is a test runner that will run the JMESPath compliance tests against a
JMESPath executable.

Compliance tests are broken down into three components:

    * The filename that contains the test.  These are grouped by feature.  The
    * test group within the file. A test group can have multiple tests.  The
    * test case number.  This is an individual test.

If "-t/--tests" is not provided then all compliance tests are run.
You can specify which tests to run using the "-t/--tests" argument.
Each test is specified as a comma separated list consisting of
"category,group_number,test_number".  The group number and test number
are optional.  If no test number if provided all tests within the group
are run.  If no group number is given, all tests in that category
are run.  To see a list of categories use the "-l/--list" option.
Multiple comma separates values are space separated.

When a test failure occurs, the category, group number, and test number are
displayed in the failure message.  This allows you to quickly rerun a specific
test.

Examples
========

These examples show how to run the compliance tests against the "jp"
executable.

Run all the basic tests::

    jp-compliance -e jp -t basic

Run all the basic tests in group 1::

    jp-compliance -e jp -t basic,1

Run the filter and function tests::

    jp-compliance -e jp -t filters functions

Run the filter and function tests in group 1::

    jp-compliance -e jp -t filters,1 functions,1

"""

import sys
import argparse
import os
import subprocess
import json
import shlex


if sys.version_info[:2] == (2, 6):
    import simplejson as json
    from ordereddict import OrderedDict
else:
    import json
    from collections import OrderedDict


_abs = os.path.abspath
_dname = os.path.dirname
_pjoin = os.path.join
_splitext = os.path.splitext
_bname = os.path.basename


class ComplianceTestRunner(object):
    TEST_DIR = _pjoin(_dname(_dname(_abs(__file__))), 'tests', 'compliance')

    def __init__(self, exe=None, tests=None, test_dir=TEST_DIR):
        self.test_dir=  test_dir
        self.tests = tests
        self.jp_executable = exe

    def run_tests(self):
        for test_case in self._test_cases():
            if self._should_run(test_case):
                self._run_test(test_case)

    def _should_run(self, test_case):
        if not self.tests:
            return True
        # Specific tests were called out so we need
        # at least one thing in self.tests to match
        # in order to run the test.
        for allowed_test in self.tests:
            if self._is_subset(allowed_test, test_case):
                return True
        return False

    def _is_subset(self, subset, fullset):
        for key in subset:
            if subset[key] != fullset.get(key):
                return False
        return True

    def _load_test_file(self, test_json_file):
        with open(test_json_file) as f:
            loaded_test = json.loads(f.read(), object_pairs_hook=OrderedDict)
        return loaded_test

    def _load_test_cases(self, filename, group_number, test_group):
        given = test_group['given']
        for i, case in enumerate(test_group['cases']):
            current = {"given": given, "group_number": group_number,
                       "test_number": i,
                       'category': _splitext(_bname(filename))[0]}
            current.update(case)
            yield current

    def _test_cases(self):
        for test_json_file in self.get_compliance_test_files():
            test_groups = self._load_test_file(test_json_file)
            for i, test_group in enumerate(test_groups):
                test_cases = self._load_test_cases(test_json_file, i, test_group)
                for test_case in test_cases:
                    yield test_case

    def _run_test(self, test_case):
        command = shlex.split(self.jp_executable)
        command.append(test_case['expression'])
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE)
        process.stdin.write(json.dumps(test_case['given']))
        process.stdin.flush()
        stdout, stderr = process.communicate()
        if 'result' in test_case:
            actual = json.loads(stdout)
            expected = test_case['result']
            if not actual == expected:
                self._show_failure(actual, test_case)
            else:
                sys.stdout.write('.')
                sys.stdout.flush()
        else:
            error_type = test_case['error']
            # For errors, we expect the error type on stderr.
            if error_type not in stderr:
                self._show_failure_for_error(stderr, test_case)
            else:
                sys.stdout.write('.')
                sys.stdout.flush()

    def _show_failure(self, actual, test_case):
        test_case['actual'] = json.dumps(actual)
        test_case['result'] = json.dumps(test_case['result'])
        failure_message = (
            "\nFAIL {category},{group_number},{test_number}\n"
            "The expression: {expression}\n"
            "was suppose to give: {result}\n"
            "but instead gave: {actual}\n"
        ).format(**test_case)
        sys.stdout.write(failure_message)

    def _show_failure_for_error(self, stderr, test_case):
        test_case['stderr'] = stderr
        failure_message = (
            "\nFAIL {category},{group_number},{test_number}\n"
            "The expression: {expression}\n"
            "was suppose to emit the error: {error}\n"
            "but instead gave: \n{stderr}\n"
        ).format(**test_case)
        sys.stdout.write(failure_message)

    def get_compliance_test_files(self):
        for root, dirnames, filenames in os.walk(self.test_dir):
            for filename in filenames:
                if filename.endswith('.json'):
                    full_path = _pjoin(root, filename)
                    yield full_path


def display_available_tests(test_files):
    print("Available test types:\n")
    for filename in test_files:
        no_extension = os.path.splitext(os.path.basename(filename))[0]
        print(no_extension)


def test_spec(value):
    parts = value.split(',')
    if not parts:
        raise ValueError("%s should be a comma separated list." % value)
    spec = {'category': parts[0]}
    if len(parts) == 2:
        spec['group_number'] = int(parts[1])
    elif len(parts) == 3:
        spec['group_number'] = int(parts[1])
        spec['test_number'] = int(parts[2])
    return spec


def main():
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument('-e', '--exe', help='The JMESPath executable to use.')
    parser.add_argument('-t', '--tests', help=('The compliance tests to run.  '
                                              'If this value is not provided, '
                                              'then all compliance tests are '
                                              'run.'), type=test_spec, nargs='+')
    parser.add_argument('-l', '--list', action="store_true",
                        help=('List the available compliance tests to run.  '
                              'These values can then be used with the '
                              '"-t/--tests" argument.  If this argument is '
                              'specified, no tests will actually be run.'))
    args = parser.parse_args()
    runner = ComplianceTestRunner(args.exe, args.tests)
    if args.list:
        display_available_tests(runner.get_compliance_test_files())
    else:
        runner.run_tests()
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
