=========
Root node
=========

:JEP: 2
:Author: Michael Dowling
:Status: draft
:Created: 02-Dec-2013

Abstract
========

This document proposes modifying the `JMESPath grammar <http://jmespath.readthedocs.org/en/latest/specification.html#grammar>`_
to support referencing the root node in an expression. The root node is defined 
as the initial data passed into a JMESPath expression.

Motivation
==========

By adding support for accessing the root node of an expression, we allow users 
to generate more customizable output structures based on the provided input. By
combining filters with root node, support we can create a powerful DSL that can
be used to build complex output.

Modified Grammar
================

The following changes will need to be made to the JMESPath grammar to support
root node expressions.

::

    expression        = sub-expression / index-expression / or-expression / identifier / "*"
    expression        =/ multi-select-list / multi-select-hash
    expression        =/ root-node
    root-node         = "$"
