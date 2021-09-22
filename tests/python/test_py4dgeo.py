import py4dgeo

import numpy as np
import os
import pytest


_test_files = [
    os.path.join(os.path.split(__file__)[0], "../data/plane_horizontal_t1.xyz")
]


@pytest.mark.parametrize("filename", _test_files)
def test_kdtree(filename):
    data = np.genfromtxt(filename)
    tree = py4dgeo.KDTree(data)
    tree.build_tree(10)
    result = tree.radius_search(np.array([0, 0, 0]), 100)
    assert result.shape[0] == data.shape[0]
