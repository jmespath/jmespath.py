import astropy.units as u
import dask.array as da
import numpy as np
import xarray as xr
from parameterized import parameterized, parameterized_class

import jmespath
import jmespath.functions
from tests import unittest


@parameterized_class(("name", "data"), [
    ("list", {
        "value": {
            "data": [[1,2,3],[4,5,6],[7,8,9]]
        },
        "same": {
            "data": [[1,2,3],[4,5,6],[7,8,9]]
        },
        "other": {
            "data": [[2,2,3],[4,5,6],[7,8,9]]
        }
    }),
    ("tuple", {
        "value": {
            "data": ((1,2,3),(4,5,6),(7,8,9))
        },
        "same": {
            "data": ([1,2,3],[4,5,6],[7,8,9])
        },
        "other": {
            "data": [[2,2,3],[4,5,6],[7,8,9]]
        }
    }),
    ("numpy", {
        "value": {
            "data": np.array([[1,2,3],[4,5,6],[7,8,9]])
        },
        "same": {
            "data": (np.array([1,2,3]),np.array([4,5,6]),np.array([7,8,9]))
        },
        "other": {
            "data": np.array([[2,2,3],[4,5,6],[7,8,9]])
        }
    }),
    ("dask", {
        "value": {
            "data": da.from_array([[1,2,3],[4,5,6],[7,8,9]])
        },
        "same": {
            "data": (da.from_array([1,2,3]),da.from_array([4,5,6]),da.from_array([7,8,9]))
        },
        "other": {
            "data": da.from_array([[2,2,3],[4,5,6],[7,8,9]])
        }
    }),
    ("xarray", {
        "value": {
            "data": xr.DataArray([[1,2,3],[4,5,6],[7,8,9]])
        },
        "same": {
            "data": (xr.DataArray([1,2,3]),xr.DataArray([4,5,6]),xr.DataArray([7,8,9]))
        },
        "other": {
            "data": xr.DataArray([[2,2,3],[4,5,6],[7,8,9]])
        }
    }),
    ("astropy", {
        "value": {
            "data": u.Quantity([[1,2,3],[4,5,6],[7,8,9]])
        },
        "same": {
            "data": (u.Quantity([1,2,3]),u.Quantity([4,5,6]),u.Quantity([7,8,9]))
        },
        "other": {
            "data": u.Quantity([[2,2,3],[4,5,6],[7,8,9]])
        }
    }),
])
class TestArrayNumeric(unittest.TestCase):
    @parameterized.expand([
        ["self", "@", lambda data: data],
        ["get", "value.data", lambda data: data["value"]["data"]],
        ["slice_horizontal", "value.data[1][:]", lambda data: np.array(data["value"]["data"])[1,:]],
        ["slice_horizontal2", "value.data[:3:2][:]", lambda data: np.array(data["value"]["data"])[:3:2,:]],
        ["slice_vertical", "value.data[:][1]", lambda data: np.array(data["value"]["data"])[:,1]],
        ["slice_vertical2", "value.data[:][:3:2]", lambda data: np.array(data["value"]["data"])[:,:3:2]],
        ["flatten", "value.data[]", lambda data: np.array(data["value"]["data"]).flatten()],
        ["compare_self", "value.data == value.data", lambda _: True],
        ["compare_same", "value.data == same.data", lambda _: True],
        ["compare_other", "value.data == other.data", lambda _: False],
        ["compare_literal_scalar", "value.data[0][0] == `1`", lambda _: True],
        ["compare_literal_slice", "value.data[1][:] == `[4, 5, 6]`", lambda _: True],
        ["compare_literal", "value.data == `[[1,2,3],[4,5,6],[7,8,9]]`", lambda _: True],
        ["compare_flattened", "value.data[] == `[1,2,3,4,5,6,7,8,9]`", lambda _: True],
    ])
    def test_search(self, test_name, query, expected):
        result = jmespath.search(query, self.data)
        np.testing.assert_array_equal(result, expected(self.data), test_name)


@parameterized_class(("name", "data"), [
    ("numpy", {
        "value": { 
            "data": np.array([["test", "messages"],["in", "numpy"]])
        },
        "same": { 
            "data": np.array([["test", "messages"],["in", "numpy"]])
        },
        "other": { 
            "data": np.array([["test", "messages"],["other", "numpy"]])
        }
    })
])
class TestArrayStr(unittest.TestCase):
    @parameterized.expand([
        ["self", "@", lambda data: data],
        ["get", "value.data", lambda data: data["value"]["data"]],
        ["slice_horizontal", "value.data[1][:]", lambda data: data["value"]["data"][1,:]],
        ["slice_vertical", "value.data[:][1]", lambda data: data["value"]["data"][:,1]],
        ["flatten", "value.data[]", lambda data: data["value"]["data"].flatten()],
        ["compare_self", "value.data == value.data", lambda _: True],
        ["compare_same", "value.data == same.data", lambda _: True],
        ["compare_other", "value.data == other.data", lambda _: False],
        ["compare_literal_scalar", "value.data[0][0] == 'test'", lambda _: True],
        ["compare_literal_slice", "value.data[1][:] == ['in', 'numpy']", lambda _: True],
        ["compare_literal", "value.data == [['test', 'messages'],['in', 'numpy']]", lambda _: True],
        ["compare_flattened", "value.data[] == ['test', 'messages', 'in', 'numpy']", lambda _: True],
    ])
    def test_search(self, name, query, expected):
        result = jmespath.search(query, self.data)
        np.testing.assert_array_equal(result, expected(self.data), name)
