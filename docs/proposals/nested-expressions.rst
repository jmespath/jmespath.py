==================
Nested Expressions
==================

:JEP: 1
:Author: Michael Dowling
:Status: accepted
:Created: 27-Nov-2013

Abstract
========

This document proposes modifying the `JMESPath grammar <https://jmespath.readthedocs.io/en/latest/specification.html#grammar>`_
to support arbitrarily nested expressions within ``multi-select-list`` and
``multi-select-hash`` expressions.

Motivation
==========

This JMESPath grammar currently does not allow arbitrarily nested expressions
within ``multi-select-list`` and ``multi-select-hash`` expressions. This
prevents nested branching expressions, nested ``multi-select-list`` expressions
within other multi expressions, and nested ``or-expression``s within any
multi-expression.

By allowing any expression to be nested within a ``multi-select-list`` and
``multi-select-hash`` expression, we can trim down several grammar rules and
provide customers with a much more flexible expression DSL.

Supporting arbitrarily nested expressions within other expressions requires:

* Updating the grammar to remove ``non-branched-expr``
* Updating compliance tests to add various permutations of the grammar to
  ensure implementations are compliant.
* Updating the JMESPath documentation to reflect the ability to arbitrarily
  nest expressions.

Nested Expression Examples
==========================

Nested branch expressions
-------------------------

Given:

.. code-block:: json

    {
        "foo": {
            "baz": [
                {
                    "bar": "abc"
                }, {
                    "bar": "def"
                }
            ],
            "qux": ["zero"]
        }
    }

With: ``foo.[baz[*].bar, qux[0]]``

Result:

.. code-block:: json

    [
        [
            "abc",
            "def"
        ],
        "zero"
    ]

Nested branch expressions with nested mutli-select
--------------------------------------------------

Given:

.. code-block:: json

    {
        "foo": {
            "baz": [
                {
                    "bar": "a",
                    "bam": "b",
                    "boo": "c"
                }, {
                    "bar": "d",
                    "bam": "e",
                    "boo": "f"
                }
            ],
            "qux": ["zero"]
        }
    }

With: ``foo.[baz[*].[bar, boo], qux[0]]``

Result:

.. code-block:: json

    [
        [
            [
                "a",
                "c"
            ],
            [
                "d",
                "f"
            ]
        ],
        "zero"
    ]

Nested or expressions
---------------------

Given:

.. code-block:: json

    {
        "foo": {
            "baz": [
                {
                    "bar": "a",
                    "bam": "b",
                    "boo": "c"
                }, {
                    "bar": "d",
                    "bam": "e",
                    "boo": "f"
                }
            ],
            "qux": ["zero"]
        }
    }

With: ``foo.[baz[*].not_there || baz[*].bar, qux[0]]``

Result:

.. code-block:: json

    [
        [
            "a",
            "d"
        ],
        "zero"
    ]

No breaking changes
-------------------

Because there are no breaking changes from this modification, existing
multi-select expressions will still work unchanged:

Given:

.. code-block:: json

    {
        "foo": {
            "baz": {
                "abc": 123,
                "bar": 456
            }
        }
    }

With: ``foo.[baz, baz.bar]``

Result:

.. code-block:: json

    [
        {
            "abc": 123,
            "bar": 456
        },
        456
    ]

Modified Grammar
================

The following modified JMESPath grammar supports arbitrarily nested expressions
and is specified using ABNF, as described in `RFC4234`_

::

    expression        = sub-expression / index-expression / or-expression / identifier / "*"
    expression        =/ multi-select-list / multi-select-hash
    sub-expression    = expression "." expression
    or-expression     = expression "||" expression
    index-expression  = expression bracket-specifier / bracket-specifier
    multi-select-list = "[" ( expression *( "," expression ) ) "]"
    multi-select-hash = "{" ( keyval-expr *( "," keyval-expr ) ) "}"
    keyval-expr       = identifier ":" expression
    bracket-specifier = "[" (number / "*") "]"
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
