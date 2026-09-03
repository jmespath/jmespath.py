#!/usr/bin/env python
import gc
import weakref

from tests import unittest

import jmespath
from jmespath import visitor


class TestVisitorMethodCache(unittest.TestCase):
    def test_method_cache_does_not_create_reference_cycle(self):
        # Visitor.visit() caches the resolved visit_* method on
        # self._method_cache.  If that cache stores a bound method, the
        # instance ends up holding a reference to itself
        # (self -> _method_cache -> bound method -> self), and a whole
        # TreeInterpreter (one gets built on every ParsedResult.search()
        # call) can then only be reclaimed by the cyclic garbage
        # collector instead of going away as soon as its refcount drops
        # to zero. Under a heavy search workload that adds up to a lot
        # of avoidable GC churn.
        gc.disable()
        try:
            expression = jmespath.compile('a.b.c')
            created = []
            original_init = visitor.TreeInterpreter.__init__

            def spy_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                created.append(weakref.ref(self))

            visitor.TreeInterpreter.__init__ = spy_init
            try:
                result = expression.search({'a': {'b': {'c': 1}}})
            finally:
                visitor.TreeInterpreter.__init__ = original_init

            self.assertEqual(result, 1)
            self.assertEqual(len(created), 1)
            # No gc.collect() here on purpose: if there were still a
            # reference cycle, the interpreter would still be alive at
            # this point even though nothing outside this test holds a
            # reference to it any more.
            self.assertIsNone(
                created[0](),
                "TreeInterpreter survived past its last external "
                "reference without a gc.collect(), which means its "
                "method cache is holding a reference cycle again.")
        finally:
            gc.enable()

    def test_visit_still_dispatches_correctly_after_caching(self):
        # The fix changes *what* gets stored in _method_cache (a plain
        # function looked up on the class instead of a bound method on
        # the instance), so repeat this a few times to make sure
        # dispatch through the cached entry still reaches the right
        # subclass-specific visit_* implementation.
        for _ in range(3):
            self.assertEqual(
                jmespath.search('a.b.c', {'a': {'b': {'c': 42}}}), 42)
        self.assertEqual(
            jmespath.search('foo[*].bar', {'foo': [{'bar': 1}, {'bar': 2}]}),
            [1, 2])
