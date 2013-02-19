JamesPath
=========

JamesPath allows you to declaratively specify how to extract
elements from a JSON document.

The python API operates directly on python data structures::

    >>> import jamespath
    >>> d = {'foo': {'bar': 'bar'}}
    >>> jamespath.search('foo.bar', d)
    ['bar']

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

Testing
=======

In addition to the unit tests for the jamespath modules,
there is a ``tests/compliance`` directory that contains
.json files with test cases.  This allows other implementations
to verify they are producing the correct output.  Each json
file is grouped by feature.
