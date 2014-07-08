==================
Filter Expressions
==================

:JEP: 9
:Author: James Saryerwinnie
:Status: proposed
:Created: 07-July-2014
:Last Updated: 09-April-2015


Abstract
========

JEP 7 introduced filter expressions, which is a mechanism to allow
list elements to be selected based on matching an expression against
each list element.  While this concept is useful, the actual comparator
expressions were not sufficiently capable to accomodate a number of common
queries.  This JEP expands on filter expressions by proposing support for
``and-expressions``, ``not-expression``, ``paren-expressions``, and
``unary-expressions``.  With these additions, the capabilities of a filter
expression now allow for sufficiently powerful queries to handle the majority
of queries.


Motivation
==========

JEP 7 introduced filter queries, that essentially look like this::

    foo[?lhs omparator rhs]

where the left hand side (lhs)  and the right hand side (rhs)
are both an ``expression``, and comparator is one of
``==, !=, <, <=, >, >=``.

This added a useful feature to JMESPath: the ability to filter
a list based on evaluating an expression against each element in a list.

In the time since JEP 7 has been part of JMESPath, a number of cases have been
pointed out in which filter expressions cannot solve.  Below are examples of
each type of missing features.


Or Expressions
--------------

First, users want the ability to filter based on matching one or more
expressions.  For example, given::

    {
      "cities": [
        {"name": "Seattle", "state": "WA"},
        {"name": "Los Angeles", "state": "CA"},
        {"name": "Bellevue", "state": "WA"},
        {"name": "New York", "state": "NY"},
        {"name": "San Antonio", "state": "TX"},
        {"name": "Portland", "state": "OR"}
      ]
    }

a user might want to select locations on the west coast, which in
this specific example means cities in either ``WA``, ``OR``, or
``CA``.  It's not possible to express this as a filter expression
given the grammar of ``expression comparator expression``.  Ideally
a user should be able to use::

    cities[?state == `WA` || state == `OR` || state == `CA`]

JMESPath already supports Or expressions, just not in the context
of filter expressions.

And Expressions
---------------

The next missing feature of filter expressions is support for And
expressions.  It's actually somewhat odd that JMESPath has support
for Or expressions, but not for And expressions.  For example,
given a list of user accounts with permissions::

    {
      "users": [
        {"name": "user1", "type": "normal"", "allowed_hosts": ["a", "b"]},
        {"name": "user2", "type": "admin", "allowed_hosts": ["a", "b"]},
        {"name": "user3", "type": "normal", "allowed_hosts": ["c", "d"]},
        {"name": "user4", "type": "admin", "allowed_hosts": ["c", "d"]},
        {"name": "user5", "type": "normal", "allowed_hosts": ["c", "d"]},
        {"name": "user6", "type": "normal", "allowed_hosts": ["c", "d"]}
      ]
    }

We'd like to find admin users that have permissions to the host named
``c``.  Ideally, the filter expression would be::

    users[?type == `admin` && contains(allowed_hosts, `c`)]


Unary Expressions
-----------------

Think of an if statement in a language such as C or Java.  While you can write
an if statement that looks like::

    if (foo == bar) { ... }

You can also use a unary expression such as::

    if (allowed_access) { ... }

or::

    if (!allowed_access) { ... }

Adding support for unary expressions brings a natural syntax when filtering
against boolean values.  Instead of::

    foo[?boolean_var == `true`]

a user could instead use::

    foo[?boolean_var]

As a more realistic example, given a slightly different structure
for the ``users`` data above::

    {
      "users": [
        {"name": "user1", "is_admin": false, "disabled": false},
        {"name": "user2", "is_admin": true, "disabled": true},
        {"name": "user3", "is_admin": false, "disabled": false},
        {"name": "user4", "is_admin": true, "disabled": false},
        {"name": "user5", "is_admin": false, "disabled": true},
        {"name": "user6", "is_admin": false, "disabled": false}
      ]
    }

If we want to get the names of all admin users whose account is enabled, we
could either say::

    users[?is_admin == `true` && disabled == `false]

but it's more natural and succinct to instead say::

    users[?is_admin && !disabled]

A case can be made that this syntax is not strictly necessary.  This is true.
However, the main reason for adding support for unary expressions in a filter
expression is users expect this syntax, and are surprised when this is not
a supported syntax.  Especially now that we are basically anchoring to
a C-like syntax for filtering in this JEP, users will expect unary expressions
even more.


Specification
=============

There are several updates to the grammar::

    and-expression         = expression "&&" expression
    not-expression         = "!" expression
    paren-expression       = "(" expression ")"


Additionally, the ``filter-expression`` rule is updated
to be more general::

    bracket-specifier      =/ "[?" expression "]"

The ``list-filter-expr`` is now a more general
``comparator-expression``::

    comparator-expression  = expression comparator expression

which is now just an expression::

    expression /= comparator-expression

And finally, the ``current-node`` is now allowed as a generic
expression::

    expression /= current-node

Now that these expressions are allowed as general ``expressions``, there
semantics outside of their original contexts must be defined.


And Expressions
---------------

An ``and-expression`` has similar semantics to and expressions in other
languages.  If the expression on the left hand side is a truth-like value, then
the value on the right hand side is returned.  Otherwise the result of the
expression on the left hand side is returned.  This also reduces to the
expected truth table:

.. list-table:: Truth table for and expressions
  :header-rows: 1

  * - LHS
    - RHS
    - Result
  * - True
    - True
    - True
  * - True
    - False
    - False
  * - False
    - True
    - False
  * - False
    - False
    - False


Not Expressions
---------------

A ``not-expression`` negates the result of an expression.  If the expression
results in a truth-like value, a ``not-expression`` will change this value to
``false``.  If the expression results in a false-like value, a
``not-expression`` will change this value to ``true``.


Paren Expressions
-----------------

A ``paren-expression`` allows a user to override the precedence order of
an expression.


Precedence
==========

This JEP introduces And expressions, which would normally be defined as::

    expression     = or-expression / and-expression / not-expression
    or-expression  = expression "||" expression
    and-expression = expression "&&" expression
    not-expression = "!" expression

However, if this current pattern is followed, it makes it impossible to parse
an expression with the correct precedence.  A more standard way of expressing
this would be::

    expression          = or-expression
    or-expression       = and-expression "||" and-expression
    and-expression      = not-expression "&&" not-expression
    not-expression      = "!" expression


Rationale
=========

This JEP brings several tokens that were only allowed in specific constructs
into the more general ``expression`` rule.  Specifically:

* The ``current-node`` (``@``) was previously only allowed in function
  expressions, but is now allowed as a general ``expression``.
* The ``filter-expression`` now accepts any arbitrary ``expression``.
* The ``list-filter-expr`` is now just a generic ``comparator-expression``,
  which again is just a general ``expression``.

There are several reasons the previous grammar rules were minimally scoped.
One of the main reasons, as stated in JEP 4 which introduced filter
expressions, was to keep the spec "purposefully minimal."  In fact the end
of JEP 4 states that there "are several extensions that can be added in
future." This is in fact exactly what this JEP proposes, the recommendations
from JEP 4.
