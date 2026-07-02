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
# 对于中文的部分的识别的代码测试用例较少，识别的误差较大，对于
OCR_CONFIG = (
    r'--oem 3 '
    r'--psm 7 '
    r'-l chi_sim+eng '
    r'-c tessedit_char_whitelist='
    r'京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼'
    r'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
)


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

            self.plate = self.color_locate_plate(self.image)
            if self.plate is None:
                self.plate = self.locate_plate(self.binary)
            
            if self.plate is None:
                return
            # 不再分割字符，直接传入整张车牌识别
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

    def color_locate_plate(self, image):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 蓝牌
        lower_blue = np.array([100, 80, 80])
        upper_blue = np.array([140, 255, 255])

        # 黄牌
        lower_yellow = np.array([10, 40, 60])
        upper_yellow = np.array([45, 255, 255])

        # 绿牌【拓宽区间适配新能源浅绿车牌】
        lower_green = np.array([35, 30, 30])
        upper_green = np.array([95, 255, 255])

        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        mask_green = cv2.inRange(hsv, lower_green, upper_green)

        mask = cv2.bitwise_or(mask_blue, mask_yellow)
        mask = cv2.bitwise_or(mask, mask_green)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9,9))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours,_ = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x,y,w,h = cv2.boundingRect(cnt)
            area = w*h
            ratio = w/float(h)
            # 放宽阈值，兼容小尺寸、外籍车牌
            if area < 1000:
                continue
            if ratio < 1.7 or ratio > 7.0:
                continue
            plate = image[y:y+h,x:x+w]
            cv2.rectangle(image,(x,y),(x+w,y+h),(0,255,0),2)
            self.show_image(self.image)
            return plate
        return None

    # 轮廓筛选定位车牌区域
    def locate_plate(self, binary):
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2:]
        plate = None
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            ratio = w / float(h)
            # 统一放宽阈值
            if area < 1000:
                continue
            if ratio < 1.7 or ratio > 7.0:
                continue
            plate = self.image[y:y+h, x:x+w]
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
        """
        字符分割（升级版）

        功能：
            1. 放大车牌
            2. CLAHE增强
            3. OTSU二值化
            4. 开运算去噪
            5. 轮廓筛选
            6. 字符排序
            7. 输出字符图片列表
        """

        if plate is None:
            return []

        # 1. 放大车牌，提高OCR识别率
        plate = cv2.resize(
            plate,
            None,
            fx=3,
            fy=3,
            interpolation=cv2.INTER_CUBIC
        )

        # 2. 转灰度
        gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)

        # 3. CLAHE增强
        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        gray = clahe.apply(gray)

        # 4. OTSU自动二值化
        _, binary = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        # 5. 开运算去除噪点
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (2, 2)
        )

        binary = cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            kernel
        )

        # 6. 查找轮廓
        contours, _ = cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        char_regions = []

        h_img, w_img = binary.shape

        for contour in contours:

            x, y, w, h = cv2.boundingRect(contour)

            area = w * h

            #面积过滤
            if area < 150:
                continue

            #宽高过滤
            if h < h_img * 0.35:
                continue

            if h > h_img * 0.95:
                continue

            if w < 8:
                continue

            ratio = h / float(w)

            if ratio < 1.2:
                continue

            if ratio > 6:
                continue

            char_regions.append((x, y, w, h))

        # 7. 左→右排序
        char_regions.sort(key=lambda item: item[0])

        chars = []

        # 8. 提取字符
        for x, y, w, h in char_regions:

            pad = 2

            x1 = max(0, x - pad)
            y1 = max(0, y - pad)

            x2 = min(binary.shape[1], x + w + pad)
            y2 = min(binary.shape[0], y + h + pad)

            char_img = binary[y1:y2, x1:x2]

            # 统一字符尺寸
            char_img = cv2.resize(
                char_img,
                (30, 60),
                interpolation=cv2.INTER_AREA
            )

            chars.append(char_img)

        # 字符数量检测
        if len(chars) < 7:
            print("字符分割失败，字符数量不足：", len(chars))

        elif len(chars) > 8:
            print("字符数量过多：", len(chars))

        else:
            print("字符数量：", len(chars))

        return chars

    #识别字符
    def recognize_characters(self, chars):
        """
        字符识别（逐字符OCR）

        参数：
            chars：segment_characters返回的字符图片列表

        返回：
            完整车牌字符串
        """

        if len(chars) == 0:
            return "未识别"

        result = ""

        for index, img in enumerate(chars):

            # 放大字符
            img = cv2.resize(
                img,
                None,
                fx=2,
                fy=2,
                interpolation=cv2.INTER_CUBIC
            )

            # OCR识别单个字符
            text = pytesseract.image_to_string(
                img,
                config="--psm 10"
            )

            # 去除空格和换行
            text = text.strip()

            text = text.replace("\n", "")

            text = text.replace(" ", "")

            # 如果为空
            if text == "":
                text = "?"

            result += text

        return result

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