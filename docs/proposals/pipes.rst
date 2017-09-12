================
Pipe Expressions
================

:JEP: 4
:Author: Michael Dowling
:Status: accepted
:Created: 07-Dec-2013

Abstract
========

This document proposes adding support for piping expressions into subsequent
expressions.

Motivation
==========

The current JMESPath grammar allows for projections at various points in an
expression. However, it is not currently possible to operate on the result of
a projection as a list.

The following example illustrates that it is not possible to operate on the
result of a projection (e.g., take the first match of a projection).

Given:

.. code-block:: json

    {
        "foo": {
            "a": {
                "bar": [1, 2, 3]
            },
            "b": {
                "bar": [4, 5, 6]
            }
        }
    }

Expression:

::

    foo.*.bar[0]

The result would be element 0 of each ``bar``:

.. code-block:: json

    [1, 4]

With the addition of filters, we could pass the result of one expression to
another, operating on the result of a projection (or any expression).

Expression:

::

    foo.*.bar | [0]

Result:

.. code-block:: json

    [1, 2, 3]
    
Not only does this give us the ability to operate on the result of a 
projection, but pipe expressions can also be useful for breaking down a complex
expression into smaller, easier to comprehend, parts.

Modified Grammar
================

The following modified JMESPath grammar supports piped expressions.

::

    expression        = sub-expression / index-expression / or-expression / identifier / "*"
    expression        =/ multi-select-list / multi-select-hash / pipe-expression
    sub-expression    = expression "." expression
    pipe-expression   = expression "|" expression
    or-expression     = expression "||" expression
    index-expression  = expression bracket-specifier / bracket-specifier
    multi-select-list = "[" ( expression *( "," expression ) ) "]"
    multi-select-hash = "{" ( keyval-expr *( "," keyval-expr ) ) "}"
    keyval-expr       = identifier ":" expression
    bracket-specifier = "[" (number / "*") "]" / "[]"
    number            = [-]1*digit
    digit             = "1" / "2" / "3" / "4" / "5" / "6" / "7" / "8" / "9" / "0"
    identifier        = 1*char
    identifier        =/ quote 1*(unescaped-char / escaped-quote) quote
    escaped-quote     = escape quote
    unescaped-char    = %x30-10FFFF
    escape            = %x5C   ; Back slash: \
    quote             = %x22   ; Double quote: '"'
    char              = %x30-39 / ; 0-9
                        %x41-5A / ; A-Z
                        %x5F /    ; _
                        %x61-7A / ; a-z
                        %x7F-10FFFF

.. _RFC4234: http://tools.ietf.org/html/rfc4234

.. note::

    ``pipe-expression`` has a higher precedent than the ``or-operator``

Compliance Tests
================

.. code-block:: json

    [{
      "given": {
        "foo": {
          "bar": {
            "baz": "one"
          },
          "other": {
            "baz": "two"
          },
          "other2": {
            "baz": "three"
          },
          "other3": {
            "notbaz": ["a", "b", "c"]
          },
          "other4": {
            "notbaz": ["d", "e", "f"]
          }
        }
      },
      "cases": [
        {
          "expression": "foo.*.baz | [0]",
          "result": "one"
        },
        {
          "expression": "foo.*.baz | [1]",
          "result": "two"
        },
        {
          "expression": "foo.*.baz | [2]",
          "result": "three"
        },
        {
          "expression": "foo.bar.* | [0]",
          "result": "one"
        },
        {
          "expression": "foo.*.notbaz | [*]",
          "result": [["a", "b", "c"], ["d", "e", "f"]]
        },
        {
          "expression": "foo | bar",
          "result": {"baz": "one"}
        },
        {
          "expression": "foo | bar | baz",
          "result": "one"
        },
        {
          "expression": "foo|bar| baz",
          "result": "one"
        },
        {
          "expression": "not_there | [0]",
          "result": null
        },
        {
          "expression": "not_there | [0]",
          "result": null
        },
        {
          "expression": "[foo.bar, foo.other] | [0]",
          "result": {"baz": "one"}
        },
        {
          "expression": "{\"a\": foo.bar, \"b\": foo.other} | a",
          "result": {"baz": "one"}
        },
        {
          "expression": "{\"a\": foo.bar, \"b\": foo.other} | b",
          "result": {"baz": "two"}
        },
        {
          "expression": "{\"a\": foo.bar, \"b\": foo.other} | *.baz",
          "result": ["one", "two"]
        },
        {
          "expression": "foo.bam || foo.bar | baz",
          "result": "one"
        },
        {
          "expression": "foo | not_there || bar",
          "result": {"baz": "one"}
        }
      ]
    }]
