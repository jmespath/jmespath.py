.. JamesPath documentation master file, created by
   sphinx-quickstart on Tue Feb 19 14:49:37 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

JMESPath
========

JSON Matching Expression paths.  JMESPath allows you
to declaratively specify how to extract elements from a JSON document.

For example, given this document::

    {"foo": {"bar": "baz"}}

The jmespath expression ``foo.bar`` will return "baz".


Contents:

.. toctree::
   :maxdepth: 2

   specification
   proposals


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

