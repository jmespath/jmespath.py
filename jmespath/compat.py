import sys

PY2 = sys.version_info[0] == 2

if PY2:
    def with_str_method(cls):
        """Class decorator that handles __str__ compat between py2 and py3."""
        # In python2, the __str__ should be __unicode__
        # and __str__ should return bytes.
        cls.__unicode__ = cls.__str__
        def __str__(self):
            return self.__unicode__().encode('utf-8')
        cls.__str__ = __str__
        return cls
else:
    def with_str_method(cls):
        # In python3, we don't need to do anything, we return a str type.
        return cls
