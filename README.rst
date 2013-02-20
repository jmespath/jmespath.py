JamesPath
=========

JamesPath allows you to declaratively specify how to extract
elements from a JSON document.

For example, given this document::

    {"foo": {"bar": "baz"}}

The jamespath expression "foo.bar" will return ["baz"].

Jamespath also supports:

Referencing elements in a list.  Given the data::

    {"foo": {"bar": ["one", "two"]}}

The expression: "foo.bar[0]" will return ["one"].
You can also reference all the items in a list using the '*'
syntax::

   {"foo": {"bar": [{"name": "one"}, {"name": "two"}]}}

The expression: "foo.bar[*].name" will return ["one", "two"].
Negative indexing is also supported (-1 refers to the last element
in the list).  Given the data above, the expression
"foo.bar[-1].name" will return ["two"].

The '*' can also be used for hash types::

   {"foo": {"bar": {"name": "one"}, "baz": {"name": "two"}}}

The expression: "foo.*.name" will return ["one", "two"].


Grammar
=======

::

    expression : expression '.' expression
               | expression '[' (number|star) ']
               | expression '.' star
               | identifier
    star : '*'
    identifier : [a-zA-Z_][a-zA-Z0-9']+
    number : -?[0-9]+


Testing
=======

In addition to the unit tests for the jamespath modules,
there is a ``tests/compliance`` directory that contains
.json files with test cases.  This allows other implementations
to verify they are producing the correct output.  Each json
file is grouped by feature.

Python Library
==============

The included python implementation has two convenience functions
that operate on python data structures.  You can use ``search``
and give it the jamespath expression and the data::

    >>> import jamespath
    >>> path = jamespath.search('foo.bar', {'foo': {'bar': 'baz'}})
    ['baz']

Similar to the ``re`` module, you can store the compiled expressions
and reuse them to perform repeated searches::

    >>> import jamespath
    >>> path = jamespath.compile('foo.bar')
    >>> path.search({'foo': {'bar': 'baz'}})
    ['baz']
    >>> path.search({'foo': {'bar': 'other'}})
    ['other']

You can also use the ``jamespath.parser.Parser`` class directly
if you want more control.
