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
