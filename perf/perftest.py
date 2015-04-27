#!/usr/bin/env python
"""Generate performance diagnostics.

The purpose of this script is to generate performance diagnostics for
various jmespath expressions to be able to track the performance
over time.  The test files are data driven similar to the
compliance tests.
"""
import argparse
import time
import os
import json
import sys

try:
    _clock = time.process_time
except AttributeError:
    # Python 2.x does not have time.process_time
    _clock = time.clock


from jmespath.parser import Parser
from jmespath.lexer import Lexer


DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cases')
DEFAULT_NUM_LOOP = 100


def run_tests(tests):
    times = []
    for test in tests:
        given = test['given']
        expression = test['expression']
        result = test['result']
        lex_time = _lex_time(expression)
        parse_time = _parse_time(expression)
        search_time = _search_time(expression, given)
        combined_time = _combined_time(expression, given, result)
        sys.stdout.write(
            "lex_time: %.5fms, parse_time: %.5fms, search_time: %.5fms "
            "combined_time: %.5fms " % (1000 * lex_time,
                                        1000 * parse_time,
                                        1000 * search_time,
                                        1000 * combined_time))
        sys.stdout.write("name: %s\n" % test['name'])


def _lex_time(expression, clock=_clock):
    best = float('inf')
    lex = Lexer()
    for i in range(DEFAULT_NUM_LOOP):
        start = clock()
        list(lex.tokenize(expression))
        end = clock()
        total = end - start
        if total < best:
            best = total
    return best


def _search_time(expression, given, clock=_clock):
    p = Parser()
    parsed = p.parse(expression)
    best = float('inf')
    for i in range(DEFAULT_NUM_LOOP):
        start = clock()
        parsed.search(given)
        end = clock()
        total = end - start
        if total < best:
            best = total
    return best


def _parse_time(expression, clock=_clock):
    best = float('inf')
    p = Parser()
    for i in range(DEFAULT_NUM_LOOP):
        p.purge()
        start = clock()
        p.parse(expression)
        end = clock()
        total = end - start
        if total < best:
            best = total
    return best


def _combined_time(expression, given, result, clock=_clock):
    best = float('inf')
    p = Parser()
    for i in range(DEFAULT_NUM_LOOP):
        p.purge()
        start = clock()
        r = p.parse(expression).search(given)
        end = clock()
        total = end - start
        if r != result:
            raise RuntimeError("Unexpected result, received: %s, "
                               "expected: %s" % (r, result))
        if total < best:
            best = total
    return best


def load_tests(filename):
    loaded = []
    with open(filename) as f:
        data = json.load(f)
    if isinstance(data, list):
        for i, d in enumerate(data):
            _add_cases(d, loaded, '%s-%s' % (filename, i))
    else:
        _add_cases(data, loaded, filename)
    return loaded


def _add_cases(data, loaded, filename):
    for case in data['cases']:
        current = {'description': data.get('description', filename),
                   'given': data['given'],
                   'name': case.get('name', case['expression']),
                   'expression': case['expression'],
                   'result': case.get('result')}
        loaded.append(current)
    return loaded


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory', default=DIRECTORY)
    parser.add_argument('-f', '--filename')
    args = parser.parse_args()
    collected_tests = []
    if args.filename:
        collected_tests.extend(load_tests(args.filename))
    else:
        for filename in os.listdir(args.directory):
            if filename.endswith('.json'):
                full_path = os.path.join(args.directory, filename)
                collected_tests.extend(load_tests(full_path))
    run_tests(collected_tests)


if __name__ == '__main__':
    main()
