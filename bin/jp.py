#!/usr/bin/env python

import sys
import json
import argparse

import jmespath
from jmespath.parser import ParseError, ArityError
from jmespath.lexer import LexerError
from jmespath.ast import JMESPathTypeError, UnknownFunctionError
from jmespath.compat import OrderedDict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('expression')
    parser.add_argument('-o', '--ordered', action='store_true',
                        help='Preserve the order of hash keys, which '
                             'are normally unordered.')
    parser.add_argument('-f', '--filename',
                        help=('The filename containing the input data.  '
                              'If a filename is not given then data is '
                              'read from stdin.'))
    args = parser.parse_args()
    expression = args.expression
    if args.filename:
        with open(args.filename, 'r') as f:
            data = json.load(f)
    else:
        data = sys.stdin.read()
        if args.ordered:
            data = json.loads(data, object_pairs_hook=OrderedDict)
        else:
            data = json.loads(data)
    try:
        sys.stdout.write(json.dumps(
            jmespath.search(expression, data), indent=4))
        sys.stdout.write('\n')
    except ArityError as e:
        sys.stderr.write("invalid-arity: %s\n" % e)
        return 1
    except JMESPathTypeError as e:
        sys.stderr.write("invalid-type: %s\n" % e)
        return 1
    except UnknownFunctionError as e:
        sys.stderr.write("unknown-function: %s\n" % e)
        return 1
    except ParseError as e:
        sys.stderr.write("syntax-error: %s\n" % e)
        return 1
    except LexerError as e:
        sys.stderr.write("syntax-error: %s\n" % e)
        return 1


if __name__ == '__main__':
    sys.exit(main())
