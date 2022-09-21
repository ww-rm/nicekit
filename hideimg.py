import argparse
from os import PathLike
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np


class MirageTank:
    @staticmethod
    def _mergeimg(cover: np.ndarray, secret: np.ndarray) -> np.ndarray:
        """合并 cover 到 secret 上, 底层方法.

        Args:
            cover: 白底显示图
            secret: 黑底显示图
        """
        # 需要是灰度图
        # 转换图片数据类型为浮点数
        cover = cover.astype("float64")
        secret = secret.astype("float64")

        # 检查像素点 min(delta) >= 0, 调整图像
        c_min = np.min(cover)
        s_max = np.max(secret)

        # 二次函数调整, cover: [128, 255], secret: [0, 128]
        cover = cover + ((128 - c_min) / (256 - c_min)**2) * (256 - cover)**2
        secret = secret - ((s_max - 128) / s_max**2) * (secret**2)

        # 计算新图, 要求 min(delta) >= 0
        delta = cover - secret
        mirage_a = 255 - delta
        mirage_grey = 255 * secret / mirage_a

        mirage = np.stack([mirage_grey, mirage_grey, mirage_grey, mirage_a], axis=2).astype("uint8")
        return mirage

    @staticmethod
    def _adjustimg(cover: np.ndarray, secret: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """调整两张图到同样大小, cover 能够完全覆盖 secret, 需要时灰度图."""

        c_height, c_width = cover.shape
        s_height, s_width = secret.shape

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
            delta_height // 2, (delta_height + 1) // 2,
            delta_width // 2, (delta_width + 1) // 2,
            cv2.BORDER_CONSTANT, value=0
        )

        return (cover, secret)

    @staticmethod
    def makeimg(cover: np.ndarray, secret: np.ndarray) -> np.ndarray:
        """制作幻影图, 需要两张灰度图."""
        cover, secret = MirageTank._adjustimg(cover, secret)
        return MirageTank._mergeimg(cover, secret)

    @staticmethod
    def load_cover_and_secret(cover_path: PathLike, secret_path: PathLike) -> Tuple[np.ndarray, np.ndarray]:
        """load cover and secret in correct format"""
        return (
            cv2.imread(Path(cover_path).as_posix(), cv2.IMREAD_GRAYSCALE),
            cv2.imread(Path(secret_path).as_posix(), cv2.IMREAD_GRAYSCALE)
        )

    @staticmethod
    def save_mirage(mirage: PathLike, save_path: PathLike) -> bool:
        """save mirage in correct format"""
        return cv2.imwrite(Path(save_path).with_suffix(".png").as_posix(), mirage)

    @staticmethod
    def create_mirage(cover_path: PathLike, secret_path: PathLike, save_path: PathLike):
        """make a mirage image with three paths"""
        cover, secret = MirageTank.load_cover_and_secret(cover_path, secret_path)
        if isinstance(cover, np.ndarray) and isinstance(secret, np.ndarray):
            mirage = MirageTank.makeimg(cover, secret)
            MirageTank.save_mirage(mirage, save_path)
        else:
            print("Image loading failed!")


def create_blacktank(img_path: PathLike, save_path: PathLike) -> Path:
    """Hide image info into alpha channel. Return save_path if success, else None."""
    img = cv2.imread(Path(img_path).as_posix(), cv2.IMREAD_GRAYSCALE)
    if isinstance(img, np.ndarray):
        img_black = np.zeros(img.shape, dtype=np.uint8)
        img_alpha = 255 - img
        img_out = np.stack([img_black, img_black, img_black, img_alpha], axis=2)

        save_path = Path(save_path).with_suffix(".png")
        cv2.imwrite(save_path.as_posix(), img_out)
        return save_path
    else:
        print("Image loading failed!")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--mirage", nargs=3, type=Path, help="cover secret dest")
    parser.add_argument("--black", nargs=2, type=Path, help="secret dest")

    args = parser.parse_args()

    if args.mirage:
        MirageTank.create_mirage(args.mirage[0], args.mirage[1], args.mirage[2])
    if args.black:
        create_blacktank(args.black[0], args.black[1])
