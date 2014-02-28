from jmespath import parser

__version__ = '0.3.0'


def compile(expression, debug=False):
    return parser.Parser(debug=debug).parse(expression)


def search(expression, data, debug=False):
    return parser.Parser(debug=debug).parse(expression).search(data)
