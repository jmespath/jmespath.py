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

from jmespath.parser import Parser
from jmespath.lexer import LexerDefinition


DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NUM_LOOP = 100


def run_tests(tests):
    times = []
    for test in tests:
        given = test['given']
        expression = test['expression']
        lex_time = _lex_time(expression)
        parse_time = _parse_time(expression)
        search_time = _search_time(expression, given)
        sys.stdout.write(
            "lex_time: %.8f, parse_time: %.8fms, search_time: %.8fms" % (
                1000 * lex_time, 1000 * parse_time, 1000 * search_time))
        sys.stdout.write(" description: %s " % test['description'])
        sys.stdout.write("name: %s\n" % test['name'])


def _lex_time(expression):
    import ply.lex
    definitions = LexerDefinition
    create_lexer = ply.lex.lex
    best = float('inf')
    for i in range(DEFAULT_NUM_LOOP):
        start = time.time()
        lexer = create_lexer(module=definitions(),
                             debug=False,
                             reflags=definitions.reflags)
        lexer.input(expression)
        while True:
            token = lexer.token()
            if token is None:
                break
        end = time.time()
        total = end - start
        if total < best:
            best = total
    return best


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
