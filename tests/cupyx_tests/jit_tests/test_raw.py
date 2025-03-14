import unittest
import numpy

import pytest

import cupy
import cupyx
from cupyx import jit
from cupy import testing


class TestRaw(unittest.TestCase):

    def test_raw_grid_1D(self):
        @jit.rawkernel()
        def f(arr1, arr2):
            x = jit.grid(1)
            if x < arr1.size:
                arr2[x] = arr1[x]

        x = cupy.arange(10)
        y = cupy.empty_like(x)
        f((1,), (10,), (x, y))
        assert (x == y).all()

    def test_raw_grid_2D(self):
        @jit.rawkernel()
        def f(arr1, arr2, n, m):
            x, y = jit.grid(2)
            # TODO(leofang): make it possible to write this:
            # if x < arr1.shape[0] and y < arr1.shape[1]:
            if x < n and y < m:
                arr2[x, y] = arr1[x, y]

        x = cupy.arange(20).reshape(4, 5)
        y = cupy.empty_like(x)
        f((1,), (4, 5), (x, y, x.shape[0], x.shape[1]))
        assert (x == y).all()

    def test_raw_grid_3D(self):
        @jit.rawkernel()
        def f(arr1, arr2, k, m, n):
            x, y, z = jit.grid(3)
            if x < k and y < m and z < n:
                arr2[x, y, z] = arr1[x, y, z]

        l, m, n = (2, 3, 4)
        x = cupy.arange(24).reshape(l, m, n)
        y = cupy.empty_like(x)
        f(((l+1)//2, (m+1)//2, (n+1)//2), (2, 2, 2), (x, y, l, m, n))
        assert (x == y).all()

    def test_raw_grid_invalid1(self):
        @jit.rawkernel()
        def f():
            x, = jit.grid(1)  # cannot unpack an int

        with pytest.raises(ValueError):
            f((1,), (1,), ())

    def test_raw_grid_invalid2(self):
        @jit.rawkernel()
        def f():
            x = jit.grid(2)
            y = cupy.int64(x)  # <- x is a tuple  # NOQA

        # we don't care the exception type as long as something is raised
        with pytest.raises(Exception):
            f((1,), (1,), ())

    def test_raw_grid_invalid3(self):
        for n in (0, 4, 'abc', [0], (1,)):
            @jit.rawkernel()
            def f():
                x = jit.grid(n)  # n can only be 1, 2, 3 (as int)  # NOQA

            err = ValueError if isinstance(n, int) else TypeError
            with pytest.raises(err):
                f((1,), (1,), ())

    def test_raw_one_thread(self):
        @jit.rawkernel()
        def f(x, y):
            y[0] = x[0]

        x = cupy.array([10], dtype=numpy.int32)
        y = cupy.array([20], dtype=numpy.int32)
        f((1,), (1,), (x, y))
        assert int(y[0]) == 10

    def test_raw_elementwise_single_op(self):
        @jit.rawkernel()
        def f(x, y):
            tid = jit.threadIdx.x + jit.blockDim.x * jit.blockIdx.x
            y[tid] = x[tid]

        x = testing.shaped_random((30,), dtype=numpy.int32, seed=0)
        y = testing.shaped_random((30,), dtype=numpy.int32, seed=1)
        f((5,), (6,), (x, y))
        assert bool((x == y).all())

    def test_raw_elementwise_loop(self):
        @jit.rawkernel()
        def f(x, y, size):
            tid = jit.threadIdx.x + jit.blockDim.x * jit.blockIdx.x
            ntid = jit.blockDim.x * jit.gridDim.x
            for i in range(tid, size, ntid):
                y[i] = x[i]

        x = testing.shaped_random((1024,), dtype=numpy.int32, seed=0)
        y = testing.shaped_random((1024,), dtype=numpy.int32, seed=1)
        f((5,), (6,), (x, y, numpy.uint32(1024)))
        assert bool((x == y).all())

    def test_raw_multidimensional_array(self):
        @jit.rawkernel()
        def f(x, y, n_row, n_col):
            tid = jit.threadIdx.x + jit.blockDim.x * jit.blockIdx.x
            ntid = jit.blockDim.x * jit.gridDim.x
            size = n_row * n_col
            for i in range(tid, size, ntid):
                i_row = i // n_col
                i_col = i % n_col
                y[i_row, i_col] = x[i_row, i_col]

        n, m = numpy.uint32(12), numpy.uint32(13)
        x = testing.shaped_random((n, m), dtype=numpy.int32, seed=0)
        y = testing.shaped_random((n, m), dtype=numpy.int32, seed=1)
        f((5,), (6,), (x, y, n, m))
        assert bool((x == y).all())

    def test_raw_multidimensional_array_with_attr(self):
        @jit.rawkernel()
        def f(x, y):
            tid = jit.threadIdx.x + jit.blockDim.x * jit.blockIdx.x
            ntid = jit.blockDim.x * jit.gridDim.x
            n_col = x.size // len(x)
            for i in range(tid, x.size, ntid):
                i_row = i // n_col
                i_col = i % n_col
                y[i_row, i_col] = x[i_row, i_col]

        n, m = numpy.uint32(12), numpy.uint32(13)
        x = testing.shaped_random((n, m), dtype=numpy.int32, seed=0)
        y = testing.shaped_random((n, m), dtype=numpy.int32, seed=1)
        f((5,), (6,), (x, y))
        assert bool((x == y).all())

    def test_raw_ndim(self):
        @jit.rawkernel()
        def f(x, y):
            y[0] = x.ndim

        x = cupy.empty((1, 1, 1, 1, 1, 1, 1), dtype=numpy.int32)
        y = cupy.zeros((1,), dtype=numpy.int64)
        f((1,), (1,), (x, y))
        assert y.item() == 7

    def test_raw_0dim_array(self):
        @jit.rawkernel()
        def f(x, y):
            y[()] = x[()]

        x = testing.shaped_random((), dtype=numpy.int32, seed=0)
        y = testing.shaped_random((), dtype=numpy.int32, seed=1)
        f((1,), (1,), (x, y))
        assert bool((x == y).all())

    def test_min(self):
        @jit.rawkernel()
        def f(x, y, z, r):
            tid = jit.blockDim.x * jit.blockIdx.x + jit.threadIdx.x
            r[tid] = min(x[tid], y[tid], z[tid])

        x = testing.shaped_random((1024,), dtype=numpy.int32, seed=0)
        y = testing.shaped_random((1024,), dtype=numpy.int32, seed=1)
        z = testing.shaped_random((1024,), dtype=numpy.int32, seed=2)
        r = testing.shaped_random((1024,), dtype=numpy.int32, seed=3)
        f((8,), (128,), (x, y, z, r))
        expected = cupy.minimum(x, cupy.minimum(y, z))
        assert bool((r == expected).all())

    def test_max(self):
        @jit.rawkernel()
        def f(x, y, z, r):
            tid = jit.blockDim.x * jit.blockIdx.x + jit.threadIdx.x
            r[tid] = max(x[tid], y[tid], z[tid])

        x = testing.shaped_random((1024,), dtype=numpy.int32, seed=0)
        y = testing.shaped_random((1024,), dtype=numpy.int32, seed=1)
        z = testing.shaped_random((1024,), dtype=numpy.int32, seed=2)
        r = testing.shaped_random((1024,), dtype=numpy.int32, seed=3)
        f((8,), (128,), (x, y, z, r))
        expected = cupy.maximum(x, cupy.maximum(y, z))
        assert bool((r == expected).all())

    def test_syncthreads(self):
        @jit.rawkernel()
        def f(x, y, buf):
            tid = jit.threadIdx.x + jit.threadIdx.y * jit.blockDim.x
            ntid = jit.blockDim.x * jit.blockDim.y
            buf[tid] = x[ntid - tid - 1]
            jit.syncthreads()
            y[tid] = buf[ntid - tid - 1]

        x = testing.shaped_random((1024,), dtype=numpy.int32, seed=0)
        y = testing.shaped_random((1024,), dtype=numpy.int32, seed=1)
        buf = testing.shaped_random((1024,), dtype=numpy.int32, seed=2)
        f((1,), (32, 32), (x, y, buf))
        assert bool((x == y).all())

    def test_shared_memory_static(self):
        @jit.rawkernel()
        def f(x, y):
            tid = jit.threadIdx.x
            ntid = jit.blockDim.x
            bid = jit.blockIdx.x
            i = tid + bid * ntid

            smem = jit.shared_memory(numpy.int32, 32)
            smem[tid] = x[i]
            jit.syncthreads()
            y[i] = smem[ntid - tid - 1]

        x = testing.shaped_random((1024,), dtype=numpy.int32, seed=0)
        y = testing.shaped_random((1024,), dtype=numpy.int32, seed=1)
        f((32,), (32,), (x, y))
        expected = x.reshape(32, 32)[:, ::-1].ravel()
        assert bool((y == expected).all())

    def test_shared_memory_dynamic(self):
        @jit.rawkernel()
        def f(x, y):
            tid = jit.threadIdx.x
            ntid = jit.blockDim.x
            bid = jit.blockIdx.x
            i = tid + bid * ntid

            smem = jit.shared_memory(numpy.int32, None)
            smem[tid] = x[i]
            jit.syncthreads()
            y[i] = smem[ntid - tid - 1]

        x = testing.shaped_random((1024,), dtype=numpy.int32, seed=0)
        y = testing.shaped_random((1024,), dtype=numpy.int32, seed=1)
        f((32,), (32,), (x, y), shared_mem=128)
        expected = x.reshape(32, 32)[:, ::-1].ravel()
        assert bool((y == expected).all())

    @staticmethod
    def _check(a, e):
        if a.dtype == numpy.float16:
            testing.assert_allclose(a, e, rtol=3e-2, atol=3e-2)
        else:
            testing.assert_allclose(a, e, rtol=1e-5, atol=1e-5)

    @testing.for_dtypes('iILQefd')
    def test_atomic_add(self, dtype):
        @jit.rawkernel()
        def f(x, index, out):
            tid = jit.blockDim.x * jit.blockIdx.x + jit.threadIdx.x
            jit.atomic_add(out, index[tid], x[tid])

        x = testing.shaped_random((1024,), dtype=dtype, seed=0)
        index = testing.shaped_random(
            (1024,), dtype=numpy.bool_, seed=1).astype(numpy.int32)
        out = cupy.zeros((2,), dtype=dtype)
        f((32,), (32,), (x, index, out))

        expected = cupy.zeros((2,), dtype=dtype)
        cupyx.scatter_add(expected, index, x)
        self._check(out, expected)

    def test_raw_grid_block_interface(self):
        @jit.rawkernel()
        def f(x, y, size):
            tid = jit.threadIdx.x + jit.blockDim.x * jit.blockIdx.x
            ntid = jit.blockDim.x * jit.gridDim.x
            for i in range(tid, size, ntid):
                y[i] = x[i]

        x = testing.shaped_random((1024,), dtype=numpy.int32, seed=0)
        y = testing.shaped_random((1024,), dtype=numpy.int32, seed=1)
        f[5, 6](x, y, numpy.uint32(1024))
        assert bool((x == y).all())

    def test_error_msg(self):
        @jit.rawkernel()
        def f(x):
            return unknown_var  # NOQA

        import re
        mes = re.escape('''Unbound name: unknown_var

  @jit.rawkernel()
  def f(x):
>     return unknown_var  # NOQA
''')
        x = cupy.zeros((10,), dtype=numpy.float32)
        with pytest.raises(NameError, match=mes):
            f((1,), (1,), (x,))
