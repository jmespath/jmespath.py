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
import timeit

_clock = timeit.default_timer


from jmespath.parser import Parser
from jmespath.lexer import Lexer


BENCHMARK_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'tests',
    'compliance',
    'benchmarks.json')
APPROX_RUN_TIME = 0.5


def run_tests(tests):
    times = []
    for test in tests:
        given = test['given']
        expression = test['expression']
        result = test['result']
        should_search = test['bench_type'] == 'full'
        lex_time = _lex_time(expression)
        parse_time = _parse_time(expression)
        if should_search:
            search_time = _search_time(expression, given)
            combined_time = _combined_time(expression, given, result)
        else:
            search_time = 0
            combined_time = 0
        sys.stdout.write(
            "lex_time: %10.5fus, parse_time: %10.5fus, search_time: %10.5fus "
            "combined_time: %10.5fus " % (1000000 * lex_time,
                                          1000000 * parse_time,
                                          1000000 * search_time,
                                          1000000 * combined_time))
        sys.stdout.write("name: %s\n" % test['name'])


def _lex_time(expression, clock=_clock):
    lex = Lexer()
    duration = 0
    i = 0
    while True:
        i += 1
        start = clock()
        list(lex.tokenize(expression))
        end = clock()
        total = end - start
        duration += total
        if duration >= APPROX_RUN_TIME:
            break
    return duration / i


def _search_time(expression, given, clock=_clock):
    p = Parser()
    parsed = p.parse(expression)
    duration =  0
    i = 0
    while True:
        i += 1
        start = clock()
        parsed.search(given)
        end = clock()
        total = end - start
        duration += total
        if duration >= APPROX_RUN_TIME:
            break
    return duration / i


def _parse_time(expression, clock=_clock):
    best = float('inf')
    p = Parser()
    duration = 0
    i = 0
    while True:
        i += 1
        p.purge()
        start = clock()
        p.parse(expression)
        end = clock()
        total = end - start
        duration += total
        if duration >= APPROX_RUN_TIME:
            break
    return duration / i


def _combined_time(expression, given, result, clock=_clock):
    best = float('inf')
    p = Parser()
    duration = 0
    i = 0
    while True:
        i += 1
        p.purge()
        start = clock()
        r = p.parse(expression).search(given)
        end = clock()
        total = end - start
        if r != result:
            raise RuntimeError("Unexpected result, received: %s, "
                               "expected: %s" % (r, result))
        duration += total
        if duration >= APPROX_RUN_TIME:
            break
    return duration / i


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
        current = {
            'given': data['given'],
            'name': case.get('comment', case['expression']),
            'expression': case['expression'],
            'result': case.get('result'),
            'bench_type': case['bench'],
        }
        loaded.append(current)
    return loaded


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--filename', default=BENCHMARK_FILE)
    args = parser.parse_args()
    collected_tests = []
    collected_tests.extend(load_tests(args.filename))
    run_tests(collected_tests)


if __name__ == '__main__':
    main()
