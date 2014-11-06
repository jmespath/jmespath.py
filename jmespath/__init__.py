from jmespath import parser

__version__ = '0.5.0'


def compile(expression):
    return parser.Parser().parse(expression)


def search(expression, data):
    return parser.Parser().parse(expression).search(data)
