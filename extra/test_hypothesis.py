# Test suite using hypothesis to generate test cases.
# This is in a standalone module so that these tests
# can a) be run separately and b) allow for customization
# via env var for longer runs in travis.
import os
import sys

from nose.plugins.skip import SkipTest
from hypothesis import given, settings, assume, HealthCheck
import hypothesis.strategies as st

from jmespath import lexer
from jmespath import parser
from jmespath import exceptions


if sys.version_info[:2] == (2, 6):
    raise RuntimeError("Hypothesis tests are not supported on python2.6. "
                       "Use python2.7, or python3.3 and greater.")


RANDOM_JSON = st.recursive(
    st.floats() | st.booleans() | st.text() | st.none(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children)
)


MAX_EXAMPLES = int(os.environ.get('JP_MAX_EXAMPLES', 1000))
BASE_SETTINGS = {
    'max_examples': MAX_EXAMPLES,
    'suppress_health_check': [HealthCheck.too_slow],
}


# For all of these tests they verify these proprties:
# either the operation succeeds or it raises a JMESPathError.
# If any other exception is raised then we error out.
@settings(**BASE_SETTINGS)
@given(st.text())
def test_lexer_api(expr):
    try:
        tokens = list(lexer.Lexer().tokenize(expr))
    except exceptions.JMESPathError as e:
        return
    except Exception as e:
        raise AssertionError("Non JMESPathError raised: %s" % e)
    assert isinstance(tokens, list)


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
