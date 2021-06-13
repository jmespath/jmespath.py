import argparse
import json
import os
import pprint
import sys

import jmespath

__version__ = "VERSION"
__project__ = "jpipe"
__description__ = "A python implementation of the jp CLI for JMESPath"
__author__ = "Zac Medico"
__email__ = "<zmedico@gmail.com>"
__classifiers__ = (
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: POSIX",
    "Programming Language :: Python :: 3",
    "Programming Language :: Unix Shell",
)
__copyright__ = "Copyright 2021 Zac Medico"
__license__ = "Apache-2.0"
__url__ = "https://github.com/pipebus/jpipe"
__project_urls__ = (("Bug Tracker", "https://github.com/pipebus/jpipe/issues"),)


# This 2 space indent matches https://github.com/jmespath/jp behavior.
JP_COMPAT_DUMP_KWARGS = (
    ("indent", 2),
    ("ensure_ascii", False),
)


def jpipe_main(argv=None):
    argv = sys.argv if argv is None else argv
    parser = argparse.ArgumentParser(
        prog=os.path.basename(argv[0]),
    )
    parser.add_argument("expression", nargs="?", default=None)
    parser.add_argument(
        "-e",
        "--expr-file",
        dest="expr_file",
        default=None,
        help=(
            "Read JMESPath expression from the specified file."
        ),
    )
    parser.add_argument(
        "-f",
        "--filename",
        dest="filename",
        default=None,
        help=(
            "The filename containing the input data. "
            "If a filename is not given then data is "
            "read from stdin."
        ),
    )
    parser.add_argument(
        "-u",
        "--unquoted",
        action="store_false",
        dest="quoted",
        default=True,
        help=(
            "If the final result is a string, it will be printed without quotes."
        ),
    )
    parser.add_argument(
        "--ast",
        action="store_true",
        help=("Only print the AST of the parsed expression.  Do not rely on this output, only useful for debugging purposes."),
    )
    parser.usage = "{}\n  {} - {}".format(parser.format_usage().partition("usage: ")[-1], __project__, __description__)

    args = parser.parse_args(argv[1:])
    expression = args.expression
    if expression == "help":
        parser.print_help()
        return 1

    if expression and args.expr_file:
        parser.error("Only use one of the expression or --expr-file arguments.")

    if args.expr_file:
        with open(args.expr_file, "rt") as f:
            expression = f.read()

    if args.ast:
        # Only print the AST
        expression = jmespath.compile(args.expression)
        sys.stdout.write(pprint.pformat(expression.parsed))
        sys.stdout.write("\n")
        return 0
    if args.filename:
        with open(args.filename, "rt") as f:
            data = json.load(f)
    else:
        data = sys.stdin.read()
        data = json.loads(data)

    result = jmespath.search(expression, data)
    if args.quoted or not isinstance(result, str):
        result = json.dumps(result, **dict(JP_COMPAT_DUMP_KWARGS))

    sys.stdout.write(result)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(jpipe_main(argv=sys.argv))
