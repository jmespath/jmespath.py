# Test suite using hypothesis to generate test cases.
# This is in a standalone module so that these tests
# can a) be run separately and b) allow for customization
# via env var for longer runs in travis.
import os
import sys
import numbers

from nose.plugins.skip import SkipTest
from hypothesis import given, settings, assume, HealthCheck
import hypothesis.strategies as st

from jmespath import lexer
from jmespath import parser
from jmespath import exceptions
from jmespath.functions import Functions


if sys.version_info[:2] == (2, 6):
    raise RuntimeError("Hypothesis tests are not supported on python2.6. "
                       "Use python2.7, or python3.3 and greater.")


JSON_NUMBERS = (st.integers() | st.floats(allow_nan=False,
                                          allow_infinity=False))

RANDOM_JSON = st.recursive(
    JSON_NUMBERS | st.booleans() | st.text() | st.none(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children)
)

MAX_EXAMPLES = int(os.environ.get('JP_MAX_EXAMPLES', 1000))
BASE_SETTINGS = {
    'max_examples': MAX_EXAMPLES,
    'suppress_health_check': [HealthCheck.too_slow,
                              HealthCheck.filter_too_much,
                              HealthCheck.data_too_large],
}


# For all of these tests they verify these properties:
# either the operation succeeds or it raises a JMESPathError.
# If any other exception is raised then we error out.
@settings(**BASE_SETTINGS)
@given(st.text())
def test_lexer_api(expr):
    try:
        tokens = list(lexer.Lexer().tokenize(expr))
    except exceptions.EmptyExpressionError:
        return
    except exceptions.LexerError as e:
        assert e.lex_position >= 0, e.lex_position
        assert e.lex_position < len(expr), e.lex_position
        if expr:
            assert expr[e.lex_position] == e.token_value[0], (
                "Lex position does not match first token char.\n"
                "Expression: %s\n%s != %s" % (expr, expr[e.lex_position],
                                              e.token_value[0])
            )
        return
    except Exception as e:
        raise AssertionError("Non JMESPathError raised: %s" % e)
    assert isinstance(tokens, list)
    # Token starting positions must be unique, can't have two
    # tokens with the same start position.
    start_locations = [t['start'] for t in tokens]
    assert len(set(start_locations)) == len(start_locations), (
        "Tokens must have unique starting locations.")
    # Starting positions must be increasing (i.e sorted).
    assert sorted(start_locations) == start_locations, (
        "Tokens must have increasing start locations.")
    # Last token is always EOF.
    assert tokens[-1]['type'] == 'eof'


@settings(**BASE_SETTINGS)
@given(st.text())
def test_parser_api_from_str(expr):
    # Same a lexer above with the assumption that we're parsing
    # a valid sequence of tokens.
    try:
        list(lexer.Lexer().tokenize(expr))
    except exceptions.JMESPathError as e:
        # We want to try to parse things that tokenize
        # properly.
        assume(False)
    try:
        ast = parser.Parser().parse(expr)
    except exceptions.JMESPathError as e:
        return
    except Exception as e:
        raise AssertionError("Non JMESPathError raised: %s" % e)
    assert isinstance(ast.parsed, dict)
    assert 'type' in ast.parsed
    assert 'children' in ast.parsed
    assert isinstance(ast.parsed['children'], list)


@settings(**BASE_SETTINGS)
@given(expr=st.text(), data=RANDOM_JSON)
def test_search_api(expr, data):
    try:
        ast = parser.Parser().parse(expr)
    except exceptions.JMESPathError as e:
        # We want to try to parse things that tokenize
        # properly.
        assume(False)
    try:
        ast.search(data)
    except exceptions.JMESPathError as e:
        return
    except Exception as e:
        raise AssertionError("Non JMESPathError raised: %s" % e)


# Additional property tests for functions.

@given(arg=JSON_NUMBERS)
def test_abs(arg):
    assert Functions().call_function('abs', [arg]) >= 0


@given(arg=st.lists(JSON_NUMBERS))
def test_avg(arg):
    result = Functions().call_function('avg', [arg])
    if result is not None:
        assert isinstance(result, numbers.Number)


@given(arg=st.lists(st.floats() | st.booleans() | st.text() | st.none(),
                    min_size=1))
def test_not_null(arg):
    result = Functions().call_function('not_null', arg)
    if result is not None:
        assert result in arg


@given(arg=RANDOM_JSON)
def test_to_number(arg):
    result = Functions().call_function('to_number', [arg])
    if result is not None:
        assert isinstance(result, numbers.Number)
