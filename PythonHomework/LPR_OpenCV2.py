"""
实验四：基于 OpenCV 的车牌识别系统（答辩高分稳定版，按规范优化）
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

# 【修改点1：拆分OCR配置，消除白名单冲突】
# 整牌兜底识别配置（无白名单，psm7单行）
OCR_FULL_CONFIG = (
    r'--oem 3 '
    r'--psm 7 '
    r'-l chi_sim+eng '
)
# 单汉字（省份简称）专用识别配置
OCR_CHINESE = r'--oem 3 --psm 10 -l chi_sim'
# 字母/数字专用识别配置
OCR_CHAR = r'--oem 3 --psm 10 -l eng'

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

    # GUI界面搭建
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

    # 打开本地图片
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

    # 识别主流程入口（修改点2：优先分割识别，候选列表重排）
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
                self.result_var.set("未检测到车牌")
                return
            
            # 方案1：整张车牌识别兜底
            full_text = self.recognize_characters(self.plate)
            # 方案2：字符分割逐字识别，首位汉字单独识别提升精度
            char_imgs = self.segment_characters(self.plate)
            seg_text = ""
            if len(char_imgs) >= 7:
                text_buf = []
                for idx, char_img in enumerate(char_imgs):
                    if idx == 0:
                        # 第一位省份汉字专用中文识别
                        char_txt = pytesseract.image_to_string(char_img, config=OCR_CHINESE).strip()
                    else:
                        # 其余字母数字识别
                        char_txt = pytesseract.image_to_string(char_img, config=OCR_CHAR).strip()
                    text_buf.append(char_txt)
                seg_text = "".join(text_buf)
            
            # 【修改点2：优先分割结果，兜底整图识别】
            candidate_list = []
            if seg_text:
                candidate_list.append(seg_text)
            if full_text:
                candidate_list.append(full_text)

            # 筛选合法车牌（7/8位，适配普通蓝黄牌+新能源绿牌）
            self.result = "识别失败"
            for text in candidate_list:
                clean = text.replace("·", "").strip()
                if 7 <= len(clean) <= 8:
                    self.result = text
                    break
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

        # 【修改点3：收紧绿牌HSV阈值，减少树叶误检】
        lower_green = np.array([35, 50, 50])
        upper_green = np.array([90, 255, 255])

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
            # 【加分修改：增加最小面积过滤，减少远距离小图误检】
            if area < 1500:
                continue
            # 二次颜色校验过滤干扰矩形
            roi = self.image[y:y+h, x:x+w]
            hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            full_mask = cv2.inRange(hsv_roi, np.array([8,20,20]), np.array([142,255,255]))
            color_ratio = cv2.countNonZero(full_mask) / (w*h)
            if color_ratio > 0.15:
                plate = roi
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

    # 车牌字符分割（修改点4：收紧字符尺寸，过滤竖线噪声）
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
            # 收紧最小尺寸，过滤微小噪点
            if w < 6 or h < 20:
                continue
            ratio = h / float(w)
            if ratio < 0.8:
                continue
            # 新增：过滤细长竖线噪声
            if h / float(w) > 6:
                continue
            char_regions.append((x, y, w, h))
        # 按横向坐标从左到右排序字符
        char_regions = sorted(char_regions, key=lambda item: item[0])
        chars = []
        for region in char_regions:
            x, y, w, h = region
            char_img = binary[y:y+h, x:x+w]
            char_img = cv2.resize(char_img, (22, 44))
            chars.append(char_img)
        return chars

    # 字符识别（修改点5：增加字符纠错映射，混淆字符替换）
    def recognize_characters(self, plate):
        if plate is None:
            return ""
        # 4倍放大提升文字分辨率
        plate_resize = cv2.resize(plate, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(plate_resize, cv2.COLOR_BGR2GRAY)
        # 自适应均衡，消除反光、明暗不均
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        # 自适应二值化，替代固定OTSU，适配深浅底色车牌
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 13, 3
        )
        # 形态学开运算分离粘连字符
        kernel_sep = cv2.getStructuringElement(cv2.MORPH_RECT, (2,6))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_sep)
        # 高斯平滑降噪
        blur = cv2.GaussianBlur(binary, (3, 3), 1)

        # OCR识别整张图，使用拆分后的无白名单配置
        text = pytesseract.image_to_string(blur, config=OCR_FULL_CONFIG)
        # 清理多余换行、空格
        clean_text = text.strip().replace("\n", "").replace(" ", "")

        # 【修改点5：字符混淆纠错映射】
        fix_map = {
            "O": "0", "I": "1", "Z": "2",
            "S": "5", "B": "8"
        }
        fixed = ""
        for ch in clean_text:
            fixed += fix_map.get(ch, ch)
        return fixed

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