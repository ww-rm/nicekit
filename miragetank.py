import argparse
from pathlib import PurePath

import cv2
import numpy as np


def adjustimg(cover, secret):
    """
    adjust img to fit mergimg function
    """
    # 图像需要是灰度图

    s_height, s_width = secret.shape

    c_height, c_width = cover.shape

    if c_height < s_height:
        cover = cv2.resize(cover, (int(c_width*s_height/c_height + 0.5), s_height), interpolation=cv2.INTER_CUBIC)
        c_height, c_width = cover.shape

    if c_width < s_width:
        cover = cv2.resize(cover, (s_width, int(c_height*s_width/c_width + 0.5)), interpolation=cv2.INTER_CUBIC)
        c_height, c_width = cover.shape

    delta_height = c_height - s_height
    delta_width = c_width - s_width
    secret = cv2.copyMakeBorder(
        secret,
        delta_height//2, (delta_height+1)//2,
        delta_width//2, (delta_width+1)//2,
        cv2.BORDER_CONSTANT, value=0
    )

    return (cover, secret)


def mergeimg(cover, secret):
    """
    merge cover over secret
    """
    # 需要是灰度图
    # 转换图片数据类型为浮点数
    cover = cover.astype("float64")
    secret = secret.astype("float64")

    # 检查像素点 min(delta) >= 0, 调整图像
    c_min = np.min(cover)
    s_max = np.max(secret)

    # 二次函数调整, cover: [128, 255], secret: [0, 128]
    cover = cover + ((128-c_min)/(256-c_min)**2) * (256-cover)**2
    secret = secret - ((s_max-128) / s_max**2) * (secret**2)

    # 计算新图, 要求 min(delta) >= 0
    delta = cover - secret
    output_a = 255 - delta
    output_grey = 255 * secret / output_a

    output = np.stack([output_grey, output_grey, output_grey, output_a], axis=2).astype("uint8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cover", type=str, help="cover(white) image")
    parser.add_argument("secret", type=str, help="secret(black) image")
    parser.add_argument("dest", type=str, help="dest path, if not \".png\" suffix, will replace to \".png\"")

    args = parser.parse_args()

    # 读取灰度图
    cover = cv2.imread(args.cover, cv2.IMREAD_GRAYSCALE)
    secret = cv2.imread(args.secret, cv2.IMREAD_GRAYSCALE)

    # 调整大小
    cover, secret = adjustimg(cover, secret)

    # 生成
    output = mergeimg(cover, secret)

    # 保存
    cv2.imwrite(
        PurePath(args.dest).with_suffix(".png").as_posix(),
        output
    )
