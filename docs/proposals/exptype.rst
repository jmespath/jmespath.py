================
Expression Types
================

:JEP: 8
:Author: James Saryerwinnie
:Status: draft
:Created: 02-Mar-2013

Abstract
========

This JEP proposes grammar modifications to JMESPath to allow for
expression references within functions.  This allows for functions
such as ``sort_by``, ``max_by``, ``min_by``.  These functions take
an argument that resolves to an expression type.  This enables
functionality such as sorting an array based on an expression that
is evaluated against every array element.


Motivation
==========

A useful feature that is common in other expression languages is the
ability to sort a JSON object based on a particular key.  For example,
given a JSON object::

  {
    "people": [
         {"age": 20, "age_str": "20", "bool": true, "name": "a", "extra": "foo"},
         {"age": 40, "age_str": "40", "bool": false, "name": "b", "extra": "bar"},
         {"age": 30, "age_str": "30", "bool": true, "name": "c"},
         {"age": 50, "age_str": "50", "bool": false, "name": "d"},
         {"age": 10, "age_str": "10", "bool": true, "name": 3}
    ]
  }

It is not currently possible to sort the ``people`` array by the ``age`` key.
Also, ``sort`` is not defined for the ``object`` type, so it's not currently
possible to even sort the ``people`` array.  In order to sort the ``people`` array,
we need to know what key to use when sorting the array.

This concept of sorting based on a key can be generalized.  Instead of
requiring a key name, an expression can be provided that each element
would be evaluated against.  In the simplest case, this expression would just
be an ``identifier``, but more complex expressions could be used such as
``foo.bar.baz``.

A simple way to accomplish this might be to create a function like this::

    sort_by(array arg1, expression)

    # Called like:

    sort_by(people, age)
    sort_by(people, to_number(age_str))

However, there's a problem with the ``sort_by`` function as defined above.
If we follow the function argument resolution process we get::

    sort_by(people, age)

    # 1. resolve people
    arg1 = search(people, <input data>) -> [{"age": ...}, {...}]

    # 2. resolve age
    arg2 = search(age, <input data>) -> null

    sort_by([{"age": ...}, {...}], null)

The second argument is evaluated against the current node and the expression
``age`` will resolve to ``null`` because the input data has no ``age`` key.
There needs to be some way to specify that an expression should evaluate to
an expression type::

    arg = search(<some expression>, <input data>) -> <expression: age>

Then the function definition of ``sort_by`` would be::

    sort_by(array arg1, expression arg2)


Specification
=============

The following grammar rules will be updated to::

    function-arg        = expression /
                          current-node /
                          "&" expression

Evaluating an expression reference should return an object of type
"expression".  The list of data types supported by a function will now be:

* number (integers and double-precision floating-point format in JSON)
* string
* boolean (``true`` or ``false``)
* array (an ordered, sequence of values)
* object (an unordered collection of key value pairs)
* null
* expression (denoted by ``&expression``)

Function signatures can now be specified using this new ``expression`` type.
Additionally, a function signature can specify the return type of the
expression.  Similarly how arrays can specify a type within a list using the
``array[type]`` syntax, expressions can specify their resolved type using
``expression->type`` syntax.


Additional Functions
--------------------

The following functions will be added:

sort_by
~~~~~~~

::

    sort_by(array elements, expression->number|expression->string expr)

Sort an array using an expression ``expr`` as the sort key.
Below are several examples using the ``people`` array (defined above) as the
given input.


.. list-table:: Examples
  :header-rows: 1

  * - Expression
    - Result
  * - ``sort_by(people, &age)[].age``
    - [10, 20, 30, 40, 50]
  * - ``sort_by(people, &age)[0]``
    - {"age": 10, "age_str": "10", "bool": true, "name": 3}
  * - ``sort_by(people, &age_str)``
    - <error: invalid-type>
  * - ``sort_by(people, &to_number(age_str))[0]``
    - {"age": 10, "age_str": "10", "bool": true, "name": 3}


max_by
~~~~~~

::

    max_by(array elements, expression->number expr)

Return the maximum element in an array using the expression ``expr`` as the
comparison key.  The entire maximum element is returned.
Below are several examples using the ``people`` array (defined above) as the
given input.


.. list-table:: Examples
  :header-rows: 1

  * - Expression
    - Result
  * - ``max_by(people, &age)``
    - {"age": 50, "age_str": "50", "bool": false, "name": "d"},
  * - ``max_by(people, &age).age``
    - 50
  * - ``max_by(people, &to_number(age_str))``
    - {"age": 50, "age_str": "50", "bool": false, "name": "d"},
  * - ``max_by(people, &age_str)``
    - <error: invalid-type>
  * - ``max_by(people, age)``
    - <error: invalid-type>


min_by
~~~~~~

::

    min_by(array elements, expression->number expr)

Return the minimum element in an array using the expression ``expr`` as the
comparison key.  The entire maximum element is returned.
Below are several examples using the ``people`` array (defined above) as the
given input.


.. list-table:: Examples
  :header-rows: 1

  * - Expression
    - Result
  * - ``min_by(people, &age)``
    - {"age": 10, "age_str": "10", "bool": true, "name": 3}
  * - ``min_by(people, &age).age``
    - 10
  * - ``min_by(people, &to_number(age_str))``
    - {"age": 10, "age_str": "10", "bool": true, "name": 3}
  * - ``min_by(people, &age_str)``
    - <error: invalid-type>
  * - ``min_by(people, age)``
    - <error: invalid-type>
