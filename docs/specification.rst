======================
JMESPath Specification
======================

This document describes the specification for jmespath.
In the specification, examples are shown through the use
of a ``search`` function.  The syntax for this function is::

    search(<jmespath expr>, <JSON document>) -> <return value>

For simplicity, the jmespath expression and the JSON document are
not quoted.  For example::

    search(foo, {"foo": "bar"}) -> "bar"

In this specification, ``null`` is used as a return value whenever an
expression does not match.  ``null`` is the generic term that maps to the JSON
``null`` value.  Implementations can replace the ``null`` value with the
language equivalent value.


Grammar
=======

The grammar is specified using ABNF, as described in `RFC4234`_

::

    expression        = sub-expression / index-expression / or-expression / identifier / "*"
    expression        =/ multi-select-list / multi-select-hash / literal
    sub-expression    = expression "." expression
    or-expression     = expression "||" expression
    index-expression  = expression bracket-specifier / bracket-specifier
    multi-select-list = "[" ( expression *( "," expression ) ) "]"
    multi-select-hash = "{" ( keyval-expr *( "," keyval-expr ) ) "}"
    keyval-expr       = identifier ":" expression
    bracket-specifier = "[" (number / "*") "]" / "[]"
    bracket-specifier =/ "[?" list-filter-expr "]"
    list-filter-expr  = expression comparator expression
    comparator        = "<" / "<=" / "==" / ">=" / ">" / "!="
    literal           = "`" json-value "`"
    literal           =/ "`" 1*(unescaped-literal / escaped-literal) "`"
    unescaped-literal = %x20-21 / %x23-5B / %x5D-5F / %x61-10FFFF
    escaped-literal   = escaped-char / (escape %x60)
    number            = ["-"]1*digit
    digit             = %x30-39
    identifier        = unquoted-string / quoted-string
    unquoted-string   = (%x41-5A / %x61-7A / %x5F) *(  ; a-zA-Z_
                            %x30-39  /  ; 0-9
                            %x41-5A /  ; A-Z
                            %x5F    /  ; _
                            %x61-7A)   ; a-z
    quoted-string     = quote 1*(unescaped-char / escaped-char) quote
    unescaped-char    = %x20-21 / %x23-5B / %x5D-10FFFF
    escape            = %x5C   ; Back slash: \
    quote             = %x22   ; Double quote: '"'
    escaped-char      = escape (
                            %x22 /          ; "    quotation mark  U+0022
                            %x5C /          ; \    reverse solidus U+005C
                            %x2F /          ; /    solidus         U+002F
                            %x62 /          ; b    backspace       U+0008
                            %x66 /          ; f    form feed       U+000C
                            %x6E /          ; n    line feed       U+000A
                            %x72 /          ; r    carriage return U+000D
                            %x74 /          ; t    tab             U+0009
                            %x75 4HEXDIG )  ; uXXXX                U+XXXX

The ``json-value`` is any valid JSON value with the one exception that the
``%x60`` character must be escaped.  While it's encouraged that implementations
use any existing JSON parser for this grammar rule (after handling the escaped
literal characters), the grammar rule is shown below for completeness::


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
    member = quoted-string name-separator value
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



Identifiers
===========


::

    identifier        = unquoted-string / quoted-string
    unquoted-string   = (%x41-5A / %x61-7A / %x5F) *(  ; a-zA-Z_
                            %x30-39  /  ; 0-9
                            %x41-5A /  ; A-Z
                            %x5F    /  ; _
                            %x61-7A)   ; a-z
    quoted-string     = quote 1*(unescaped-char / escaped-char) quote
    unescaped-char    = %x20-21 / %x23-5B / %x5D-10FFFF
    escape            = %x5C   ; Back slash: \
    quote             = %x22   ; Double quote: '"'
    escaped-char      = escape (
                            %x22 /          ; "    quotation mark  U+0022
                            %x5C /          ; \    reverse solidus U+005C
                            %x2F /          ; /    solidus         U+002F
                            %x62 /          ; b    backspace       U+0008
                            %x66 /          ; f    form feed       U+000C
                            %x6E /          ; n    line feed       U+000A
                            %x72 /          ; r    carriage return U+000D
                            %x74 /          ; t    tab             U+0009
                            %x75 4HEXDIG )  ; uXXXX                U+XXXX

An ``identifier`` is the most basic expression and can be used to extract a single
element from a JSON document.  The return value for an ``identifier`` is the
value associated with the identifier.  If the ``identifier`` does not exist in
the JSON document, than a ``null`` value is returned.

From the grammar rule listed above identifiers can be one of more characters,
and must start with ``A-Za-z_``.

An identifier can also be quoted.  This is necessary when an identifier has
characters not specified in the ``unquoted-string`` grammar rule.
In this situation, an identifier is specified with a double quote, followed by
any number of ``unescaped-char`` or ``escaped-char`` characters, followed by a
double quote.  The ``quoted-string`` rule is the same grammar rule as a JSON
string, so any valid string can be used between double quoted, include JSON
supported escape sequences, and six character unicode escape sequences.

Note that any identifier that does not start with ``A-Za-z_`` **must**
be quoted.


Examples
--------

::

   search(foo, {"foo": "value"}) -> "value"
   search(bar, {"foo": "value"}) -> null
   search(foo, {"foo": [0, 1, 2]}) -> [0, 1, 2]
   search("with space", {"with space": "value"}) -> "value"
   search("special chars: !@#", {"special chars: !@#": "value"}) -> "value"
   search("quote\"char", {"quote\"char": "value"}) -> "value"
   search("\u2713", {"\u2713": "value"}) -> "value"


SubExpressions
==============

::

  sub-expression    = expression "." expression

A subexpression is a combination of two expressions separated by the '.' char.
A subexpression is evaluted as follows:

* Evaluate the expression on the left with the original JSON document.
* Evaluate the expression on the right with the result of the left expression
  evaluation.

In pseudocode::

  left-evaluation = search(left-expression, original-json-document)
  result = search(right-expression, left-evaluation)


A subexpression is itself an expression, so there can be multiple levels of
subexpressions: ``grandparent.parent.child``.


Examples
--------

Given a JSON document: ``{"foo": {"bar": "baz"}}``, and a jmespath expression:
``foo.bar``, the evaluation process would be::

  left-evaluation = search("foo", {"foo": {"bar": "baz"}}) -> {"bar": "baz"}
  result = search("bar": {"bar": "baz"}) -> "baz"

The final result in this example is ``"baz"``.

Additional examples::

   search(foo.bar, {"foo": {"bar": "value"}}) -> "value"
   search(foo.bar, {"foo": {"baz": "value"}}) -> null
   search(foo.bar.baz, {"foo": {"bar": {"baz": "value"}}}) -> "value"


Index Expressions
=================

::

  index-expression  = expression bracket-specifier / bracket-specifier
  bracket-specifier = "[" (number / "*") "]" / "[]"

An index expression is used to access elements in a list.  Indexing is 0 based,
the index of 0 refers to the first element of the list.  A negative number is a
valid index.  A negative number indicates that indexing is relative to the end
of the list, specifically::

  negative-index == (length of array) + negative-index

Given an array of length ``N``, an index of ``-1`` would be equal to a positive
index of ``N - 1``, which is the last element of the list.  If an index
expression refers to an index that is greater than the length of the array, a
value of ``null`` is returned.

For the grammar rule ``expression bracket-specifier`` the ``expression`` is
first evaluated, and then return value from the ``expression`` is given as
input to the ``bracket-specifier``.

Using a "*" character within a ``bracket-specifier`` is discussed below in the
``wildcard expressions`` section.

Flatten Operator
----------------

When the character sequence ``[]`` is provided as a bracket specifier, then
a flattening operation occurs on the current result.  The flattening operator
will merge sublists in the current result into a single list.  The flattening
operator has the following semantics:

* Create an empty result list.
* Iterate over the elements of the current result.
* If the current element is not a list, add to the end of the result list.
* If the current element is a list, add each element of the current element
  to the end of the result list.
* The result list is now the new current result.

Once the flattening operation has been performed, subsequent operations
are projected onto the flattened list with the same semantics as a
wildcard expression.  Thus the difference between ``[*]`` and ``[]`` is that
``[]`` will first flatten sublists in the current result.


Examples
--------

::

  search([0], ["first", "second", "third"]) -> "first"
  search([-1], ["first", "second", "third"]) -> "third"
  search([100], ["first", "second", "third"]) -> null
  search(foo[0], {"foo": ["first", "second", "third"]) -> "first"
  search(foo[100], {"foo": ["first", "second", "third"]) -> null
  search(foo[0][0], {"foo": [[0, 1], [1, 2]]}) -> 0


Or Expressions
==============

::

  or-expression     = expression "||" expression

An or expression will evaluate to either the left expression or the right
expression.  If the evaluation of the left expression is not null it is used as
the return value.  If the evaluation of the right expression is not null it is
used as the return value.  If neither the left or right expression are
non-null, then a value of null is returned.

Examples
--------

::

  search(foo || bar, {"foo": "foo-value"}) -> "foo-value"
  search(foo || bar, {"bar": "bar-value"}) -> "bar-value"
  search(foo || bar, {"foo": "foo-value", "bar": "bar-value"}) -> "foo-value"
  search(foo || bar, {"baz": "baz-value"}) -> null
  search(foo || bar || baz, {"baz": "baz-value"}) -> "baz-value"
  search(override || mylist[-1], {"mylist": ["one", "two"]}) -> "two"
  search(override || mylist[-1], {"mylist": ["one", "two"], "override": "yes"}) -> "yes"


MultiSelect List
================

::

    multi-select-list = "[" ( expression *( "," expression ) "]"

A multiselect expression is used to extract a subset of elements from a JSON
hash.  There are two version of multiselect, one in which the multiselect
expression is enclosed in ``{...}`` and one which is enclosed in ``[...]``.
This section describes the ``[...]`` version.  Within the start and closing
characters is one or more non expressions separated by a comma.  Each
expression will be evaluated against the JSON document.  Each returned element
will be the result of evaluating the expression. A ``multi-select-list`` with
``N`` expressions will result in a list of length ``N``.  Given a multiselect
expression ``[expr-1,expr-2,...,expr-n]``, the evaluated expression will return
``[evaluate(expr-1), evaluate(expr-2), ..., evaluate(expr-n)]``.

Examples
--------

::

  search([foo,bar], {"foo": "a", "bar": "b", "baz": "c"}) -> ["a", "b"]
  search([foo,bar[0]], {"foo": "a", "bar": ["b"], "baz": "c"}) -> ["a", "b"]
  search([foo,bar.baz], {"foo": "a", "bar": {"baz": "b"}}) -> ["a", "b"]
  search([foo,baz], {"foo": "a", "bar": "b"}) -> ["a", null]


MultiSelect Hash
================

::

    multi-select-hash = "{" ( keyval-expr *( "," keyval-expr ) "}"
    keyval-expr       = identifier ":" expression

A ``multi-select-hash`` expression is similar to a ``multi-select-list``
expression, except that a hash is created instead of a list.  A
``multi-select-hash`` expression also requires key names to be provided, as
specified in the ``keyval-expr`` rule.  Given the following rule::

    keyval-expr       = identifier ":" expression

The ``identifier`` is used as the key name and the result of evaluating the
``expression`` is the value associated with the ``identifier`` key.

Each ``keyval-expr`` within the ``multi-select-hash`` will correspond to a
single key value pair in the created hash.


Examples
--------

Given a ``multi-select-hash`` expression ``{foo: one.two, bar: bar}`` and the
data ``{"bar": "bar", {"one": {"two": "one-two"}}}``, the expression is
evaluated as follows:

1. A hash is created: ``{}``
2. A key ``foo`` is created whose value is the result of evaluating ``one.two``
   against the provided JSON document: ``{"foo": evaluate(one.two, <data>)}``
3. A key ``bar`` is created whose value is the result of evaluting the
   expression ``bar`` against the provided JSON document.

The final result will be: ``{"foo": "one-two", "bar": "bar"}``.

Additional examples:

::

  search({foo: foo, bar: bar}, {"foo": "a", "bar": "b", "baz": "c"})
                -> {"foo": "a", "bar": "b"}
  search({foo: foo, firstbar: bar[0]}, {"foo": "a", "bar": ["b"]})
                -> {"foo": "a", "firstbar": "b"}
  search({foo: foo, "bar.baz": bar.baz}, {"foo": "a", "bar": {"baz": "b"}})
                -> {"foo": "a", "bar.baz": "b"}
  search({foo: foo, baz: baz}, {"foo": "a", "bar": "b"})
                -> {"foo": "a", "bar": null}


Wildcard Expressions
====================

::

    expression        =/ "*"
    bracket-specifier = "[" "*" "]"

A wildcard expression is a expression of either ``*`` or ``[*]``.  A wildcard
expression can return multiple elements, and the remaining expressions are
evaluated against each returned element from a wildcard expression.  The
``[*]`` syntax applies to a list type and the ``*`` syntax applies to a hash
type.

The ``[*]`` syntax (referred to as a list wildcard expression) will return all
the elements in a list.  Any subsequent expressions will be evaluated against
each individual element.  Given an expression ``[*].child-expr``, and a list of
N elements, the evaluation of this expression would be ``[child-expr(el-0),
child-expr(el-2), ..., child-expr(el-N)]``.  This is referred to as a
**projection**, and the ``child-expr`` expression is projected onto the
elements of the resulting list.

Once a projection has been created, all subsequent expressions are projected
onto the resulting list.

The ``*`` syntax (referred to as a hash wildcard expression) will return a list
of the hash element's values.  Any subsequent expression will be evaluated
against each individual element in the list (this is also referred to as a
**projection**).

Note that if any subsequent expression after a wildcard expression returns a
``null`` value, it is omitted from the final result list.

A list wildcard expression is only valid for the JSON array type.  If a list
wildcard expression is applied to any other JSON type, a value of ``null`` is
returned.

Similarly, a hash wildcard expression is only valid for the JSON object type.
If a hash wildcard expression is applied to any other JSON type, a value of
``null`` is returned.

Examples
--------

::

  search([*].foo, [{"foo": 1}, {"foo": 2}, {"foo": 3}]) -> [1, 2, 3]
  search([*].foo, [{"foo": 1}, {"foo": 2}, {"bar": 3}]) -> [1, 2]
  search('*.foo', {"a": {"foo": 1}, "b": {"foo": 2}, "c": {"bar": 1}}) -> [1, 2]


.. _RFC4234: http://tools.ietf.org/html/rfc4234
