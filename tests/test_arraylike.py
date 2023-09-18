import numpy as np
import xarray as xr
from parameterized import parameterized, parameterized_class

import jmespath
import jmespath.functions
from tests import unittest


@parameterized_class(("name", "data"), [
    ("list", {
        "a": {
            "data": [[1,2,3],[4,5,6],[7,8,9]]
        },
        "b": {
            "data": [[1,2,3],[4,5,6],[7,8,9]]
        },
        "c": {
            "data": [[2,2,3],[4,5,6],[7,8,9]]
        }
    }),
    ("numpy", {
        "a": {
            "data": np.array([[1,2,3],[4,5,6],[7,8,9]])
        },
        "b": {
            "data": np.array([[1,2,3],[4,5,6],[7,8,9]], dtype='int16')
        },
        "c": {
            "data": np.array([[2,2,3],[4,5,6],[7,8,9]])
        }
    }),
    ("xarray", {
        "a": {
            "data": xr.DataArray([[1,2,3],[4,5,6],[7,8,9]])
        },
        "b": {
            "data": xr.DataArray([[1,2,3],[4,5,6],[7,8,9]])
        },
        "c": {
            "data": xr.DataArray([[2,2,3],[4,5,6],[7,8,9]])
        }
    })
])
class TestArrayNumeric(unittest.TestCase):
    @parameterized.expand([
        ["self", "@", lambda data: data],
        ["get", "a.data", lambda data: data["a"]["data"]],
        ["slice_horizontal", "a.data[1][:]", lambda data: np.array(data["a"]["data"])[1,:]],
        ["slice_horizontal2", "a.data[:3:2][:]", lambda data: np.array(data["a"]["data"])[:3:2,:]],
        ["slice_vertical", "a.data[:][1]", lambda data: np.array(data["a"]["data"])[:,1]],
        ["slice_vertical2", "a.data[:][:3:2]", lambda data: np.array(data["a"]["data"])[:,:3:2]],
        ["flatten", "a.data[]", lambda data: np.array(data["a"]["data"]).flatten()],
        ["compare_self", "a.data == a.data", lambda _: True],
        ["compare_same", "a.data == b.data", lambda _: True],
        ["compare_other", "a.data == c.data", lambda _: False],
        ["compare_literal_scalar", "a.data[0][0] == `1`", lambda _: True],
        ["compare_literal_slice", "a.data[1][:] == `[4, 5, 6]`", lambda _: True],
        ["compare_literal", "a.data == `[[1,2,3],[4,5,6],[7,8,9]]`", lambda _: True],
        ["compare_flattened", "a.data[] == `[1,2,3,4,5,6,7,8,9]`", lambda _: True],
    ])
    def test_search(self, test_name, query, expected):
        result = jmespath.search(query, self.data)
        np.testing.assert_array_equal(result, expected(self.data), test_name)


@parameterized_class(("name", "data"), [
    ("numpy", {
        "a": { 
            "data": np.array([["test", "messages"],["in", "numpy"]])
        },
        "b": { 
            "data": np.array([["test", "messages"],["in", "numpy"]])
        },
        "c": { 
            "data": np.array([["test", "messages"],["other", "numpy"]])
        }
    })
])
class TestArrayStr(unittest.TestCase):
    @parameterized.expand([
        ["self", "@", lambda data: data],
        ["get", "a.data", lambda data: data["a"]["data"]],
        ["slice_horizontal", "a.data[1][:]", lambda data: data["a"]["data"][1,:]],
        ["slice_vertical", "a.data[:][1]", lambda data: data["a"]["data"][:,1]],
        ["flatten", "a.data[]", lambda data: data["a"]["data"].flatten()],
        ["compare_self", "a.data == a.data", lambda _: True],
        ["compare_same", "a.data == b.data", lambda _: True],
        ["compare_other", "a.data == c.data", lambda _: False],
        ["compare_literal_scalar", "a.data[0][0] == 'test'", lambda _: True],
        ["compare_literal_slice", "a.data[1][:] == ['in', 'numpy']", lambda _: True],
        ["compare_literal", "a.data == [['test', 'messages'],['in', 'numpy']]", lambda _: True],
        ["compare_flattened", "a.data[] == ['test', 'messages', 'in', 'numpy']", lambda _: True],
    ])
    def test_search(self, name, query, expected):
        result = jmespath.search(query, self.data)
        np.testing.assert_array_equal(result, expected(self.data), name)
