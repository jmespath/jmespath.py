#!/usr/bin/env python
"""Generate performance diagnostics.

The purpose of this script is to generate performance diagnostics for
various jamespath expressions to be able to track the performance
over time.  The test files are data driven similar to the
compliance tests.
"""
import argparse
import time
import os
import json
import sys

from jamespath.parser import Parser


DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NUM_LOOP = 100


def run_tests(tests):
    times = []
    for test in tests:
        given = test['given']
        expression = test['expression']
        parse_time = _parse_time(expression)
        search_time = _search_time(expression, given)
        sys.stdout.write(
            "parse_time: %.8fms, search_time: %.8fms" % (
            1000 * parse_time, 1000 * search_time))
        sys.stdout.write(" description: %s" % test['description'])
        sys.stdout.write("name: %s\n" % test['name'])


def _search_time(expression, given):
    p = Parser()
    parsed = p.parse(expression)
    best = float('inf')
    for i in range(DEFAULT_NUM_LOOP):
        start = time.time()
        parsed.search(given)
        end = time.time()
        total = end - start
        if total < best:
            best = total
    return best

def _parse_time(expression):
    best = float('inf')
    p = Parser()
    for i in range(DEFAULT_NUM_LOOP):
        p.purge()
        start = time.time()
        p.parse(expression)
        end = time.time()
        total = end - start
        if total < best:
            best = total
    return best

def load_tests(filename):
    loaded = []
    with open(filename) as f:
        data = json.load(f)
    for case in data['cases']:
        current = {'description': data['description'],
                   'given': data['given'],
                   'name': case['name'],
                   'expression': case['expression'],
                   'result': case['result']}
        loaded.append(current)
    return loaded


def main():
    parser = argparse.ArgumentParser()
    collected_tests = []
    for filename in os.listdir(DIRECTORY):
        if filename.endswith('.json'):
            collected_tests.extend(load_tests(filename))
    run_tests(collected_tests)


if __name__ == '__main__':
    main()
