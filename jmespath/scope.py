from collections import deque


class ScopedChainDict:
    """Dictionary that can delegate lookups to multiple dicts.

    This provides a basic get/set dict interface that is
    backed by multiple dicts.  Each dict is searched from
    the top most (most recently pushed) scope dict until
    a match is found.

    """
    def __init__(self, *scopes):
        # The scopes are evaluated starting at the top of the stack (the most
        # recently pushed scope via .push_scope()).  If we use a normal list()
        # and push/pop scopes by adding/removing to the end of the list, we'd
        # have to always call reversed(self._scopes) whenever we resolve a key,
        # because the end of the list is the top of the stack.
        # To avoid this, we're using a deque so we can append to the front of
        # the list via .appendleft() in constant time, and iterate over scopes
        # without having to do so with a reversed() call each time.
        self._scopes = deque(scopes)

    def __getitem__(self, key):
        for scope in self._scopes:
            if key in scope:
                return scope[key]
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def push_scope(self, scope):
        self._scopes.appendleft(scope)

    def pop_scope(self):
        self._scopes.popleft()
