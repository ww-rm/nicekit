import os
import string
from hashlib import md5

import cv2
import matplotlib.pyplot as plt
import numpy as np


def getMd5(img):
    return md5(''.join([str(i) for i in img.flat]).encode()).hexdigest()


def makeDir():
    for alpha in string.ascii_lowercase:
        try:
            os.mkdir('./chars/' + alpha)
        except FileExistsError:
            pass
    for num in range(10):
        try:
            os.mkdir('./chars/' + str(num))
        except FileExistsError:
            pass


def cleanNoise(img):
    assert img.ndim == 2  # 单通道

    height = img.shape[0]
    width = img.shape[1]
    imgCopy = img.copy()

    # 四个角
    if img[1][0] == img[0][1] == 0:
        imgCopy[0][0] = 0
    if img[1][width-1] == img[0][width-2] == 0:
        imgCopy[0][width-1] = 0
    if img[height-2][0] == img[height-1][1] == 0:
        imgCopy[height-1][0] = 0
    if img[height-2][width-1] == img[height-1][width-2] == 0:
        imgCopy[height-1][width-1] = 0

    # 四条边
    for col in range(1, width-1):
        upThreePix = [img[0][col-1], img[1][col], img[0][col+1]]
        downThreePix = [img[height-1][col-1],
                        img[height-2][col], img[height-1][col+1]]

        if upThreePix.count(0) >= 2:
            imgCopy[0][col] = 0
        if downThreePix.count(0) >= 2:
            imgCopy[height-1][col] = 0

        if upThreePix.count(255) >= 2:
            imgCopy[0][col] = 255
        if downThreePix.count(255) >= 2:
            imgCopy[height-1][col] = 255

    for row in range(1, height-1):
        leftThreePix = [img[row-1][0], img[row+1][0], img[row][1]]
        rightThreePix = [img[row-1][width-1],
                         img[row+1][width-1], img[row][width-2]]

        if leftThreePix.count(0) >= 2:
            imgCopy[row][0] = 0
        if rightThreePix.count(0) >= 2:
            imgCopy[row][width-1] = 0
        if leftThreePix.count(255) >= 2:
            imgCopy[row][0] = 255
        if rightThreePix.count(255) >= 2:
            imgCopy[row][width-1] = 255

    # 中间的区域
    for row in range(1, height-1):
        for col in range(1, width-1):
            fourPix = [img[row-1][col], img[row+1]
                       [col], img[row][col-1], img[row][col+1]]
            if fourPix.count(0) >= 3:
                imgCopy[row][col] = 0
            if fourPix.count(255) >= 3:
                imgCopy[row][col] = 255

    return imgCopy


def imgProcessor(img, threshold=110, dsize=(15, 30)):
    assert img.ndim == 3 and img.shape[2] == 3  # 三通道

    imgHeight = img.shape[0]
    imgWidth = img.shape[1]

    # grayImg = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    grayImg = cv2.split(img)[0]
    # grayImg = cv2.resize(grayImg, dsize=(
    #     imgWidth*25, imgHeight*25), interpolation=cv2.INTER_AREA)
    # grayImg = cv2.medianBlur(grayImg, 51)
    cv2.threshold(grayImg, threshold, 255, cv2.THRESH_BINARY_INV, grayImg) # 阈值分割
    grayImg = cv2.resize(grayImg, dsize=(
        imgWidth*3, imgHeight*3), interpolation=cv2.INTER_AREA) # 放大
    for i in range(3):
        grayImg = cleanNoise(grayImg)

    grayImg = cv2.resize(grayImg, dsize=(
        imgWidth, imgHeight), interpolation=cv2.INTER_AREA) # 缩小
    for i in range(2):
        grayImg = cleanNoise(grayImg)
    cv2.threshold(grayImg, threshold, 255, cv2.THRESH_BINARY, grayImg)

    cv2.imwrite('grayImg.bmp', grayImg)

    chars = []
    grayImgHeight = grayImg.shape[0]
    grayImgWidth = grayImg.shape[1]

    verticalHist = [0]*grayImgWidth
    for i in range(grayImgWidth):
        for j in grayImg[..., i]:
            if j > 0:
                verticalHist[i] += 1

    begin = 0
    while begin < grayImgWidth:
        if verticalHist[begin] > 1:
            end = begin
            while end < grayImgWidth and verticalHist[end] > 1:
                end += 1
            chars.append(grayImg[..., begin:end].copy())
            begin = end
        begin += 1
    # 垂直分割

    if len(chars) != 4:
        # print(len(chars))
        return []

    for i in range(len(chars)):
        height = chars[i].shape[0]
        width = chars[i].shape[1]

        horizontalHist = [0]*height

        for j in range(height):
            for k in chars[i][j]:
                if k > 0:
                    horizontalHist[j] += 1

        begin = height-1
        while begin >= 0 and horizontalHist[begin] == 0:
            begin -= 1
        # end = begin
        # while end < height and horizontalHist[end] > 0:
        #     end += 1

        chars[i] = chars[i][0:begin+1].copy()
    # 水平去除底边缘

    # for i in range(len(chars)):
    #     chars[i] = cv2.resize(chars[i], dsize=(400, 600),
    #                           interpolation=cv2.INTER_AREA)
    #     cv2.threshold(chars[i], 255-threshold, 255,
    #                   cv2.THRESH_BINARY, chars[i])
    #     cnts = cv2.findContours(chars[i], cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0][0]
    #     rect = cv2.minAreaRect(cnts)
    #     angle = rect[2]
    #     print(rect)
    #     rotateMat = cv2.getRotationMatrix2D((chars[i].shape[0]/2, chars[i].shape[1]/2), -angle, 1)
    #     chars[i] = cv2.warpAffine(chars[i], rotateMat, (400,600))
    #     # exit()

    for i in range(len(chars)):
        chars[i] = cv2.resize(chars[i], dsize=dsize,
                              interpolation=cv2.INTER_AREA)
        cv2.threshold(chars[i], 255-threshold, 255,
                      cv2.THRESH_BINARY, chars[i])
    # 统一尺寸

    return chars

def getImgFeature(img):
    assert img.ndim == 2

    return tuple(img.flat)

if __name__ == '__main__':
    makeDir()

    codePics = os.listdir('./trainData/')
    print('total: ', len(codePics))

    count = 0
    for code in codePics:
        img = cv2.imread('./trainData/{filename}'.format(filename=code))
        chars = imgProcessor(img)

        if chars:
            count += 1
            for i in range(len(chars)):
                print('./chars/{char}/{filename}.png'.format(char=code[i],
                                                            filename=getMd5(chars[i])[0:6]))
                cv2.imwrite('./chars/{char}/{filename}.png'.format(
                    char=code[i],
                    filename=getMd5(chars[i])[0:6]
                ), chars[i])
        else:
            print(code)

    print('success: ', count)
    print('percent: ', count/len(codePics))
    # for i in codePics:
    #     img = cv2.imread('./codes/'+i)
    #     a = imgProcessor(img)
    #     input('press')
    #     # for i in a:
    #     #     print(getMd5(i))
    #     #     cv2.imshow('f', i)
    #     #     cv2.waitKey()
