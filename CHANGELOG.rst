0.9.3
=====

* Fix issue where long types in py2 and ``Decimal`` types
  were not being evaluated as numbers
  (`issue 125 <https://github.com/jmespath/jmespath.py/issues/125>`__)
* Handle numbers in scientific notation in ``to_number()`` function
  (`issue 120 <https://github.com/jmespath/jmespath.py/issues/120>`__)
* Fix issue where custom functions would override the function table
  of the builtin function class
  (`issue 133 <https://github.com/jmespath/jmespath.py/issues/133>`__)


0.9.2
=====

* Fix regression when using ordering comparators on strings
  (`issue 124 <https://github.com/jmespath/jmespath.py/issues/124>`__)


0.9.1
=====

* Raise LexerError on invalid numbers
  (`issue 98 <https://github.com/jmespath/jmespath.py/issues/98>`__)
* Add support for custom functions (#100)
  (`issue 100 <https://github.com/jmespath/jmespath.py/issues/100>`__)
* Fix ZeroDivisionError for built-in function avg() on empty lists (#115)
  (`issue 115 <https://github.com/jmespath/jmespath.py/issues/115>`__)
* Properly handle non numerical ordering operators (#117)
  (`issue 117 <https://github.com/jmespath/jmespath.py/issues/117>`__)


0.9.0
=====

* Add support for new lines with tokens in an expression
* Add support for `JEP 9 <http://jmespath.org/proposals/improved-filters.html>`__,
  which introduces "and" expressions, "unary" expressions, "not" expressions,
  and "paren" expressions
* Fix issue with hardcoded path in ``jp.py`` executable
  (`issue 90 <https://github.com/jmespath/jmespath.py/issues/90>`__,
   `issue 88 <https://github.com/jmespath/jmespath.py/issues/88>`__,
   `issue 82 <https://github.com/jmespath/jmespath.py/issues/82>`__)


0.8.0
=====

* Improve lexing performance (`issue 84 <https://github.com/jmespath/jmespath.py/pull/84>`__)
* Fix parsing error for multiselect lists (`issue 86 <https://github.com/jmespath/jmespath.py/issues/86>`__)
* Fix issue with escaping single quotes in literal strings (`issue 85 <https://github.com/jmespath/jmespath.py/issues/85>`__)
* Add support for providing your own dict cls to support
  ordered dictionaries (`issue 94 <https://github.com/jmespath/jmespath.py/pull/94>`__)
* Add map() function (`issue 95 <https://github.com/jmespath/jmespath.py/pull/95>`__)


0.7.1
=====

* Rename ``bin/jp`` to ``bin/jp.py``
* Fix issue with precedence when parsing wildcard
  projections
* Remove ordereddict and simplejson as py2.6 dependencies.
  These were never actually used in the jmespath code base,
  only in the unit tests.  Unittests requirements are handled
  via requirements26.txt.


0.7.0
=====

* Add support for JEP-12, raw string literals
* Support .whl files

0.6.2
=====

* Implement JEP-10, slice projections
* Fix bug with filter projection parsing
* Add ``to_array`` function
* Add ``merge`` function
* Fix error messages for function argument type errors
