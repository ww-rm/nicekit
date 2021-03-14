import numpy as np

import nnfunc
import nnlayer
import nnmodel

neg_x = np.asarray(
    [
        [x, y] for x in range(1, 10) for y in range(x+1, 10)
    ]
)

pos_x = np.asarray(
    [
        [y, x] for x in range(1, 10) for y in range(x+1, 10)
    ]
)

train_x = np.concatenate((neg_x, pos_x)).T
train_y = np.asarray([0]*36 + [1]*36).reshape((-1, 1)).T

test_x = np.asarray([
    [10, 1],  # 1
    [20, 2],  # 1
    [3.7, 6.9],  # 0
    [4.6, 9.1]  # 0
]).T

if __name__ == "__main__":
    model = nnmodel.Model(2, 1)
    model.add_layer(nnlayer.LinearLayer(2, 10, 0.1))
    model.add_layer(nnlayer.ActivationLayer(10, nnfunc.Sigmoid()))
    model.add_layer(nnlayer.LinearLayer(10, 1, 0.1))
    model.add_layer(nnlayer.ActivationLayer(1, nnfunc.Sigmoid()))

    model.set_loss_layer(nnlayer.LossLayer(1, nnfunc.SqrtLoss()))

    print(train_x)
    print(train_y)
    for i in range(100000):
        model.forward(train_x)
        loss = model.backward(train_y)
        print(loss)
        
    res = model.forward(test_x)
    print(res)
