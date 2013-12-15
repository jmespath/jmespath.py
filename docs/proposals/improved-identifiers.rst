====================
Improved Identifiers
====================

:JEP: 6
:Author: James Saryerwinnie
:Status: draft
:Created: 14-Dec-2013
:Last Updated: 15-Dec-2013


Abstract
========

This JEP proposes grammar modifications to JMESPath in order to improve
identifiers used in JMESPath.  In doing so, several inconsistencies in the
identifier grammar rules will be fixed, along with an improved grammar for
specifying unicode identifiers in a way that is consistent with JSON
strings.


Motivation
==========

There are two ways to currently specify an identifier, the unquoted rule::

    identifier        = 1*char

and the quoted rule::

    identifier        =/ quote 1*(unescaped-char / escaped-quote) quote

The ``char`` rule contains a set of characters that do **not** have to be
quoted::

    char              = %x30-39 / ; 0-9
                        %x41-5A / ; A-Z
                        %x5F /    ; _
                        %x61-7A / ; a-z
                        %x7F-10FFFF

There is an ambiguity between the ``%x30-39`` rule and the ``number`` rule::

    number            = ["-"]1*digit
    digit             = "1" / "2" / "3" / "4" / "5" / "6" / "7" / "8" / "9" / "0"

It's ambiguous which rule to use.  Given a string "123", it's not clear whether
this should be parsed as an identifier or a number. Existing implementations
**aren't** following this rule (because it's ambiguous) so the grammar should
be updated to remove the ambiguity, specifically, an identifier **cannot**
start with ``[0-9]``.

Unicode
-------

JMESPath supports unicode through the ``char``  and ``unescaped-char`` rule::

    unescaped-char    = %x30-10FFFF
    char              = %x30-39 / ; 0-9
                        %x41-5A / ; A-Z
                        %x5F /    ; _
                        %x61-7A / ; a-z
                        %x7F-10FFFF

However, JSON supports a syntax for escaping unicode characters.  Any
character in the Basic Multilingual Plane (BMP) can be escaped with::

    char = escape (%x75 4HEXDIG )  ; \uXXXX

Similar to the way that XPath supports numeric character references used
in XML (``&#nnnn``), JMESPath should support the same escape sequences
used in JSON.  JSON also supports a 12 character escape sequence for
characters outside of the BMP, by encoding the UTF-16 surrogate pair.
For example, the code point ``U+1D11E`` can be represented
as ``"\uD834\uDD1E"``.


Escape Sequences
----------------

Consider the following JSON object::

    {"foo\nbar": "baz"}

A JMESPath expression should be able to retrieve the value of baz.  With
the current grammar, one must rely on the environment's ability to input
control characters such as the newline (``%x0A``).  This can be problematic
in certain environments.  For example, in python, this is not a problem::

    >>> jmespath_expression = "foo\nbar"

Python will interpret the sequence ``"\n"`` (``%5C %6E``) as the newline
character ``%x0A``.  However, consider Bash::

    $ foo --jmespath-expression "foo\nbar"

In this situation, bash will not interpret the ``"\n"`` (``%5C %6E``) sequence.


Specification
=============

The ``char`` rule contains a set of characters that do **not** have to be
quoted.  The new set of characters that do not have to quoted will be::

    unquoted-string   = (%x41-5A / %x61-7A) *(%30-39 / %x41-5A / %x5F / %x61-7A)

In order for an identifier to not be quoted, it must start with ``[A-Za-z]``,
then must be followed by zero or more ``[0-9A-Za-z_]``.

The unquoted rule is updated to account for all JSON supported escape
sequences::

    quoted-string     =/ quote 1*(unescaped-char / escaped-char) quote

The full rule for an identifier is::

    identifier        = unquoted-string / quoted-string
    unquoted-string   = (%x41-5A / %x61-7A) *(  ; a-zA-Z
                            %30-39  /  ; 0-9
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


Rationale
=========

Adopting the same string rules as JSON strings will allow users familiar with
JSON semantics to understand how JMESPath identifiers will work.

This change also provides a nice consistency for the literal syntax proposed
in JEP 3.  With this model, the supported literal strings can be the same
as quoted identifiers.

This also will allow the grammar to grow in a consistent way if JMESPath
adds support for filtering based on literal values.  For example (note that
this is just a suggested syntax, not a formal proposal), given the data::

    {"foo": [{"✓": "✓"}, {"✓": "✗"}]}

You can now have the following JMESPath expressions::

    foo[?"✓" = `✓`]
    foo[?"\u2713" = `\u2713`]

As a general property, any supported JSON string is now a supported quoted
identifier.


Impact
======

For any implementation that was parsing digits as an identifier, identifiers
starting with digits will no longer be valid, e.g. ``foo.0.1.2``.
All remaining changes are additive and backwards compatible.
