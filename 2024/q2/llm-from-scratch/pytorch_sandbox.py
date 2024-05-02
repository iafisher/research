import torch
import torch.nn.functional as F


def tensor_examples():
    tensor0d = torch.tensor(1)
    print(tensor0d)

    tensor1d = torch.tensor([1, 2, 3])
    print(tensor1d)

    tensor2d = torch.tensor([[1, 2], [3, 4]])
    print(tensor2d)

    tensor3d = torch.tensor([[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
    print(tensor3d)

    floatvec = torch.tensor([1.0, 2.0, 3.0])
    print(floatvec.dtype)

    print(floatvec.to(torch.float64))

    print(tensor1d.view(3, 1))
    # 1 2  ==>  1 3
    # 3 4  ==>  2 4
    print(tensor2d.T)

    m1 = torch.rand([2, 2])
    m2 = torch.rand([2, 2])
    print(m1)
    print(m2)
    print(m1 @ m2)  # equivalent: m1.matmul(m2)


def autograd_examples():
    # logistic regression forward pass:

    # target label
    y = torch.tensor([1.0])

    # input data
    x1 = torch.tensor([1.1])

    # model weight
    w1 = torch.tensor([2.2])

    # model bias
    b = torch.tensor([0.0])

    # computation
    z = x1 * w1 + b
    a = torch.sigmoid(z)

    loss = F.binary_cross_entropy(a, y)
