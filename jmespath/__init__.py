import json

from jmespath import parser
from jmespath.compat import string_type
from jmespath.visitor import Options

__version__ = '1.1.0'

# Optional native accelerator (e.g. ``aero-jmespath``). When installed it exposes
# ``search(expression, json_string)`` that runs the whole parse + eval + serialize
# pipeline in native code.  ``search_json`` uses it automatically when ``data`` is
# a JSON string and falls back to pure Python otherwise, so this is purely an
# opt-in performance improvement and never changes behaviour.
_NATIVE_ACCELERATOR = None
try:
    import aero_jmespath as _accelerator
    _NATIVE_ACCELERATOR = _accelerator.search
except ImportError:
    pass


def compile(expression):
    return parser.Parser().parse(expression)


def search(expression, data, options=None):
    return parser.Parser().parse(expression).search(data, options=options)


def search_json(expression, data, options=None):
    """Search a JSON document given as a *string*.

    ``data`` must be a JSON-encoded string.  When the optional native
    accelerator (``aero-jmespath``) is installed, the expression is evaluated
    entirely in native code and the serialized result is decoded back to a
    Python value.  Otherwise this is equivalent to
    ``search(expression, json.loads(data))``.

    The return value is the same as :func:`search`.
    """
    if _NATIVE_ACCELERATOR is not None and isinstance(data, string_type):
        result = _NATIVE_ACCELERATOR(expression, data)
        # The native kernel reports errors (bad JSON, unsupported expression,
        # invalid value) as "\x1eERR<code>". Falling back to pure Python here
        # keeps exceptions identical to the non-accelerated path (ValueError
        # for bad JSON, ParseError for a bad expression).
        if not result.startswith(b"\x1eERR"):
            return json.loads(result)
    if isinstance(data, string_type):
        data = json.loads(data)
    return search(expression, data, options=options)
