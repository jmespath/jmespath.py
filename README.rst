JMESPath
========

JMESPath (pronounced "jaymz path") allows you to declaratively specify how to
extract elements from a JSON document.

For example, given this document::

    {"foo": {"bar": "baz"}}

The jmespath expression ``foo.bar`` will return "baz".

JMESPath also supports:

Referencing elements in a list.  Given the data::

    {"foo": {"bar": ["one", "two"]}}

The expression: ``foo.bar[0]`` will return "one".
You can also reference all the items in a list using the ``*``
syntax::

   {"foo": {"bar": [{"name": "one"}, {"name": "two"}]}}

The expression: ``foo.bar[*].name`` will return ["one", "two"].
Negative indexing is also supported (-1 refers to the last element
in the list).  Given the data above, the expression
``foo.bar[-1].name`` will return ["two"].

The ``*`` can also be used for hash types::

   {"foo": {"bar": {"name": "one"}, "baz": {"name": "two"}}}

The expression: ``foo.*.name`` will return ["one", "two"].

**NOTE: jmespath is being actively developed.  There are a number
of features it does not currently support that may be added in the
future.**


Grammar
=======

The grammar is specified using ABNF, as described in `RFC4234`_

::

    expression        = sub-expression / index-expression / or-expression / identifier / "*"
    sub-expression    = expression "." expression
    or-expression     = expression "||" expression
    index-expression  = expression bracket-specifier / bracket-specifier
    bracket-specifier = "[" (number / "*") "]"
    number            = [-]1*digit
    digit             = "1" / "2" / "3" / "4" / "5" / "6" / "7" / "8" / "9" / "0"
    identifier        = 1*char
    char              = unescaped /
                        escape (
                            %x20-2F /    ; Space,!,",#,$,%,&,',(,),*,+,comma,-,.,/
                            %x3A-40 /    ; :,;,<,=,>,?,@
                            %x5B    /    ; Left bracket: [
                            %x5C    /    ; Back slash: \
                            %x5D    /    ; Right bracket: ]
                            %x5E    /    ; Caret: ^
                            %x60    /    ; Backtick: `
                            %x7B-7E /    ; {,|,},~
                            b       /    ; backspace
                            n       /    ; new line
                            f       /    ; form feed
                            r       /    ; carriage return
                            t       )    ; tab
    escape            = %x5C   ; Back slash: \
    unescaped         = %x30-39 / %x41-5A / %x5F / %x61-7A / %x7F-10FFFF


Testing
=======

In addition to the unit tests for the jmespath modules,
there is a ``tests/compliance`` directory that contains
.json files with test cases.  This allows other implementations
to verify they are producing the correct output.  Each json
file is grouped by feature.

Python Library
==============

The included python implementation has two convenience functions
that operate on python data structures.  You can use ``search``
and give it the jmespath expression and the data::

    >>> import jmespath
    >>> path = jmespath.search('foo.bar', {'foo': {'bar': 'baz'}})
    'baz'

Similar to the ``re`` module, you can store the compiled expressions
and reuse them to perform repeated searches::

    >>> import jmespath
    >>> path = jmespath.compile('foo.bar')
    >>> path.search({'foo': {'bar': 'baz'}})
    'baz'
    >>> path.search({'foo': {'bar': 'other'}})
    'other'

You can also use the ``jmespath.parser.Parser`` class directly
if you want more control.


.. _RFC4234: http://tools.ietf.org/html/rfc4234
