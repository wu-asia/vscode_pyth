"""
实验四：基于 OpenCV 的车牌识别系统
Author : wu-asia
"""

import os
import cv2
import numpy as np

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

from PIL import Image
from PIL import ImageTk


class PlateRecognitionSystem:
    
    #车牌识别系统
    def __init__(self):

        self.root = tk.Tk()
        self.root.title("基于OpenCV车牌识别系统")
        self.root.geometry("1200x700")

        self.image = None
        self.gray = None
        self.binary = None
        self.plate = None
        self.characters = []
        self.result = ""

        self.create_widgets()

    # GUI
    def create_widgets(self):

        self.left_frame = tk.Frame(self.root)
        self.left_frame.pack(side=tk.LEFT, padx=20, pady=20)

        self.right_frame = tk.Frame(self.root)
        self.right_frame.pack(side=tk.RIGHT, padx=20)

        self.canvas = tk.Label(
            self.left_frame,
            width=700,
            height=500,
            relief=tk.SUNKEN,
            bg="white"
        )

        self.canvas.pack()

        tk.Button(
            self.right_frame,
            text="打开图片",
            width=18,
            command=self.open_image
        ).pack(pady=8)

        tk.Button(
            self.right_frame,
            text="开始识别",
            width=18,
            command=self.start_recognition
        ).pack(pady=8)

        tk.Button(
            self.right_frame,
            text="退出系统",
            width=18,
            command=self.root.destroy
        ).pack(pady=8)

        tk.Label(
            self.right_frame,
            text="识别结果："
        ).pack(pady=15)

        self.result_var = tk.StringVar()

        tk.Entry(
            self.right_frame,
            width=28,
            textvariable=self.result_var,
            state="readonly"
        ).pack()


    # 图片读取
    def open_image(self):
        """
        打开图片
        """

        filename = filedialog.askopenfilename(
            filetypes=[
                ("Image", "*.jpg"),
                ("Image", "*.png"),
                ("Image", "*.jpeg")
            ]
        )

        if filename == "":
            return

        self.image = cv2.imread(filename)

        self.show_image(self.image)

    # 图片显示
    def show_image(self, image):
        """
        在GUI中显示图片
        """

        if image is None:
            return

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        img = Image.fromarray(rgb)

        img.thumbnail((650, 500))

        photo = ImageTk.PhotoImage(img)

        self.canvas.configure(image=photo)
        self.canvas.image = photo

    # 主流程
    def start_recognition(self):
        """
        开始识别
        """

        if self.image is None:

            messagebox.showwarning(
                "提示",
                "请先打开图片！"
            )

            return

        self.gray = self.gray_process(self.image)

        self.binary = self.image_preprocess(self.gray)

        self.plate = self.locate_plate(self.binary)

        self.characters = self.segment_characters(self.plate)

        self.result = self.recognize_characters(
            self.characters
        )

        self.result_var.set(self.result)

    # 图像灰度化
    def gray_process(self, image):
        #图像灰度化
        

        pass

    # 图像预处理
    def image_preprocess(self, gray):
        """
        图像预处理 包括：
        1.高斯滤波 2. 中值滤波
        3.Sobel   4. Canny
        5.二值化   6. 开闭运算
        """
        # 高斯滤波
        blur = cv2.GaussianBlur(
            gray,
            (5, 5),
            0
        )

        # Sobel算子
        # 提取水平边缘
        sobel = cv2.Sobel(
            blur,
            cv2.CV_8U,
            1,
            0,
            ksize=3
        )

        # 二值化
        _, binary = cv2.threshold(

            sobel,

            0,

            255,

            cv2.THRESH_BINARY +
            cv2.THRESH_OTSU

        )

        # 定义矩形结构元素
        kernel = cv2.getStructuringElement(

            cv2.MORPH_RECT,

            (17, 5)

        )

        # 闭运算
        # 填补车牌字符之间空隙
        close = cv2.morphologyEx(

            binary,

            cv2.MORPH_CLOSE,

            kernel

        )

        # 开运算
        # 去除小噪点
        kernel2 = cv2.getStructuringElement(

            cv2.MORPH_RECT,

            (3, 3)

        )

        opening = cv2.morphologyEx(

            close,

            cv2.MORPH_OPEN,

            kernel2

        )

        return opening

    # 车牌定位
    def locate_plate(self, binary):
        """
        定位车牌区域可采用：轮廓检测、长宽比筛选、面积筛选
        """

        pass

    # 字符分割
    def segment_characters(self, plate):
        """
        字符切割 返回：list
        """

        pass

    # 字符识别
    def recognize_characters(self, chars):
        """
        字符识别 可采用：模板匹配或KNN或SVM
        """

        pass

    # 保存中间结果
    def save_image(self, image, filename):
        """
        保存图片
        """

        pass

    # 清空数据

    def clear(self):
        """
        清空数据
        """

        self.image = None
        self.gray = None
        self.binary = None
        self.plate = None
        self.characters = []
        self.result = ""

        self.result_var.set("")

    # 主循环

    def run(self):
        self.root.mainloop()

# 主函数

def main():
    app = PlateRecognitionSystem()
    app.run()


if __name__ == "__main__":
    main()