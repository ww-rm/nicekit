import numpy as np


class BaseActivation:
    """激活函数以及自身的导函数

    Methods:
        __call__:
            函数本身
        de:
            导函数

    Examples:
        func = Class()
        res = func(x)
        res_de = func.de(x)
    """


class BaseLoss:
    """损失函数以及自身的导函数

    Methods:
        __call__:
            函数本身
        de:
            导函数

    Examples:
        func = Class()
        res = func(x)
        res_de = func.de(x)
    """


class Sigmoid(BaseActivation):
    """sigmoid函数"""

    def __call__(self, input_):
        tmp = np.exp(np.negative(input_))
        return 1.0 / (1.0 + tmp)

    @property
    def de(self):
        def sigmoid_de(input_):
            """sigmoid导函数"""
            tmp = self(input_)
            return tmp * (1.0-tmp)
        return sigmoid_de


class SqrtLoss(BaseLoss):
    """平方损失函数
    
    Args:
        y_true: 真实值
        y_pred: 计算值
    """

    def __call__(self, y_true, y_pred):
        return np.sum(np.power(y_true-y_pred, 2)) / 2

    @property
    def de(self):
        def sqrtloss_de(y_true, y_pred):
            """平方损失导函数"""
            return -np.subtract(y_true, y_pred)
        return sqrtloss_de


sigmoid = Sigmoid()
sqrtloss = SqrtLoss()
