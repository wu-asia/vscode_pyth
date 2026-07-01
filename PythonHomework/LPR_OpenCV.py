"""
实验四：基于 OpenCV 的车牌识别系统
Author : wu-asia
"""

import os
import cv2
import numpy as np
import pytesseract

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

from PIL import Image
from PIL import ImageTk

# Windows高DPI兼容设置
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Tesseract D盘路径配置（关键，按你的安装目录修改）
pytesseract.pytesseract.tesseract_cmd = r"D:\Program Files\Tesseract-OCR\tesseract.exe"
# 同时加载中文简体+英文数字，psm8单行文字识别适配车牌
OCR_CONFIG = r"--oem 3 --psm 8 -l chi_sim+eng"

class PlateRecognitionSystem:
    # 车牌识别系统
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("基于OpenCV车牌识别系统")
        # 获取屏幕尺寸并居中显示
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w, win_h = 1000, 600
        self.root.geometry(f"{win_w}x{win_h}+{(screen_w-win_w)//2}+{(screen_h-win_h)//2}")
        self.root.minsize(1000, 600)
        
        self.image = None
        self.gray = None
        self.binary = None
        self.plate = None
        self.characters = []
        self.result = ""
        try:
            self.create_widgets()
        except Exception as e:
            print(e)

    # GUI界面搭建（类内方法，正确缩进）
    def create_widgets(self):
        # 网格布局权重分配，左区域宽、右区域窄，不会互相挤压
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 左侧画布区域，第0列
        self.left_frame = tk.Frame(self.root)
        self.left_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.canvas = tk.Canvas(
            self.left_frame,
            bg="white",
            relief=tk.SUNKEN
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 右侧按钮面板，第1列，垂直填充
        self.right_frame = tk.Frame(self.root)
        self.right_frame.grid(row=0, column=1, padx=20, pady=20, sticky="ns")

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
            text="清空数据",
            width=18,
            command=self.clear
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

    # 打开本地图片（同级类方法，顶格缩进）
    def open_image(self):
        filename = filedialog.askopenfilename(
            filetypes=[
                ("图片文件", "*.jpg *.png *.jpeg"),
                ("全部文件", "*.*")
            ]
        )
        if filename == "":
            return
        self.clear()
        self.image = cv2.imread(filename)

        if self.image is None:
            messagebox.showerror("错误", "图片读取失败！")
            return

        self.show_image(self.image)

    # 在tkinter画布显示图片
    def show_image(self, image):
        if image is None:
            return

        # OpenCV(BGR) -> RGB
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        img = Image.fromarray(rgb)

        # 缩放图片
        img.thumbnail((650, 500))

        photo = ImageTk.PhotoImage(img)

        # 清空Canvas
        self.canvas.delete("all")

        # 更新Canvas尺寸
        self.canvas.update_idletasks()

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        # 图片居中显示
        self.canvas.create_image(
            canvas_w // 2,
            canvas_h // 2,
            image=photo,
            anchor="center"
        )

        # 保存引用，防止图片被垃圾回收
        self.canvas.image = photo
    # 识别主流程入口
    def start_recognition(self):
        try:
            if self.image is None:
                messagebox.showwarning("提示", "请先打开图片！")
                return
            self.gray = self.gray_process(self.image)
            self.binary = self.image_preprocess(self.gray)
            self.plate = self.locate_plate(self.binary)
            if self.plate is None:
                return
            self.characters = self.segment_characters(self.plate)
            self.result = self.recognize_characters(self.characters)
            self.result_var.set(self.result)
        except Exception as e:
            messagebox.showerror("运行异常", f"识别失败：{str(e)}")

    # 图像灰度化
    def gray_process(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return gray

    # 图像预处理：滤波、Sobel、二值化、形态学开闭运算
    def image_preprocess(self, gray):
        # 高斯滤波降噪
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        # Sobel提取垂直边缘（车牌字符纵向特征）
        sobel = cv2.Sobel(blur, cv2.CV_8U, 1, 0, ksize=3)
        # OTSU自适应二值化
        _, binary = cv2.threshold(sobel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # 闭运算，连接字符间隙
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        close = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close)
        # 开运算，去除细小噪点
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        opening = cv2.morphologyEx(close, cv2.MORPH_OPEN, kernel_open)
        return opening

    # 轮廓筛选定位车牌区域
    def locate_plate(self, binary):
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2:]
        plate = None
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            ratio = w / float(h)
            # 面积、长宽比筛选国内蓝牌
            if area < 2000:
                continue
            if ratio < 2.5 or ratio > 5.5:
                continue
            plate = self.image[y:y+h, x:x+w]
            # 原图绘制车牌框
            cv2.rectangle(self.image, (x, y), (x+w, y+h), (0, 255, 0), 2)
            break
        if plate is None:
            messagebox.showwarning("提示", "未检测到车牌！")
            return None
        self.show_image(self.image)
        return plate

    # OpenCV弹窗调试中间图
    def show_cv_image(self, title, image):
        if image is None:
            return
        cv2.imshow(title, image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # 车牌字符分割
    def segment_characters(self, plate):
        if plate is None:
            return []
        gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
        # 反二值化：字符变白，背景变黑
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2:]
        char_regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w < 5 or h < 20:
                continue
            ratio = h / float(w)
            if ratio < 1.0:
                continue
            char_regions.append((x, y, w, h))
        # 按横向坐标从左到右排序字符
        char_regions = sorted(char_regions, key=lambda item: item[0])
        chars = []
        for region in char_regions:
            x, y, w, h = region
            char_img = binary[y:y+h, x:x+w]
            char_img = cv2.resize(char_img, (20, 40))
            chars.append(char_img)
        return chars

    # 字符识别（Tesseract OCR实现，补齐原空函数）
    def recognize_characters(self, chars):
        if not chars:
            return "无识别字符"
        # 拼接全部字符图像为一整张
        total_h = max(img.shape[0] for img in chars)
        total_w = sum(img.shape[1] for img in chars)
        concat_img = np.zeros((total_h, total_w), dtype=np.uint8)
        offset = 0
        for c_img in chars:
            h, w = c_img.shape
            concat_img[0:h, offset:offset+w] = c_img
            offset += w
        # OCR识别
        text = pytesseract.image_to_string(concat_img, config=OCR_CONFIG)
        # 清洗换行、空格
        clean_text = text.strip().replace("\n", "").replace(" ", "")
        return clean_text if clean_text else "识别失败"

    # 保存处理后图片
    def save_image(self, image, filename):
        if image is None:
            return
        cv2.imwrite(filename, image)

    # 重置所有缓存数据
    def clear(self):
        self.image = None
        self.gray = None
        self.binary = None
        self.plate = None
        self.characters = []
        self.result = ""
        self.result_var.set("")

        self.canvas.delete("all")
        self.canvas.image = None

    # GUI主循环
    def run(self):
        self.root.mainloop()

# 程序入口
def main():
    print("正在启动车牌识别系统...")
    app = PlateRecognitionSystem()
    print("GUI创建完成，进入主循环...")
    app.run()

if __name__ == "__main__":
    main()