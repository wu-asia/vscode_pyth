"""
实验四：基于OpenCV+百度AI云端API车牌识别系统
双模式：优先云端AI识别，网络异常自动降级本地OpenCV+Tesseract
Author : wu-asia
"""
import os
import cv2
import numpy as np
import pytesseract
import requests
import base64

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

# ===================== 百度AI车牌识别API配置（自行替换密钥） =====================
BAIDU_API_KEY = "9YSronlqcRAPBNQgZYwAt3ry"
BAIDU_SECRET_KEY = "A7ETaTeRMsFsJJ1IsrW1rBPzUfRqXqcN"

# Tesseract 本地OCR路径
pytesseract.pytesseract.tesseract_cmd = r"D:\Program Files\Tesseract-OCR\tesseract.exe"

# 本地三套OCR配置
OCR_FULL_WHITE_CONFIG = (
    r'--oem 3 '
    r'--psm 7 '
    r'-l chi_sim+eng '
    r'-c tessedit_char_whitelist=京沪津渝冀晋蒙辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川贵云藏陕甘青宁0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ·'
)
OCR_FULL_CONFIG = (
    r'--oem 3 '
    r'--psm 7 '
    r'-l chi_sim+eng '
)
OCR_CHINESE = r'--oem 3 --psm 10 -l chi_sim'
OCR_CHAR = r'--oem 3 --psm 10 -l eng'

# ===================== 百度AI接口工具函数 =====================
def get_baidu_token():
    """获取百度鉴权token，30天有效"""
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": BAIDU_API_KEY,
        "client_secret": BAIDU_SECRET_KEY
    }
    try:
        resp = requests.post(url, params=params, timeout=5)
        return resp.json().get("access_token", "")
    except Exception:
        return ""

def ai_plate_recognize(cv_img):
    """传入opencv图像，调用百度AI识别车牌，返回格式化结果"""
    token = get_baidu_token()
    if not token:
        return ""
    # 图片转base64
    _, buffer = cv2.imencode(".jpg", cv_img)
    img_b64 = base64.b64encode(buffer).decode("utf-8")
    # 请求接口
    req_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/license_plate?access_token={token}"
    post_data = {"image": img_b64, "multi_detect": "false"}
    try:
        res = requests.post(req_url, data=post_data, timeout=8)
        json_data = res.json()
        if "words_result" not in json_data or len(json_data["words_result"]) == 0:
            return ""
        plate_info = json_data["words_result"][0]
        num = plate_info["number"]
        color = plate_info["color"]
        return f"{num} ({color}牌)"
    except Exception:
        return ""

# ===================== GUI主程序类 =====================
class PlateRecognitionSystem:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("基于OpenCV+AI云端API车牌识别系统")
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
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 左侧画布
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
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
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
            # 第一步：优先调用百度AI云端识别
            ai_out = ai_plate_recognize(self.image)
            if ai_out:
                self.result_var.set(f"{ai_out}")
                return

            # 云端识别失败，降级本地OpenCV方案
            self.gray = self.gray_process(self.image)
            self.binary = self.image_preprocess(self.gray)
            self.plate = self.color_locate_plate(self.image)
            if self.plate is None:
                self.plate = self.locate_plate(self.binary)
            if self.plate is None:
                self.result_var.set("未检测到车牌")
                return

            full_text = self.recognize_characters(self.plate)
            char_imgs = self.segment_characters(self.plate)
            seg_text = ""
            if len(char_imgs) >= 6:
                buf = []
                for idx, img in enumerate(char_imgs):
                    if idx == 0:
                        buf.append(pytesseract.image_to_string(img, config=OCR_CHINESE).strip())
                    else:
                        buf.append(pytesseract.image_to_string(img, config=OCR_CHAR).strip())
                seg_text = "".join(buf)

            candidate_list = []
            if seg_text:
                candidate_list.append(seg_text)
            if full_text:
                candidate_list.append(full_text)

            self.result = "识别失败"
            for text in candidate_list:
                clean = text.replace("·", "").strip()
                if 6 <= len(clean) <= 9:
                    self.result = text
                    break
            self.result_var.set(f"本地识别：{self.result}")
        except Exception as e:
            messagebox.showerror("运行异常", f"{str(e)}")

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
        lower_blue = np.array([100, 80, 80])
        upper_blue = np.array([140, 255, 255])
        lower_yellow = np.array([10, 40, 60])
        upper_yellow = np.array([45, 255, 255])
        lower_green = np.array([35, 50, 60])
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
            if area < 1800:
                continue
            if ratio < 1.7 or ratio > 7.0:
                continue
            plate = image[y:y+h,x:x+w]
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
            if area < 1800:
                continue
            if ratio < 1.7 or ratio > 7.0:
                continue
            roi = self.image[y:y+h, x:x+w]
            hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            full_mask = cv2.inRange(hsv_roi, np.array([8,20,20]), np.array([142,255,255]))
            color_ratio = cv2.countNonZero(full_mask) / (w*h)
            if color_ratio > 0.18:
                plate = roi
                cv2.rectangle(self.image, (x, y), (x+w, y+h), (0, 255, 0), 2)
                break
        if plate is None:
            messagebox.showwarning("提示", "未检测到车牌！")
            return None
        self.show_image(self.image)
        return plate

    def segment_characters(self, plate):
        if plate is None:
            return []
        gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2:]
        char_regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w < 3 or h < 14:
                continue
            ratio = h / float(w)
            if ratio < 0.7 or ratio > 7.5:
                continue
            char_regions.append((x, y, w, h))
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
        plate_resize = cv2.resize(plate, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(plate_resize, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 17, 2)
        kernel_sep = cv2.getStructuringElement(cv2.MORPH_RECT, (2,6))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_sep)
        blur = cv2.GaussianBlur(binary, (3, 3), 1)

        text = pytesseract.image_to_string(blur, config=OCR_FULL_WHITE_CONFIG)
        clean_text = text.strip().replace("\n", "").replace(" ", "")
        fix_map = {"O":"0","I":"1","Z":"2","S":"5","B":"8"}
        fixed = ""
        for ch in clean_text:
            fixed += fix_map.get(ch, ch)
        return fixed

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

# 程序入口
def main():
    print("正在启动 云端AI+本地双模式车牌识别系统...")
    app = PlateRecognitionSystem()
    print("GUI加载完成，进入主循环")
    app.run()

if __name__ == "__main__":
    main()