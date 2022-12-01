from typing import Tuple

import torch

from torch_sparse import SparseTensor


def spmm_sum(src: SparseTensor, other: torch.Tensor) -> torch.Tensor:
    rowptr, col, value = src.csr()

    row = src.storage._row # COO rowindx
    csr2csc = src.storage._csr2csc
    colptr = src.storage._colptr

    if value is not None:
        value = value.to(other.dtype)

    if value is not None and value.requires_grad: # sparse value grad
        row = src.storage.row()

    if other.requires_grad: # dense grad
        row = src.storage.row()
        csr2csc = src.storage.csr2csc()
        colptr = src.storage.colptr()

    return torch.ops.torch_sparse.spmm_sum(row, rowptr, col, value, colptr,
                                           csr2csc, other)


def spmm_add(src: SparseTensor, other: torch.Tensor) -> torch.Tensor:
    return spmm_sum(src, other)


def spmm_mean(src: SparseTensor, other: torch.Tensor) -> torch.Tensor:
    rowptr, col, value = src.csr()

    row = src.storage._row
    rowcount = src.storage._rowcount
    csr2csc = src.storage._csr2csc
    colptr = src.storage._colptr

    if value is not None:
        value = value.to(other.dtype)

    if value is not None and value.requires_grad:
        row = src.storage.row()

    if other.requires_grad:
        row = src.storage.row()
        rowcount = src.storage.rowcount()
        csr2csc = src.storage.csr2csc()
        colptr = src.storage.colptr()

    return torch.ops.torch_sparse.spmm_mean(row, rowptr, col, value, rowcount,
                                            colptr, csr2csc, other)


def spmm_min(src: SparseTensor,
             other: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    rowptr, col, value = src.csr()

    if value is not None:
        value = value.to(other.dtype)

    return torch.ops.torch_sparse.spmm_min(rowptr, col, value, other)


def spmm_max(src: SparseTensor,
             other: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    rowptr, col, value = src.csr()

    if value is not None:
        value = value.to(other.dtype)

    return torch.ops.torch_sparse.spmm_max(rowptr, col, value, other)


def spmm(src: SparseTensor, other: torch.Tensor,
         reduce: str = "sum") -> torch.Tensor:
    if reduce == 'sum' or reduce == 'add':
        return spmm_sum(src, other)
    elif reduce == 'mean':
        return spmm_mean(src, other)
    elif reduce == 'min':
        return spmm_min(src, other)[0]
    elif reduce == 'max':
        return spmm_max(src, other)[0]
    else:
        raise ValueError


def spspmm_sum(src: SparseTensor, other: SparseTensor) -> SparseTensor:
    assert src.sparse_size(1) == other.sparse_size(0)
    rowptrA, colA, valueA = src.csr()
    rowptrB, colB, valueB = other.csr()
    value = valueA if valueA is not None else valueB
    if valueA is not None and valueA.dtype == torch.half:
        valueA = valueA.to(torch.float)
    if valueB is not None and valueB.dtype == torch.half:
        valueB = valueB.to(torch.float)
    M, K = src.sparse_size(0), other.sparse_size(1)
    rowptrC, colC, valueC = torch.ops.torch_sparse.spspmm_sum(
        rowptrA, colA, valueA, rowptrB, colB, valueB, K)
    if valueC is not None and value is not None:
        valueC = valueC.to(value.dtype)
    return SparseTensor(row=None, rowptr=rowptrC, col=colC, value=valueC,
                        sparse_sizes=(M, K), is_sorted=True)


def spspmm_add(src: SparseTensor, other: SparseTensor) -> SparseTensor:
    return spspmm_sum(src, other)


def spspmm(src: SparseTensor, other: SparseTensor,
           reduce: str = "sum") -> SparseTensor:
    if reduce == 'sum' or reduce == 'add':
        return spspmm_sum(src, other)
    elif reduce == 'mean' or reduce == 'min' or reduce == 'max':
        raise NotImplementedError
    else:
        raise ValueError

SparseTensor.spspmm = lambda self, other, reduce="sum": spspmm(
    self, other, reduce)
