import inspect

iteritems = dict.items

map = map
text_type = str
string_type = str


def with_str_method(cls):
    # In python3, we don't need to do anything, we return a str type.
    return cls

def with_repr_method(cls):
    return cls

def get_methods(cls):
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        yield name, method
