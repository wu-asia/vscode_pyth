"""
实验四：基于 OpenCV 的车牌识别系统（绿牌/中文识别修复版）
Author : wu-asia
"""

import os
import cv2
import numpy as np
import pytesseract
# 放在pytesseract导入后
TESS_PATH = r"D:\Program Files\Tesseract-OCR\tesseract.exe"
if not os.path.exists(TESS_PATH):
    messagebox.showerror("环境错误", f"Tesseract不存在：{TESS_PATH}")
pytesseract.pytesseract.tesseract_cmd = TESS_PATH
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

# Tesseract 路径，按你本地安装目录修改
pytesseract.pytesseract.tesseract_cmd = r"D:\Program Files\Tesseract-OCR\tesseract.exe"

# 优化OCR配置：车牌专用白名单、单行模式、中英文混合
OCR_CONFIG = (
    r'--oem 3 '
    r'--psm 8 '
    r'-l chi_sim+eng '
    r'-c tessedit_char_whitelist=京沪津渝冀晋蒙辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川贵云藏陕甘青宁0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ·'
)
# 单汉字识别配置（省份简称专用）
OCR_CHINESE = r'--oem 3 --psm 10 -l chi_sim'
# 字母数字识别配置
OCR_CHAR = r'--oem 3 --psm 10 -l eng'

class PlateRecognitionSystem:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("基于OpenCV车牌识别系统")
        # 窗口居中
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
            print("界面初始化异常：", e)

    def create_widgets(self):
        # 布局权重
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 左侧图片画布
        self.left_frame = tk.Frame(self.root)
        self.left_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.canvas = tk.Canvas(self.left_frame, bg="white", relief=tk.SUNKEN)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 右侧控制面板
        self.right_frame = tk.Frame(self.root)
        self.right_frame.grid(row=0, column=1, padx=20, pady=20, sticky="ns")

        tk.Button(self.right_frame, text="打开图片", width=18, command=self.open_image).pack(pady=8)
        tk.Button(self.right_frame, text="开始识别", width=18, command=self.start_recognition).pack(pady=8)
        tk.Button(self.right_frame, text="清空数据", width=18, command=self.clear).pack(pady=8)
        tk.Button(self.right_frame, text="退出系统", width=18, command=self.root.destroy).pack(pady=8)

        tk.Label(self.right_frame, text="识别结果：").pack(pady=15)
        self.result_var = tk.StringVar()
        tk.Entry(self.right_frame, width=28, textvariable=self.result_var, state="readonly").pack()

    def open_image(self):
        filename = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.jpg *.png *.jpeg"), ("全部文件", "*.*")]
        )
        if not filename:
            return
        self.clear()
        self.image = cv2.imread(filename)
        if self.image is None:
            messagebox.showerror("错误", "图片读取失败！")
            return
        self.show_image(self.image)

    def show_image(self, image):
        if image is None:
            return
        rgb = cv2.cvtColor(image, cv2.BGR2RGB)
        img = Image.fromarray(rgb)
        img.thumbnail((650, 500))
        photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.update_idletasks()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.create_image(cw//2, ch//2, image=photo, anchor="center")
        self.canvas.image = photo

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
            
            # 优先整张识别兜底（绿牌兼容性更强）
            full_text = self.recognize_characters(self.plate)
            char_imgs = self.segment_characters(self.plate)
            seg_text = ""
            if len(char_imgs) >= 7:
                text_buf = []
                for idx, char_img in enumerate(char_imgs):
                    if idx == 0:
                        char_txt = pytesseract.image_to_string(char_img, config=OCR_CHINESE).strip()
                    else:
                        char_txt = pytesseract.image_to_string(char_img, config=OCR_CHAR).strip()
                    text_buf.append(char_txt)
                seg_text = "".join(text_buf)
            
            # 双结果择优，优先长度符合的
            candidate_list = [full_text, seg_text]
            valid_result = "识别失败"
            for text in candidate_list:
                clean = text.replace("·", "").strip()
                if 7 <= len(clean) <= 8:
                    valid_result = text
                    break
            self.result = valid_result
            self.result_var.set(self.result)
        except Exception as e:
            messagebox.showerror("运行异常", f"识别失败：{str(e)}")

    def gray_process(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def image_preprocess(self, gray):
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        sobel = cv2.Sobel(blur, cv2.CV_8U, 1, 0, ksize=3)
        _, binary = cv2.threshold(sobel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        close = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        opening = cv2.morphologyEx(close, cv2.MORPH_OPEN, kernel_open)
        return opening

    def color_locate_plate(self, image):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # 拓宽HSV阈值适配褪色/浅色车牌
        lower_blue = np.array([98, 60, 60])
        upper_blue = np.array([142, 255, 255])
        lower_yellow = np.array([8, 30, 50])
        upper_yellow = np.array([48, 255, 255])
        lower_green = np.array([32, 20, 20])
        upper_green = np.array([98, 255, 255])

        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        mask_green = cv2.inRange(hsv, lower_green, upper_green)

        mask = cv2.bitwise_or(mask_blue, mask_yellow)
        mask = cv2.bitwise_or(mask, mask_green)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9,9))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            x,y,w,h = cv2.boundingRect(cnt)
            area = w*h
            ratio = w/float(h)
            if area < 1000 or ratio < 1.7 or ratio > 7.0:
                continue
            plate = image[y:y+h, x:x+w]
            cv2.rectangle(image,(x,y),(x+w,y+h),(0,255,0),2)
            self.show_image(self.image)
            return plate
        return None

    def locate_plate(self, binary):
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2:]
        plate = None
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            ratio = w / float(h)
            if area < 1000 or ratio < 1.7 or ratio > 7.0:
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

    def show_cv_image(self, title, image):
        if image is None:
            return
        cv2.imshow(title, image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def segment_characters(self, plate):
        if plate is None:
            return []
        gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2:]
        char_regions = []
        # 放宽字符筛选阈值，适配绿牌细小字符
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w < 3 or h < 15:
                continue
            ratio = h / float(w)
            if ratio < 0.8:
                continue
            char_regions.append((x, y, w, h))
        # 从左到右排序字符
        char_regions = sorted(char_regions, key=lambda item: item[0])
        chars = []
        for region in char_regions:
            x, y, w, h = region
            char_img = binary[y:y+h, x:x+w]
            char_img = cv2.resize(char_img, (22, 44))
            chars.append(char_img)
        return chars

    def recognize_characters(self, plate):
        if plate is None:
            return ""
        # 放大4倍提升分辨率
        plate_resize = cv2.resize(plate, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(plate_resize, cv2.COLOR_BGR2GRAY)
        # 自适应均衡，解决逆光反光、绿牌渐变底色
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        # 自适应二值化替代固定OTSU，适配绿底白字
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 13, 3
        )
        # 形态学分离粘连字符
        kernel_sep = cv2.getStructuringElement(cv2.MORPH_RECT, (2,6))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_sep)
        blur = cv2.GaussianBlur(binary, (3, 3), 1)

        text = pytesseract.image_to_string(blur, config=OCR_CONFIG)
        clean_text = text.strip().replace("\n", "").replace(" ", "")
        return clean_text

    def save_image(self, image, filename):
        if image is not None:
            cv2.imwrite(filename, image)

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

    def run(self):
        self.root.mainloop()

def main():
    print("正在启动车牌识别系统...")
    app = PlateRecognitionSystem()
    print("GUI创建完成，进入主循环...")
    app.run()

if __name__ == "__main__":
    main()