==================
Filter Expressions
==================

:JEP: 7
:Author: James Saryerwinnie
:Status: accepted
:Created: 16-Dec-2013


Abstract
========

This JEP proposes grammar modifications to JMESPath to allow for filter
expressions.  A filtered expression allows list elements to be selected
based on matching expressions.  A literal expression
is also introduced (from JEP 3) so that it is possible to match elements
against literal values.


Motivation
==========

A common request when querying JSON objects is the ability to select
elements based on a specific value.  For example, given a JSON object::

    {"foo": [{"state": "WA", "value": 1},
             {"state": "WA", "value": 2},
             {"state": "CA", "value": 3},
             {"state": "CA", "value": 4}]}

A user may want to select all objects in the ``foo`` list that have
a ``state`` key of ``WA``.  There is currently no way to do this
in JMESPath.  This JEP will introduce a syntax that allows this::

    foo[?state == `WA`]

Additionally, a user may want to project additional expressions onto the values
matched from a filter expression.  For example, given the data above, select
the ``value`` key from all objects that have a ``state`` of ``WA``::

    foo[?state == `WA`].value

would return ``[1, 2]``.


Specification
=============

The updated grammar for filter expressions::

    bracket-specifier      = "[" (number / "*") "]" / "[]"
    bracket-specifier      =/ "[?" list-filter-expression "]"
    list-filter-expression = expression comparator expression
    comparator             = "<" / "<=" / "==" / ">=" / ">" / "!="
    expression             =/ literal
    literal                = "`" json-value "`"
    literal                =/ "`" 1*(unescaped-literal / escaped-literal) "`"
    unescaped-literal      = %x20-21 /       ; space !
                                %x23-5A /   ; # - [
                                %x5D-5F /   ; ] ^ _
                                %x61-7A     ; a-z
                                %x7C-10FFFF ; |}~ ...
    escaped-literal        = escaped-char / (escape %x60)

The ``json-value`` rule is any valid json value.  While it's recommended
that implementations use an existing JSON parser to parse the
``json-value``, the grammar is added below for completeness::

    json-value = "false" / "null" / "true" / json-object / json-array /
                 json-number / json-quoted-string
    json-quoted-string = %x22 1*(unescaped-literal / escaped-literal) %x22
    begin-array     = ws %x5B ws  ; [ left square bracket
    begin-object    = ws %x7B ws  ; { left curly bracket
    end-array       = ws %x5D ws  ; ] right square bracket
    end-object      = ws %x7D ws  ; } right curly bracket
    name-separator  = ws %x3A ws  ; : colon
    value-separator = ws %x2C ws  ; , comma
    ws              = *(%x20 /              ; Space
                        %x09 /              ; Horizontal tab
                        %x0A /              ; Line feed or New line
                        %x0D                ; Carriage return
                       )
    json-object = begin-object [ member *( value-separator member ) ] end-object
    member = quoted-string name-separator json-value
    json-array = begin-array [ json-value *( value-separator json-value ) ] end-array
    json-number = [ minus ] int [ frac ] [ exp ]
    decimal-point = %x2E       ; .
    digit1-9 = %x31-39         ; 1-9
    e = %x65 / %x45            ; e E
    exp = e [ minus / plus ] 1*DIGIT
    frac = decimal-point 1*DIGIT
    int = zero / ( digit1-9 *DIGIT )
    minus = %x2D               ; -
    plus = %x2B                ; +
    zero = %x30                ; 0


Comparison Operators
--------------------

The following operations are supported:

* ``==``, tests for equality.
* ``!=``, tests for inequality.
* ``<``, less than.
* ``<=``, less than or equal to.
* ``>``, greater than.
* ``>=``, greater than or equal to.

The behavior of each operation is dependent on the type of each evaluated
expression.

The comparison semantics for each operator are defined below based on
the corresponding JSON type:

Equality Operators
~~~~~~~~~~~~~~~~~~

For ``string/number/true/false/null`` types, equality is an exact match. A
``string`` is equal to another ``string`` if they they have the exact sequence
of code points.  The literal values ``true/false/null`` are only equal to their
own literal values.  Two JSON objects are equal if they have the same set
of keys (for each key in the first JSON object there exists a key with equal
value in the second JSON object).  Two JSON arrays are equal if they have
equal elements in the same order (given two arrays ``x`` and ``y``,
for each ``i`` in ``x``, ``x[i] == y[i]``).

Ordering Operators
~~~~~~~~~~~~~~~~~~

Ordering operators ``>, >=, <, <=`` are **only** valid for numbers.
Evaluating any other type with a comparison operator will yield a ``null``
value, which will result in the element being excluded from the result list.
For example, given::

    search('foo[?a<b]', {"foo": [{"a": "char", "b": "char"},
                                 {"a": 2, "b": 1},
                                 {"a": 1, "b": 2}]})

The three elements in the foo list are evaluated against ``a < b``.  The first
element resolves to the comparison ``"char" < "bar"``, and because these types
are string, the expression results in ``null``, so the first element is not
included in the result list.  The second element resolves to ``2 < 1``,
which is ``false``, so the second element is excluded from the result list.
The third expression resolves to ``1 < 2`` which evalutes to ``true``, so the
third element is included in the list.  The final result of that expression
is ``[{"a": 1, "b": 2}]``.


Filtering Semantics
-------------------

When a filter expression is matched, the matched element in its entirety is
included in the filtered response.

Using the previous example, given the following data::

    {"foo": [{"state": "WA", "value": 1},
             {"state": "WA", "value": 2},
             {"state": "CA", "value": 3},
             {"state": "CA", "value": 4}]}


The expression ``foo[?state == `WA`]`` will return the following value::

    [{"state": "WA", "value": 1}]


Literal Expressions
-------------------

Literal expressions are also added in the JEP, which is essentially a JSON
value surrounded by the "`" character.  You can escape the "`" character via
"\\`", and if the character "\`" appears in the JSON value, it must also be
escaped.  A simple two pass algorithm in the lexer could first process any
escaped "`" characters before handing the resulting string to a JSON parser.

Because string literals are by far the most common type of JSON value, an
alternate syntax is supported where the starting and ending double quotes
are not required for strings.  For example::

    `foobar`   -> "foobar"
    `"foobar"` -> "foobar"
    `123`      -> 123
    `"123"`    -> "123"
    `123.foo`  -> "123.foo"
    `true`     -> true
    `"true"`   -> "true"
    `truee`    -> "truee"

Literal expressions aren't allowed on the right hand side of a subexpression::

    foo[*].`literal`

but they are allowed on the left hand side::

    `{"foo": "bar"}`.foo

They may also be included in other expressions outside of a filter expressions.
For example::

    {value: foo.bar, type: `multi-select-hash`}


Rationale
=========

The proposed filter expression syntax was chosen such that there is sufficient
expressive power for any type of filter one might need to perform while at the
same time being as minimal as possible.  To help illustrate this, below are a
few alternate syntax that were considered.

In the simplest case where one might filter a key based on a literal value,
a possible filter syntax would be::

    foo[bar == baz]

or in general terms: ``[identifier comparator literal-value]``.  However this
has several issues:

* It is not possible to filter based on two expressions (get all elements whose
  ``foo`` key equals its ``bar`` key.
* The literal value is on the right hand side, making it hard to troubleshoot
  if the identifier and literal value are swapped: ``foo[baz == bar]``.
* Without some identifying token unary filters would not be possible as they
  would be ambiguous.  Is the expression ``[foo]`` filtering all elements with
  a foo key with a truth value or is it a multiselect-list selecting the
  ``foo`` key from each hash?  Starting a filter expression with a token such
  as ``[?`` make it clear that this is a filter expression.
* This makes the syntax for filtering against literal JSON arrays and objects
  hard to visually parse.  "Filter all elements whose ``foo`` key is a single
  list with a single integer value of 2:  ``[foo == [2]]``.
* Adding literal expressions makes them useful even outside of a filter
  expression.  For example, in a ``multi-select-hash``, you can create
  arbitrary key value pairs:  ``{a: foo.bar, b: `some string`}``.


This JEP is purposefully minimal.  There are several extensions that can be
added in future:

* Support any arbitrary expression within the ``[? ... ]``.  This would
  enable constructs such as or expressions within a filter.  This would
  allow unary expressions.

In order for this to be useful we need to define what corresponds to true and
false values, e.g. an empty list is a false value.  Additionally, "or
expressions" would need to change its semantics to branch based on the
true/false value of an expression instead of whether or not the expression
evalutes to null.

This is certainly a direction to take in the future, adding arbitrary
expressions in a filter would be a backwards compatible change, so it's not
part of this JEP.

* Allow filter expressions as top level expressions.  This would potentially
  just return ``true/false`` for any value that it matched.

This might be useful if you can combine this with something that can accept
a list to use as a mask for filtering other elements.
