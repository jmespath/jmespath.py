from jmespath import parser

__version__ = '0.3.1'


def compile(expression):
    return parser.Parser().parse(expression)


def search(expression, data):
    return parser.Parser().parse(expression).search(data)
