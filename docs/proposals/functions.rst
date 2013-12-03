=========
Functions
=========

:JEP: 3
:Author: Michael Dowling
:Status: Draft
:Created: 27-Nov-2013

Abstract
========

This document proposes modifying the `JMESPath grammar <http://jmespath.readthedocs.org/en/latest/specification.html#grammar>`_
to support function expressions.

Motivation
==========

Functions allow users to easily transform and filter data in JMESPath
expressions. As JMESPath is currently implemented, functions would be very useful
in ``multi-select-list`` and ``multi-select-hash`` expressions to format the
output of an expression to contain data that might not have been in the
original JSON input. If filtered projections are added to JMESPath, functions
would be a powerful mechanism to perform any kind of special comparisons for
things like ``length()``, ``matches()``, ``substring()``, etc.

Data Types
==========

In order to support functions, we must define a type system. Because JMESPath
is a JSON DSL, we will use JSON types:

* Number (integers and double-precision floating-point format in JavaScript)
* String
* Boolean (``true`` or ``false``)
* Array (an ordered, sequence of values)
* Object (an unordered, comma-separated collection of key:value pairs)
* null

Syntax Changes
==============

Functions may be used to start any expression, including but not limited to the
root of an expression, inside of a ``multi-select`` expression, or at the start
of an ``or-expression``.

The function grammar will require the following grammar additions:

::

    function-expression = identifier "(" *(function-arg *("," function-arg ) ) ")"
    function-arg        = expression / primitive
    primitive           = "null" / "true" / "false"

``expression`` will need to be updated to add the ``current-node`` grammar:

::

    expression        = sub-expression / index-expression / or-expression / identifier / "*"
    expression        =/ multi-select-list / multi-select-hash
    expression        =/ function-expression / current-node
    current-node      = "@"

A function can accept any number of arguments, and each argument can be an
expression or primitive.

primitive
---------

With the addition of primitives, ``true``, ``false``, and ``null`` will now be
tokenized as primitive tokens. These tokens represent the JavaScript primitives
of ``true``, ``false``, and ``null``. A quoted primitive remains an identifier
(e.g., ``"true"`` will continue to be an ``identifier`` String token).

current-node
------------

The ``current-node`` token is used to represent the current node being
evaluated. When passing arguments to a function, arguments are only treated as
JMESPath expressions if the argument begins with the ``current-node`` (``@``)
token. The usage of the ``current-node`` token means that any tokens after the
current node being evaluated are considered JMESPath expressions that traverse
the current node.

current-node state
~~~~~~~~~~~~~~~~~~

At the start of an expression, the value of the current node is the data
being evaluated by the JMESPath expression. As an expression is evaluated, the
value the the current node represents MUST change to reflect the node currently
being evaluated. When in a projection, the current node value MUST be changed
to the node currently being evaluated by the projection.

``current-node`` and function arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If an argument is passed to a function that does not start with the
``current-node`` token, then argument is treated as a scalar expression.

Given the following expression:

    foo(true, abc)

The ``foo`` function is invoked and is passed a primitive ``true`` value and a
scalar string "abc".

When an argument is prefixed with the ``current-node`` token ``@``, the
argument passed to the function will be the result of an expression.

    foo(true, @.abc)

In the above example, the function is passed two arguments: a primitive value
``true`` and the result of grabbing the ``abc`` key of the current node being
evaluated.

Truthy vs Falsey Values
=======================

Some of these built-in functions (e.g., ``get``) evaluate arguments to
determine if they are "truthy" or "falsey". In order to discourage
inconsistencies in the language in future JEPs, this JEP formally defines
"truthy" and "falsey" values.

Falsey
------

"Falsey" is defined using the following semantics:

1. Boolean false
2. Empty string
3. ``null``
4. Empty Array
5. Empty Object

Truthy
------

"Truthy" is defined using the following semantics:

1. Boolean true
2. A string with one or more characters
3. An Array with one or more elements
4. An Object with one or more key value pairs
5. Any Number value, including 0

Built-in functions
==================

JMESPath will ship with various built-in functions that operate on different
data types. Functions can have a required arity or be variadic with a minimum
number of arguments.

.. note::

    All String related functions are defined on the basis of Unicode code points; they do not take collations into account.

String functions
----------------

concat
~~~~~~

::

    String|null concat(String|Number $string1, String|Number $string2 [, String|Number $... ])

Returns each argument concatenated one after the other.

Any argument that is not a String or Number is excluded from the concatenated
result. If no arguments are Strings or Numbers, this function MUST return
``null``.

.. list-table:: Examples
   :header-rows: 1

   * - Expression
     - Result
   * - ``concat(a, b)``
     - "ab"
   * - ``concat(a, b, c)``
     - "abc"
   * - ``concat(a, b, 1)``
     - "ab1"
   * - ``concat(a, false, b)``
     - "ab"
   * - ``concat(true, false)``
     - ``null``
   * - ``concat(a)``
     - raises an error because the function requires at least two arguments

.. _length:

length
~~~~~~

::

    Number|null length(String|Array|Object $subject)

Returns the length of the given argument using the following types rules:

1. String: returns the number of characters in the String
2. Array: returns the number of elements in the Array
3. Object: returns the number of key-value pairs in the Object
4. Boolean, null: returns null

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - n/a
     - ``length(abc)``
     - 3
   * - n/a
     - ``length("abc")``
     - 3
   * - "current"
     - ``length(@)``
     - 7
   * - "current"
     - ``length(@.not_there)``
     - ``null``
   * - n/a
     - ``length(false)``
     - ``null``
   * - n/a
     - ``length(10)``
     - ``null``
   * - n/a
     - ``length()``
     - Raises an error
   * - ``["a", "b", "c"]``
     - ``length(@)``
     - 3
   * - ``[]``
     - ``length(@)``
     - 0
   * - ``{}``
     - ``length(@)``
     - 0
   * - ``{"foo": "bar", "baz": "bam"}``
     - ``length(@)``
     - 2

lowercase
~~~~~~~~~

::

    String|null lowercase(String $subject)

Returns the provided ``$subject`` argument in lowercase characters.

If the provided argument is not a String, this function MUST return ``null``.

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - n/a
     - ``lowercase(ABC)``
     - "abc"
   * - n/a
     - ``lowercase("ABC")``
     - "abc"
   * - "CURRENT"
     - ``lowercase(@)``
     - "current"
   * - 123
     - ``lowercase(@)``
     - ``null``
   * - "foo"
     - ``lowercase(@.not_there)``
     - ``null``

matches
~~~~~~~

::

    String|null matches(String $subject, String $pattern [, String $flags])

Returns ``true`` if the given PCRE regular expression ``$pattern`` matches the
provided ``$subject`` string or ``false`` if it does not match.

This function accepts an optional argument, ``$flags``, to set options for
the interpretation of the regular expression. The argument accepts a
string in which individual letters are used to set options. The presence of
a letter within the string indicates that the option is on; its absence
indicates that the option is off. Letters may appear in any order and may be
repeated.

This function returns ``null`` if the provided ``$subject`` argument is not a
string.

This function MUST fail if the provided ``$pattern`` argument is not a string
or if the provided ``$flags`` argument is not a string.

Flags
^^^^^

* ``i``: Case-insensitive matching.
* ``m``: multiline; treat beginning and end characters (^ and $) as working
  over multiple lines (i.e., match the beginning or end of each line
  (delimited by \n or \r), not only the very beginning or end of the
  whole input string)

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - n/a
     - ``matches("foobar", "foo")``
     - ``true``
   * - n/a
     - ``matches("FOO", "^foo$", "i")``
     - ``true``
   * - n/a
     - ``matches("FOO", "foo", "im")``
     - ``true``
   * - n/a
     - ``matches("testing", "foo")``
     - ``false``
   * - "foo"
     - ``matches(@, "foo")``
     - ``true``
   * - "foo"
     - ``matches(@, @)``
     - ``true``
   * - n/a
     - ``matches("foo123", "123")``
     - ``true``
   * - n/a
     - ``matches(false, "foo")``
     - ``null``
   * - n/a
     - ``matches("foo123", 123)``
     - Raises an error
   * - n/a
     - ``matches("foo123", false)``
     - Raises an error
   * - ``[]``
     - ``matches("foo123", @)``
     - Raises an error

substring
~~~~~~~~~

::

    String|null substring(String $subject, Number $start [, Number $length])

Returns a subset of the given string in the ``$subject`` argument starting at
the given ``$start`` position. If no ``$length`` argument is provided, the
function will return the entire remainder of a string after the given
``$start`` position. If the ``$length`` argument is provided, the function will
return a subset of the string starting at the given ``$start`` position and
ending at the ``$start`` position + ``$length`` position.

The provided ``$start`` and ``$length`` arguments MUST be an integer. If a
negative integer is provided for the ``$start`` argument, the start position is
calculated as the total length of the string + the provided ``$start``
argument.

If the given ``$subject`` is not a String, this function returns ``null``.

This function MUST raise an error if the given ``$start`` or ``$length``
arguments are not Numbers.

.. list-table:: Examples
   :header-rows: 1

   * - Expression
     - Result
   * - ``substring("testing", 0, 4)``
     - "test"
   * - ``substring("testing", -2)``
     - "ng"
   * - ``substring("testing", 0, -3)``
     - "test"
   * - ``substring("testing", -3)``
     - "ing"
   * - ``substring("testing", -3, 2)``
     - "in"
   * - ``substring(false, "abc", 2)``
     - ``null``
   * - ``substring("testing", "abc", 2)``
     - Raises an error
   * - ``substring("testing", 0, "abc")``
     - Raises an error

uppercase
~~~~~~~~~

::

    String|null uppercase(String $subject)

Returns the provided ``$subject`` argument in uppercase characters.

If the provided argument is not a String, this function MUST return ``null``.

.. list-table:: Examples
   :header-rows: 1

   * - Expression
     - Result
   * - ``uppercase(Foo)``
     - "FOO"
   * - ``uppercase("123")``
     - "123"
   * - ``uppercase(123)``
     - ``null``
   * - ``uppercase(null)``
     - ``null``

Number functions
----------------

abs
~~~

::

    Number|null abs(Number $number)

Returns the absolute value of the provided argument.

If the provided argument is not a Number, then this function MUST return ``null``.

.. list-table:: Examples
   :header-rows: 1

   * - Expression
     - Result
   * - ``abs(1)``
     - 1
   * - ``abs(-1)``
     - 1
   * - ``abs(abc)``
     - ``null``

ceil
~~~~

::

    Number|null ceil(Number $number)

Returns the next highest integer value by rounding up if necessary.

This function MUST return ``null`` if the provided argument is not a Number.

.. list-table:: Examples
   :header-rows: 1

   * - Expression
     - Result
   * - ``ceil(1.001)``
     - 2
   * - ``ceil(1.9)``
     - 2
   * - ``ceil(1)``
     - 1
   * - ``ceil(abc)``
     - ``null``

floor
~~~~~

::

    Number|null floor(Number $number)

Returns the next lowest integer value by rounding down if necessary.

This function MUST return ``null`` if the provided argument is not a Number.

.. list-table:: Examples
   :header-rows: 1

   * - Expression
     - Result
   * - ``floor(1.001)``
     - 1
   * - ``floor(1.9)``
     - 1
   * - ``floor(1)``
     - 1
   * - ``floor(abc)``
     - ``null``

Array functions
---------------

avg
~~~

::

    Number|null avg(Array $arr)

Returns the average of the elements in the provided Array.

Elements in the Array that are not Numbers are excluded from the averaged
result. If no elements are Numbers, then this function MUST return ``null``.

If the provided argument, ``$arr``, is not an Array, this function MUST return
``null``.

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - ``[10, 15, 20]``
     - ``avg(@)``
     - 15
   * - ``[10, false, 20]``
     - ``avg(@)``
     - 15
   * - ``[false]``
     - ``avg(@)``
     - ``null``
   * - ``false``
     - ``avg(@)``
     - ``null``

.. _contains:

contains
~~~~~~~~

::

    Boolean|null contains(Array|String $subject, String|Number $search)

Returns true if the given ``$subject`` contains the provided ``$search``
String. The ``$search`` argument can be either a String or Number.

If ``$subject`` is an Array, this function returns true if one of the elements
in the Array is equal to the provided ``$search`` value.

If the provided ``$subject`` is a String, this function returns true if
the string contains the provided ``$search`` argument.

This function returns ``null`` if the given ``$subject`` argument is not an
Array or String.

This function MUST raise an error if the provided ``$search`` argument is not
a String or Number.

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - n/a
     - ``contains("foobar", "foo")``
     - ``true``
   * - n/a
     - ``contains("foobar", "not")``
     - ``false``
   * - n/a
     - ``contains("foobar", "bar")``
     - ``true``
   * - n/a
     - ``contains(false, "bar")``
     - ``null``
   * - n/a
     - ``contains(123, "bar")``
     - ``null``
   * - n/a
     - ``contains("foobar", 123)``
     - ``false``
   * - ``["a", "b"]``
     - ``contains(@, a)``
     - ``true``
   * - ``["a"]``
     - ``contains(@, a)``
     - ``true``
   * - ``["a"]``
     - ``contains(@, b)``
     - ``false``
   * - ``{"a": "123"}``
     - ``contains(@, "123")``
     - ``null``
   * - ``{"a": "123"}``
     - ``contains("foo", @)``
     - Raises an error

join
~~~~

::

    String|null join(String $glue, Array $stringsArray)

Returns all of the elements from the provided ``$stringsArray`` Array joined
together using the ``$glue`` argument as a separator between each.

Any element that is not a String or Number is excluded from the joined result.

This function MUST return ``null`` if ``$stringsArray`` is not an Array.

This function MUST raise an error if the provided ``$glue`` argument is not a
String.

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - ``["a", "b"]``
     - ``join(", ", @)``
     - "a, b"
   * - ``["a", "b"]``
     - ``join("", @)``
     - "ab"
   * - ``["a", false, "b"]``
     - ``join(", ", @)``
     - "a, b"
   * - ``[false]``
     - ``join(", ", @)``
     - ""
   * - n/a
     - ``join(", ", foo)``
     - ``null``
   * - ``["a", "b"]``
     - ``join(false, @)``
     - Raises an error

length
~~~~~~

See length_.

max
~~~

::

    Number|null max(Array $collection)

Returns the highest found Number in the provided Array argument. Any element in
the sequence that is not a Number MUST be ignored from the calculated result.

If the provided argument is not an Array, this function MUST return ``null``.

If no Numeric values are found, this function MUST return ``null``.

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - ``[10, 15]``
     - ``max(@)``
     - 15
   * - ``[10, false, 20]``
     - ``max(@)``
     - 20
   * - ``[false]``
     - ``max(@)``
     - ``null``
   * - ``[]``
     - ``max(@)``
     - ``null``
   * - ``{"foo": 10, "bar": 20}``
     - ``max(@)``
     - ``null``
   * - ``false``
     - ``max(@)``
     - ``null``

min
~~~

::

    Number|null min(Array $collection)

Returns the lowest found Number in the provided Array argument.

Any element in the sequence that is not a Number MUST be ignored from the
calculated result. If no Numeric values are found, this function MUST return
``null``.

This function MUST return ``null`` if the provided argument is not an Array.

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - ``[10, 15]``
     - ``min(@)``
     - 10
   * - ``[10, false, 20]``
     - ``min(@)``
     - 10
   * - ``[false]``
     - ``min(@)``
     - ``null``
   * - ``[]``
     - ``min(@)``
     - ``null``
   * - ``{"foo": 10, "bar": 20}``
     - ``min(@)``
     - ``null``
   * - ``false``
     - ``min(@)``
     - ``null``

reverse
~~~~~~~

::

    Array|null reverse(Array $list)

This function accepts an Array ``$list`` argument and returns the the elements
in reverse order.

This function MUST return ``null`` if the provided argument is not an Array.

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - ``["a", "b", "c"]``
     - ``reverse(@)``
     - ``["c", "b", "a"]``
   * - ``[1, "a", "c"]``
     - ``reverse(@)``
     - ``["c", "a", 1]``
   * - ``{"a": 1, "b": 2}``
     - ``reverse(@)``
     - ``null``
   * - ``false``
     - ``reverse(@)``
     - ``null``

sort
~~~~

::

    Array|null sort(Array $list)

This function accepts an Array ``$list`` argument and returns the
lexicographically sorted elements of the ``$list`` as an Array.

This function MUST return ``null`` if the provided argument is not an Array.

Array element types are sorted in the following order (the lower the number
means the sooner in the list the element appears):

1. Object
2. Array
3. null
4. Boolean
5. Number
6. String

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - ``[b, a, c]``
     - ``sort(@)``
     - ``[a, b, c]``
   * - ``[1, a, c]``
     - ``sort(@)``
     - ``[1, a, c]``
   * - ``[false, [], null]``
     - ``sort(@)``
     - ``[[], null, false]``
   * - ``[[], {}, false]``
     - ``sort(@)``
     - ``[{}, [], false]``
   * - ``{"a": 1, "b": 2}``
     - ``sort(@)``
     - ``null``
   * - ``false``
     - ``sort(@)``
     - ``null``

Object functions
----------------

contains
~~~~~~~~

See contains_.

length
~~~~~~

See length_.

keys
~~~~

::

    Array|null keys(Object $obj)

Returns an Array containing the hash keys of the provided Object.

This function MUST return ``null`` if the provided argument is not an Object.

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - ``{"foo": "baz", "bar": "bam"}``
     - ``keys(@)``
     - ``["foo", "bar"]``
   * - ``{}``
     - ``keys(@)``
     - ``[]``
   * - ``false``
     - ``keys(@)``
     - ``null``
   * - ``[b, a, c]``
     - ``keys(@)``
     - ``null``

union
~~~~~

::

    Object|null union(Object $object1, Object $object2 [, Object $... ])

Returns an Object containing all of the provided arguments merged into a single
Object. If a key collision occurs, the first key value is used.

This function requires at least two arguments. If any of the provided
arguments are not Objects, those argument are ignored from the resulting merged
object.

If no Object arguments are found, this function MUST return ``null``.

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - ``[{"foo": "baz", "bar": "bam"}, {"qux": "more"}]``
     - ``union(@[0], @[1])``
     - ``{"foo": "baz", "bar": "bam", "qux": "more"}``
   * - ``[{"foo": "baz", "bar": "bam"}, {"qux": "more", "foo": "ignore"}]``
     - ``union(@[0], @[1])``
     - ``{"foo": "baz", "bar": "bam", "qux": "more"}``
   * - ``[{}, {}]``
     - ``union(@[0], @[1])``
     - ``{}``
   * - ``[{"foo": "baz", "bar": "bam"}, [], false, {"qux": "more", "foo": "ignore"}]``
     - ``union(@[0], @[1])``
     - ``{"foo": "baz", "bar": "bam", "qux": "more"}``
   * - n/a
     - ``union(false, false)``
     - ``null``
   * - {}
     - ``union(@)``
     - Raises an error

values
~~~~~~

::

    Array|null values(Object|Array $obj)

Returns the values of the provided Object.

If the given argument is an Array, this function transparently returns the
given argument.

This function MUST return ``null`` if the given argument is not an Object or
Array.

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - ``{"foo": "baz", "bar": "bam"}``
     - ``values(@)``
     - ``["baz", "bam"]``
   * - ``["a", "b"]``
     - ``values(@)``
     - ``["a", "b"]``
   * - ``[{}, {}]``
     - ``values(@)``
     - ``[{}, {}]``
   * - ``false``
     - ``values(@)``
     - ``null``

Type functions
--------------

get
~~~

::

    mixed|null get(mixed $subject [, mixed $... ])

This function accepts a variable number of arguments, each of which can be of
any type and returns the first argument that is not "falsey".

This function MUST return ``null`` if all arguments are "falsey".

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - n/a
     - ``get(abc)``
     - "abc"
   * - n/a
     - ``get(true, abc)``
     - ``true``
   * - n/a
     - ``get(abc, true)``
     - "abc"
   * - n/a
     - ``get(false, true)``
     - ``true``
   * - n/a
     - ``get(null, false, 123)``
     - 123
   * - n/a
     - ``get(0, abc)``
     - 0
   * - n/a
     - ``get("")``
     - ``null``
   * - n/a
     - ``get("", false, null)``
     - ``null``
   * - ``[]``
     - ``get(@, 123)``
     - 123
   * - ``{}``
     - ``get(@, 123)``
     - 123
   * - ``{"abc": false}``
     - ``get(@, 123)``
     - ``{"abc": false}``
   * - ``[false]``
     - ``get(@, 123)``
     - ``[false]``

type
~~~~

::

    String type(mixed $subject)

Returns the JavaScript type of the given ``$subject`` argument as a string
value.

The return value MUST be one of the following:

* Number
* String
* Boolean
* Array
* Object
* null

.. list-table:: Examples
   :header-rows: 1

   * - Given
     - Expression
     - Result
   * - "foo"
     - ``type(@)``
     - "String"
   * - ``true``
     - ``type(@)``
     - "Boolean"
   * - ``false``
     - ``type(@)``
     - "Boolean"
   * - ``null``
     - ``type(@)``
     - "null"
   * - 123
     - ``type(@)``
     - Number
   * - 123.05
     - ``type(@)``
     - Number
   * - ``["abc"]``
     - ``type(@)``
     - "Array"
   * - ``{"abc": "123"}``
     - ``type(@)``
     - "Object"

Test Cases
==========

.. code-block:: json

    [{
      "given":
        {
          "foo": -1,
          "zero": 0,
          "arr": [-1, 3, 4, 5, "a", "100"],
          "strings": ["a", "b", "c"],
          "dec": [1.01, 1.9, -1.5],
          "str": "Str",
          "false": false,
          "empty": [],
          "empty2": {}
        },
      "cases": [
        {
          "expression": "abs(@.foo)",
          "result": 1
        },
        {
          "expression": "abs(@.str)",
          "result": null
        },
        {
          "expression": "abs(@.arr[1])",
          "result": 3
        },
        {
          "expression": "abs(false)",
          "result": null
        },
        {
          "expression": "abs(1, 2, 3)",
          "error": "runtime"
        },
        {
          "expression": "abs()",
          "error": "runtime"
        },
        {
          "expression": "avg(@.arr)",
          "result": 2.75
        },
        {
          "expression": "avg(\"abc\")",
          "result": null
        },
        {
          "expression": "avg(@.foo)",
          "result": null
        },
        {
          "expression": "avg(@)",
          "result": null
        },
        {
          "expression": "avg(@.strings)",
          "result": null
        },
        {
          "expression": "ceil(@.dec[0])",
          "result": 2
        },
        {
          "expression": "ceil(@.dec[1])",
          "result": 2
        },
        {
          "expression": "ceil(@.dec[2])",
          "result": -1
        },
        {
          "expression": "ceil(abc)",
          "result": null
        },
        {
          "expression": "concat(@.strings[0], @.strings[1], @.strings[2])",
          "result": "abc"
        },
        {
          "expression": "concat(@.strings[0], @.strings[1], @.strings[2], @.foo)",
          "result": "abc-1"
        },
        {
          "expression": "concat(@.strings[0], @.strings[1], @.strings[2], @)",
          "result": "abc"
        },
        {
          "expression": "concat(null, false)",
          "result": null
        },
        {
          "expression": "concat(foo)",
          "error": "runtime"
        },
        {
          "expression": "concat()",
          "error": "runtime"
        },
        {
          "expression": "contains(abc, a)",
          "result": true
        },
        {
          "expression": "contains(abc, d)",
          "result": false
        },
        {
          "expression": "contains(false, d)",
          "result": null
        },
        {
          "expression": "contains(@.strings, a)",
          "result": true
        },
        {
          "expression": "contains(@.dec, 1.9)",
          "result": false
        },
        {
          "expression": "contains(@.dec, false)",
          "error": "runtime"
        },
        {
          "expression": "length(@)",
          "result": 9
        },
        {
          "expression": "length(@.arr)",
          "result": 6
        },
        {
          "expression": "length(@.str)",
          "result": 3
        },
        {
          "expression": "floor(@.dec[0])",
          "result": 1
        },
        {
          "expression": "floor(@.foo)",
          "result": -1
        },
        {
          "expression": "floor(@.str)",
          "result": null
        },
        {
          "expression": "get(@.empty)",
          "result": null
        },
        {
          "expression": "get(@.empty, @.\"false\")",
          "result": null
        },
        {
          "expression": "get(@.empty, @.\"false\", @.foo)",
          "result": -1
        },
        {
          "expression": "get(@.zero, 10)",
          "result": 0
        },
        {
          "expression": "get(null, false, @.empty, true)",
          "result": true
        },
        {
          "expression": "join(\", \", @.str)",
          "result": null
        },
        {
          "expression": "join(\", \", @.strings)",
          "result": "a, b, c"
        },
        {
          "expression": "join(\"|\", @.strings)",
          "result": "a|b|c"
        },
        {
          "expression": "join(\"|\", @.dec)",
          "result": "1.01|1.9|-1.5"
        },
        {
          "expression": "join(\"|\", @.empty)",
          "result": ""
        },
        {
          "expression": "keys(@)",
          "result": ["foo", "zero", "arr", "strings", "dec", "str", "false", "empty", "empty2"]
        },
        {
          "expression": "keys(@.empty2)",
          "result": []
        },
        {
          "expression": "keys(@.strings)",
          "result": null
        },
        {
          "expression": "keys(abc)",
          "result": null
        },
        {
          "expression": "keys(false)",
          "result": null
        },
        {
          "expression": "length(abc)",
          "result": 3
        },
        {
          "expression": "length(\"\")",
          "result": 0
        },
        {
          "expression": "length(@.foo)",
          "result": null
        },
        {
          "expression": "length(@.strings[0])",
          "result": 1
        },
        {
          "expression": "length(false)",
          "result": null
        },
        {
          "expression": "lowercase(@.str)",
          "result": "str"
        },
        {
          "expression": "lowercase(false)",
          "result": null
        },
        {
          "expression": "matches(@.str, \"str\")",
          "result": false
        },
        {
          "expression": "matches(@.str, \"str\", i)",
          "result": true
        },
        {
          "expression": "matches(@.str, false)",
          "error": "runtime"
        },
        {
          "expression": "matches(@.str, \"ST\", \"im\")",
          "result": true
        },
        {
          "expression": "matches(false, \"str\")",
          "result": null
        },
        {
          "expression": "matches(str, \"str\", i, 123)",
          "error": "runtime"
        },
        {
          "expression": "max(@.arr)",
          "result": 5
        },
        {
          "expression": "max(@.dec)",
          "result": 1.9
        },
        {
          "expression": "max(abc)",
          "result": null
        },
        {
          "expression": "max(@.empty)",
          "result": null
        },
        {
          "expression": "min(@.arr)",
          "result": -1
        },
        {
          "expression": "min(@.dec)",
          "result": -1.5
        },
        {
          "expression": "min(abc)",
          "result": null
        },
        {
          "expression": "min(@.empty)",
          "result": null
        },
        {
          "expression": "reverse(@.arr)",
          "result": ["100", "a", 5, 4, 3, -1]
        },
        {
          "expression": "reverse(@.strings)",
          "result":  ["c", "b", "a"]
        },
        {
          "expression": "reverse(abc)",
          "result": null
        },
        {
          "expression": "reverse(@.empty)",
          "result": null
        },
        {
          "expression": "reverse(@)",
          "result": null
        },
        {
          "expression": "sort(@.arr)",
          "result": [-1, 3, 4, 5, "a", "100"]
        },
        {
          "expression": "sort(@.strings)",
          "result":  ["a", "b", "c"]
        },
        {
          "expression": "sort(abc)",
          "result": null
        },
        {
          "expression": "sort(@.empty)",
          "result": []
        },
        {
          "expression": "sort(@)",
          "result": null
        },
        {
          "expression": "substring(abc, 0, -1)",
          "result": "ab"
        },
        {
          "expression": "substring(abc, -2)",
          "result": "bc"
        },
        {
          "expression": "substring(abc123, 1)",
          "result": "bc123"
        },
        {
          "expression": "substring(false, 1, 1)",
          "result": null
        },
        {
          "expression": "substring(abc, true)",
          "error": "runtime"
        },
        {
          "expression": "substring(abc, 1, false)",
          "error": "runtime"
        },
        {
          "expression": "substring()",
          "error": "runtime"
        },
        {
          "expression": "type(abc)",
          "result": "String"
        },
        {
          "expression": "type(123)",
          "result": "Number"
        },
        {
          "expression": "type(1.2)",
          "result": "Number"
        },
        {
          "expression": "type(true)",
          "result": "Boolean"
        },
        {
          "expression": "type(false)",
          "result": "Boolean"
        },
        {
          "expression": "type(@.empty)",
          "result": "Array"
        },
        {
          "expression": "type(@.strings)",
          "result": "Array"
        },
        {
          "expression": "type(@)",
          "result": "Object"
        },
        {
          "expression": "uppercase(@.str)",
          "result": "STR"
        },
        {
          "expression": "uppercase(false)",
          "result": null
        }
      ]
    }, {
      "given":
        [
          {"foo": "baz", "bar": "bam"},
          {"foo": "123"},
          {"abc": "def", "fez": "qux"},
          [1, 2, 3],
          "abc",
          true
        ],
      "cases": [
        {
          "expression": "union(@[0], @[1])",
          "result": {"foo": "baz", "bar": "bam"}
        },
        {
          "expression": "union(@[0], @[2])",
          "result": {"foo": "baz", "bar": "bam", "abc": "def", "fez": "qux"}
        },
        {
          "expression": "union(@[3], @[4])",
          "result": null
        },
        {
          "expression": "union(true, false)",
          "result": null
        },
        {
          "expression": "values(@[0])",
          "result": ["baz", "bam"]
        },
        {
          "expression": "values(@[1])",
          "result": ["123"]
        },
        {
          "expression": "values(@[3])",
          "result": [1, 2, 3]
        },
        {
          "expression": "values(@[4])",
          "result": null
        }
      ]
    }]
