import numpy as np

import nnfunc


class BaseLayer:
    """网络层基类

    Attributes:
        input_size: 输入维度大小
        output_size: 输出维度大小
        input_fw: 前向传播中传入的矩阵
        output_fw: 前向传播中传出的矩阵
        input_bw: 后向传播中传入的矩阵
        output_bw: 后向传播中传出的矩阵

    Methods:
        forward: 进行前向传播, 会更新input_fw, output_fw的值
        backward: 进行后向传播, 会更新input_bw, output_bw的值, 同时会梯度下降更新本层的训练参数
    """

    def __init__(self, input_size: int, output_size: int):
        self.input_size = input_size
        self.output_size = output_size
        self.input_fw = None
        self.output_fw = None
        self.input_bw = None
        self.output_bw = None

    def forward(self, input_):
        raise NotImplementedError

    def backward(self, input_):
        raise NotImplementedError


class LossLayer(BaseLayer):
    """损失层

    Args:
        input_size: 输入维度
        loss_func: 要使用的损失函数

    Methods:
        forward: 计算损失值
        backward: 损失反向传播
    """

    def __init__(self, input_size, loss_func: nnfunc.BaseLoss):
        if not isinstance(loss_func, nnfunc.BaseLoss):
            raise TypeError("loss_func must be an instance of nnfunc.BaseLoss")

        super().__init__(input_size, 1)
        self.func = loss_func

    def forward(self, y_true, y_pred):
        """前向传播计算损失值

        Args:
            y_true: 真实值
            y_pred: 预测值
            形状为(input_size, N)

        Returns:
            损失值
        """

        self.loss_value = self.func(y_true, y_pred)
        return self.loss_value

    def backward(self, y_true, y_pred):
        """反向传播损失函数的梯度

        Args:
            y_true: 真实值
            y_pred: 预测值

        Returns:
            损失函数对y_pred的导数
            形状为(input_size, N)
        """

        self.output_bw = self.func.de(y_true, y_pred)
        return self.output_bw


class ActivationLayer(BaseLayer):
    """激活层

    Args:
        input_size: 输入维度
        activation_func: 要使用的激活函数

    Methods:
        forward: 前向计算
        backward: 反向计算
    """

    def __init__(self, input_size, activation_func):
        if not isinstance(activation_func, nnfunc.BaseActivation):
            raise TypeError("activation_func must be an instance of nnfunc.BaseActivation")

        super().__init__(input_size, input_size)
        self.func = activation_func

    def forward(self, input_):
        """前向计算

        Args:
            input_: 形状为(input_size, N)

        Returns:
            形状(output_size, N)
        """

        self.input_fw = np.asarray(input_)

        # 前向传播
        self.output_fw = self.func(self.input_fw)
        return self.output_fw

    def backward(self, input_):
        """反向传播累计梯度

        Args:
            input_: 形状为(output_size, N)

        Returns:
            形状(input_size, N)
        """
        self.input_bw = np.asarray(input_)

        # 反向传播
        # 累计梯度等于本层求导乘上传入的梯度
        self.output_bw = self.func.de(self.input_fw)*self.input_bw
        return self.output_bw


class LinearLayer(BaseLayer):
    """线性层

    是一个Wx+b的矩阵变换

    Args:
        input_size: 输入维度
        output_size: 输出维度
        learning_rate: 参数的学习率

    Methods:
        forward
        backward
    """

    def __init__(self, input_size, output_size, learning_rate=0.01):
        super().__init__(input_size, output_size)

        # 随机初始化weight和bias
        self.weight = np.random.random_sample((output_size, input_size))
        self.bias = np.random.random_sample((output_size, 1))
        self.learning_rate = learning_rate

    def forward(self, input_):
        """前向传播

        Args:
            input_: 形状为(input_size, N)

        Returns:
            形状(output_size, N)
        """

        self.input_fw = np.asarray(input_)

        # 前向传播
        self.output_fw = self.weight @ self.input_fw + self.bias

        return self.output_fw

    def backward(self, input_):
        """反向传播

        Args:
            input_: 从后一层回传的累计梯度, 形状为(output_size, N)

        Returns:
            矩阵, 形状为(input_size, N)
        """

        self.input_bw = np.asarray(input_)

        # 反向传播累计梯度
        self.output_bw = self.weight.T @ self.input_bw

        # 梯度下降
        # 此处取了总样本数的平均梯度
        gred_weight = (self.input_bw @ self.input_fw.T) / self.input_fw.shape[1]
        gred_bias = (self.input_bw @ np.ones((self.input_bw.shape[1], 1))) / self.input_fw.shape[1]

        # 梯度下降
        self.weight += (-gred_weight*self.learning_rate)
        self.bias += (-gred_bias*self.learning_rate)

        return self.output_bw
