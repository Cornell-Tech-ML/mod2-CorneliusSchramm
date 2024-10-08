from __future__ import annotations

import random
from typing import Iterable, Optional, Sequence, Tuple, Union

import numba
import numba.cuda
import numpy as np
import numpy.typing as npt
from numpy import array, float64
from typing_extensions import TypeAlias

from .operators import prod

MAX_DIMS = 32


class IndexingError(RuntimeError):
    """Exception raised for indexing errors."""

    pass


Storage: TypeAlias = npt.NDArray[np.float64]
OutIndex: TypeAlias = npt.NDArray[np.int32]
Index: TypeAlias = npt.NDArray[np.int32]
Shape: TypeAlias = npt.NDArray[np.int32]
Strides: TypeAlias = npt.NDArray[np.int32]

UserIndex: TypeAlias = Sequence[int]
UserShape: TypeAlias = Sequence[int]
UserStrides: TypeAlias = Sequence[int]


def index_to_position(index: Index, strides: Strides) -> int:
    """Converts a multidimensional tensor `index` into a single-dimensional position in
    storage based on strides.

    Args:
    ----
        index : index tuple of ints
        strides : tensor strides

    Returns:
    -------
        Position in storage

    """
    # TODO: Implement for Task 2.1.
    if len(index) != len(strides):
        raise IndexingError(f"Index {index} must have same length as strides {strides}")
    position = sum(index * stride for index, stride in zip(index, strides))
    return position


def to_index(ordinal: int, shape: Shape, out_index: OutIndex) -> None:
    """Convert an `ordinal` to an index in the `shape`.
    Should ensure that enumerating position 0 ... size of a
    tensor produces every index exactly once. It
    may not be the inverse of `index_to_position`.

    Args:
    ----
        ordinal: ordinal position to convert.
        shape : tensor shape.
        out_index : return index corresponding to position.

    """
    # TODO: Implement for Task 2.1.
    # Calculate strides
    for i in range(len(shape) - 1, -1, -1):
        out_index[i] = ordinal % shape[i]
        ordinal = ordinal // shape[i]

    # raise NotImplementedError("Need to implement for Task 2.1") 


# def broadcast_index(
#     big_index: Index, big_shape: Shape, shape: Shape, out_index: OutIndex
# ) -> None:
#     """Convert a `big_index` into `big_shape` to a smaller `out_index`
#     into `shape` following broadcasting rules. In this case
#     it may be larger or with more dimensions than the `shape`
#     given. Additional dimensions may need to be mapped to 0 or
#     removed.

#     Args:
#     ----
#         big_index : multidimensional index of bigger tensor
#         big_shape : tensor shape of bigger tensor
#         shape : tensor shape of smaller tensor
#         out_index : multidimensional index of smaller tensor

#     Returns:
#     -------
#         None

#     """
#     # Ensure shape is not empty
#     print("shape:", shape)
#     print("big_shape:", big_shape)
#     print("big_index:", big_index)
#     print("out_index:", out_index)
#     if len(shape) == 0:
#         return
#     # Pad shape if necessary
#     pad_amount = len(big_shape) - len(shape)
#     padded_shape = (1,) * pad_amount + shape

#     # Check for broadcasting compatibility
#     for dim in range(len(big_shape)):
#         if padded_shape[dim] != 1 and padded_shape[dim] != big_shape[dim]:
#             raise ValueError(
#                 f"Shapes {big_shape} and {shape} are not broadcast-compatible."
#             )

#     # Map indices correctly by aligning dimensions from the right
#     for dim in range(len(shape)):
#         big_dim = dim + pad_amount
#         if padded_shape[big_dim] > 1:
#             out_index[dim] = big_index[big_dim]
#         else:
#             out_index[dim] = 0


#     # raise NotImplementedError("Need to implement for Task 2.2")
def broadcast_index(
    big_index: Index, big_shape: Shape, shape: Shape, out_index: OutIndex
) -> None:
    """Convert a `big_index` into `big_shape` to a smaller `out_index`
    into `shape` following broadcasting rules. In this case
    it may be larger or with more dimensions than the `shape`
    given. Additional dimensions may need to be mapped to 0 or
    removed.

    Args:
    ----
        big_index : multidimensional index of bigger tensor
        big_shape : tensor shape of bigger tensor
        shape : tensor shape of smaller tensor
        out_index : multidimensional index of smaller tensor

    Returns:
    -------
        None

    """
    # Debugging Statements
    print("shape:", shape)
    print("big_shape:", big_shape)
    print("big_index:", big_index)
    print("out_index:", out_index)
    
    if len(shape) == 0:
        # If the smaller tensor is a scalar, no need to modify out_index
        return
    
    pad_amount = len(big_shape) - len(shape)
    
    if pad_amount < 0:
        raise ValueError("big_shape must have at least as many dimensions as shape")
    
    # Create padded_shape by prepending 1s to match the number of dimensions
    padded_shape = np.concatenate((np.ones(pad_amount, dtype=shape.dtype), shape))
    
    # Check for broadcasting compatibility
    for dim in range(len(big_shape)):
        if padded_shape[dim] != 1 and padded_shape[dim] != big_shape[dim]:
            raise ValueError(
                f"Shapes {big_shape} and {shape} are not broadcast-compatible."
            )
    
    # Map indices correctly by aligning dimensions from the right
    for dim in range(len(shape)):
        big_dim = dim + pad_amount
        if padded_shape[big_dim] > 1:
            out_index[dim] = big_index[big_dim]
        else:
            out_index[dim] = 0

def shape_broadcast(shape1: UserShape, shape2: UserShape) -> UserShape:
    """Broadcast two shapes to create a new union shape.

    Args:
    ----
        shape1 : first shape
        shape2 : second shape

    Returns:
    -------
        broadcasted shape

    Raises:
    ------
        IndexingError : if cannot broadcast

    """
    # TODO: Implement for Task 2.2.

    # check if padding needed
    number_of_dims1 = len(shape1)
    number_of_dims2 = len(shape2)

    if number_of_dims1 != number_of_dims2:
        dims_to_pad = abs(number_of_dims1 - number_of_dims2)
        if number_of_dims1 < number_of_dims2:
            shape1 = tuple(1 for _ in range(dims_to_pad)) + tuple(shape1)
        else:
            shape2 = tuple(1 for _ in range(dims_to_pad)) + tuple(shape2)

    # check if indexing error
    broadcasted_shape = []
    for dim1, dim2 in zip(shape1, shape2):
        if dim1 != dim2 and not (dim1 == 1 or dim2 == 1):
            raise IndexingError(f"Cannot broadcast shapes {shape1} and {shape2}")
        broadcasted_shape.append(max(dim1, dim2))
    return tuple(broadcasted_shape)
    
    # Alternative / more elegant
    #   # Pad shorter shape with 1s
    # s1, s2 = shape1[::-1], shape2[::-1]
    # max_len = max(len(s1), len(s2))
    # s1 = s1 + (1,) * (max_len - len(s1))
    # s2 = s2 + (1,) * (max_len - len(s2))

    # # Create broadcasted shape
    # try:
    #     broadcasted = tuple(max(d1, d2) if d1 == 1 or d2 == 1 or d1 == d2 else 
    #                         raise IndexingError(f"Incompatible dimensions {d1} and {d2}")
    #                         for d1, d2 in zip(s1, s2))
    # except IndexingError as e:
    #     raise IndexingError(f"Cannot broadcast shapes {shape1} and {shape2}: {str(e)}")

    # return broadcasted[::-1]  

    # raise NotImplementedError("Need to implement for Task 2.2")


def strides_from_shape(shape: UserShape) -> UserStrides:
    """Return a contiguous stride for a shape"""
    layout = [1]
    offset = 1
    for s in reversed(shape):
        layout.append(s * offset)
        offset = s * offset
    return tuple(reversed(layout[:-1]))


class TensorData:
    _storage: Storage
    _strides: Strides
    _shape: Shape
    strides: UserStrides
    shape: UserShape
    dims: int

    def __init__(
        self,
        storage: Union[Sequence[float], Storage],
        shape: UserShape,
        strides: Optional[UserStrides] = None,
    ):
        if isinstance(storage, np.ndarray):
            self._storage = storage
        else:
            self._storage = array(storage, dtype=float64)

        if strides is None:
            strides = strides_from_shape(shape)

        assert isinstance(strides, tuple), "Strides must be tuple"
        assert isinstance(shape, tuple), "Shape must be tuple"
        if len(strides) != len(shape):
            raise IndexingError(f"Len of strides {strides} must match {shape}.")
        self._strides = array(strides)
        self._shape = array(shape)
        self.strides = strides
        self.dims = len(strides)
        self.size = int(prod(shape))
        self.shape = shape
        assert len(self._storage) == self.size

    def to_cuda_(self) -> None:  # pragma: no cover
        """Convert to cuda"""
        if not numba.cuda.is_cuda_array(self._storage):
            self._storage = numba.cuda.to_device(self._storage)

    def is_contiguous(self) -> bool:
        """Check that the layout is contiguous, i.e. outer dimensions have bigger strides than inner dimensions.

        Returns
        -------
            bool : True if contiguous

        """
        last = 1e9
        for stride in self._strides:
            if stride > last:
                return False
            last = stride
        return True

    @staticmethod
    def shape_broadcast(shape_a: UserShape, shape_b: UserShape) -> UserShape:
        return shape_broadcast(shape_a, shape_b)

    def index(self, index: Union[int, UserIndex]) -> int:
        if isinstance(index, int):
            aindex: Index = array([index])
        else:  # if isinstance(index, tuple):
            aindex = array(index)

        # Pretend 0-dim shape is 1-dim shape of singleton
        shape = self.shape
        if len(shape) == 0 and len(aindex) != 0:
            shape = (1,)

        # Check for errors
        if aindex.shape[0] != len(self.shape):
            raise IndexingError(f"Index {aindex} must be size of {self.shape}.")
        for i, ind in enumerate(aindex):
            if ind >= self.shape[i]:
                raise IndexingError(f"Index {aindex} out of range {self.shape}.")
            if ind < 0:
                raise IndexingError(f"Negative indexing for {aindex} not supported.")

        # Call fast indexing.
        return index_to_position(array(index), self._strides)

    def indices(self) -> Iterable[UserIndex]:
        lshape: Shape = array(self.shape)
        out_index: Index = array(self.shape)
        for i in range(self.size):
            to_index(i, lshape, out_index)
            yield tuple(out_index)

    def sample(self) -> UserIndex:
        """Get a random valid index"""
        return tuple((random.randint(0, s - 1) for s in self.shape))

    def get(self, key: UserIndex) -> float:
        x: float = self._storage[self.index(key)]
        return x

    def set(self, key: UserIndex, val: float) -> None:
        self._storage[self.index(key)] = val

    def tuple(self) -> Tuple[Storage, Shape, Strides]:
        """Return core tensor data as a tuple."""
        return (self._storage, self._shape, self._strides)

    def permute(self, *order: int) -> TensorData:
        """Permute the dimensions of the tensor.

        Args:
        ----
            *order: a permutation of the dimensions

        Returns:
        -------
            New `TensorData` with the same storage and a new dimension order.

        """
        assert list(sorted(order)) == list(
            range(len(self.shape))
        ), f"Must give a position to each dimension. Shape: {self.shape} Order: {order}"

        # TODO: Implement for Task 2.1.
        if order == tuple(range(len(self.shape))):
            return self
        new_shape = tuple(self.shape[i] for i in order)
        new_strides = tuple(self.strides[i] for i in order)
        return TensorData(
            self._storage,  
            new_shape,      
            new_strides    
        )
        

    def to_string(self) -> str:
        """Convert to string"""
        s = ""
        for index in self.indices():
            l = ""
            for i in range(len(index) - 1, -1, -1):
                if index[i] == 0:
                    l = "\n%s[" % ("\t" * i) + l
                else:
                    break
            s += l
            v = self.get(index)
            s += f"{v:3.2f}"
            l = ""
            for i in range(len(index) - 1, -1, -1):
                if index[i] == self.shape[i] - 1:
                    l += "]"
                else:
                    break
            if l:
                s += l
            else:
                s += " "
        return s
