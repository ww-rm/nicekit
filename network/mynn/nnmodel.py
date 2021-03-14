import numpy as np

import nnlayer


class BaseModel:
    def __init__(self, input_size, output_size):
        self.input_size = input_size
        self.output_size = output_size


class Model(BaseModel):
    """自定义网络

    Attributes:
        layers: 一个列表, 保存了所有的网络层对象
        loss_layer: 损失层

    Methods:
        add_layer: 添加一个层
        set_loss_layer: 设置损失层
        forward: 前向传播
        backward: 反向传播
    """

    def __init__(self, input_size, output_size):
        super().__init__(input_size, output_size)
        self.layers = []
        self.loss_layer = None

    def add_layer(self, layer: nnlayer.BaseLayer):
        """添加一个层

        Args:
            layer: 要添加的层
        """

        if not isinstance(layer, nnlayer.BaseLayer):
            raise TypeError("layer must be an instance of nnlayer.BaseLayer")
        self.layers.append(layer)

    def set_loss_layer(self, loss_layer: nnlayer.LossLayer):
        """设置损失层

        Args:
            loss_layer: 要设置的损失层
        """

        if not isinstance(loss_layer, nnlayer.LossLayer):
            raise TypeError("loss_layer must be an instance of nnlayer.LossLayer")
        self.loss_layer = loss_layer

    def forward(self, input_):
        """前向传播

        Args:
            input_: 形状为(input_size, N)

        Returns:
            整个网络最后一层的output_fw, 同时layers中所有的input_fw和output_fw会更新
        """

        for layer in self.layers:
            input_ = layer.forward(input_)
        return self.layers[-1].output_fw

    def backward(self, y_true):
        """反向传播

        反向传播损失梯度, 同时更新所有参数

        Args:
            y_true: 真实值, 形状(output_size, N)

        Returns:
            本轮传播之前的损失值
        """

        # 计算损失和梯度
        loss_value = self.loss_layer.forward(y_true, self.layers[-1].output_fw)
        input_ = self.loss_layer.backward(y_true, self.layers[-1].output_fw)

        # 反向传播
        for layer in self.layers[::-1]:
            input_ = layer.backward(input_)

        return loss_value
