from __future__ import annotations
# 导入界面、文件对话框、弹窗基础库
import base64
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
# 图像处理核心库
import cv2
import numpy as np
# 导入识别系统、识别结果实体类（同目录system模块）
from system import PlateRecognitionSystem,RecognitionOutput


# GUI主界面类：整个车牌识别可视化窗口全部逻辑
class LicensePlateApp:
    def __init__(self, root: tk.Tk, system: PlateRecognitionSystem) -> None:
        """
        GUI窗口初始化构造函数
        :param root: tk顶层主窗口对象
        :param system: 车牌识别核心业务系统实例
        """
        # 绑定窗口、识别系统到实例变量
        self.root = root
        self.system = system
        # 记录当前选中的图片路径，未导入时为空
        self.current_image_path: str | None = None
        # 存储所有标签页容器：{标签名称: 画布Frame}
        self.tabs: dict[str, ttk.Frame] = {}
        # 设置窗口标题、固定宽高尺寸
        self.root.title("基于OpenCV的车牌识别系统")
        self.root.geometry("1360x860")
        # 加载界面样式、搭建所有控件布局
        self._build_style()
        self._build_layout()

    def _build_style(self) -> None:
        """配置全局界面字体、颜色、控件样式"""
        style = ttk.Style()
        # 使用clam轻量化主题
        style.theme_use("clam")
        # 普通面板背景色
        style.configure("TFrame", background="#f3f5f7")
        # 普通标签字体、背景
        style.configure("TLabel", background="#f3f5f7", font=("Microsoft YaHei", 10))
        # 大标题样式（加粗22号字）
        style.configure("Title.TLabel", font=("Microsoft YaHei", 22, "bold"))
        # 识别结果大号加粗字体
        style.configure("Result.TLabel", font=("Microsoft YaHei", 24, "bold"))
        # 按钮字体
        style.configure("TButton", font=("Microsoft YaHei", 10))
        # 分组框标题字体
        style.configure("TLabelframe", font=("Microsoft YaHei", 11, "bold"))
        style.configure("TLabelframe.Label", font=("Microsoft YaHei", 11, "bold"))

    def _build_layout(self) -> None:
        """搭建窗口所有控件：标题、按钮区、结果区、多标签画布、字符展示栏、底部状态栏"""
        # 主容器，铺满整个窗口，内外边距12
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)
        # 系统大标题
        ttk.Label(main, text="基于OpenCV的车牌识别系统", style="Title.TLabel").pack(pady=(0, 10))

        # 控制按钮分组框
        control = ttk.LabelFrame(main, text="控制区域", padding=10)
        control.pack(fill=tk.X)
        button_bar = ttk.Frame(control)
        button_bar.pack(fill=tk.X)
        # 导入图片按钮，绑定加载函数
        ttk.Button(button_bar, text="导入图片", command=self._load_image, width=14).pack(side=tk.LEFT, padx=4)
        # 开始识别按钮，初始禁用（必须先导入图片才能点）
        self.recognize_button = ttk.Button(
            button_bar,
            text="开始识别",
            command=self._run_recognition,
            width=14,
            state=tk.DISABLED,
        )
        self.recognize_button.pack(side=tk.LEFT, padx=4)
        # 清空所有结果按钮
        ttk.Button(button_bar, text="清空结果", command=self._reset, width=14).pack(side=tk.LEFT, padx=4)

        # 识别结果展示分组框
        result_frame = ttk.LabelFrame(control, text="识别结果", padding=10)
        result_frame.pack(fill=tk.X, pady=(10, 0))
        # 大号车牌结果文本
        self.result_label = ttk.Label(result_frame, text="请先导入车牌图片", style="Result.TLabel", foreground="#333333")
        self.result_label.pack(side=tk.LEFT, padx=4)
        # 右侧小字：置信度、车牌颜色
        self.extra_label = ttk.Label(result_frame, text="置信度: -    车牌颜色: -", foreground="#555555")
        self.extra_label.pack(side=tk.RIGHT, padx=4)

        # 多标签页容器（切换各类处理效果图）
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        # 循环创建10个图像处理步骤标签页
        for title in ["原图", "灰度图", "边缘增强", "颜色掩膜", "形态学结果", "车牌定位", "车牌校正", "车牌二值化", "字符分割", "结果标注"]:
            self.tabs[title] = self._create_image_tab(title)

        # 底部单字符预览区域
        chars_frame = ttk.LabelFrame(main, text="分割字符", padding=8)
        chars_frame.pack(fill=tk.X)
        self.char_canvas = tk.Canvas(chars_frame, height=110, bg="#222222", highlightthickness=0)
        self.char_canvas.pack(fill=tk.X)

        # 底部状态栏，显示当前操作状态
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, pady=(8, 0))

    def _create_image_tab(self, title: str) -> ttk.Frame:
        """创建单个标签页：包含画布+横竖滚动条，用于展示大图"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=title)
        # 黑色画布用于绘制图片
        canvas = tk.Canvas(frame, bg="#1e1e1e", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        # 垂直滚动条
        scrollbar_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar_y.pack(fill=tk.Y, side=tk.RIGHT)
        # 水平滚动条
        scrollbar_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=canvas.xview)
        scrollbar_x.pack(fill=tk.X, side=tk.BOTTOM)
        # 画布绑定滚动条联动
        canvas.configure(xscrollcommand=scrollbar_x.set, yscrollcommand=scrollbar_y.set)
        # 画布挂载到页面，后续存图片对象防回收
        frame.canvas = canvas
        return frame

    def _to_photo_image(self, image: np.ndarray, max_size: tuple[int, int]) -> tk.PhotoImage:
        """
        OpenCV图像 → tk可显示图片
        原理：cv图像二进制编码base64，绕过PIL兼容问题
        :param image: opencv BGR图像矩阵
        :param max_size: 画布最大宽高，大图自动缩小
        :return tk.PhotoImage：tk专用图像对象
        """
        height, width = image.shape[:2]
        # 计算缩放比例，不拉伸，等比例缩小
        scale = min(max_size[0] / max(width, 1), max_size[1] / max(height, 1), 1.0)
        if scale < 1.0:
            image = cv2.resize(
                image,
                (max(1, int(width * scale)), max(1, int(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        # 图片编码为png二进制流
        success, buffer = cv2.imencode(".png", image)
        if not success:
            raise ValueError("图像编码失败")
        # base64编码传给tk图像
        encoded = base64.b64encode(buffer.tobytes())
        return tk.PhotoImage(data=encoded)

    def _display_image(self, title: str, image: np.ndarray | None) -> None:
        """指定标签页画布绘制图像，灰度图自动转彩色显示"""
        frame = self.tabs[title]
        canvas = frame.canvas
        canvas.delete("all")
        if image is None:
            return
        display = image
        # 单通道灰度图转三通道BGR才能正常渲染
        if len(display.shape) == 2:
            display = cv2.cvtColor(display, cv2.COLOR_GRAY2BGR)
        photo = self._to_photo_image(display, max_size=(1080, 620))
        # 左上角绘制图片
        canvas.create_image(20, 20, anchor=tk.NW, image=photo)
        # 保存图像引用，tk会自动回收图片导致黑屏
        frame.photo = photo
        # 更新滚动范围适配图片大小
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _display_chars(self, chars: list[np.ndarray]) -> None:
        """底部画布批量绘制分割后的单个字符小图"""
        self.char_canvas.delete("all")
        if not chars:
            return
        x = 10  # 起始X坐标
        photo_refs = []  # 保存所有字符图像，防止被垃圾回收黑屏
        for index, char_image in enumerate(chars):
            # 字符灰度转彩色
            display = cv2.cvtColor(char_image, cv2.COLOR_GRAY2BGR)
            # 统一缩放字符尺寸
            display = cv2.resize(display, (36, 72), interpolation=cv2.NEAREST)
            photo = self._to_photo_image(display, max_size=(36, 72))
            self.char_canvas.create_image(x, 20, anchor=tk.NW, image=photo)
            # 字符下方绘制编号
            self.char_canvas.create_text(x + 18, 100, text=str(index + 1), fill="#ffffff")
            x += 48  # 每个字符间隔48像素
            photo_refs.append(photo)
        self.char_canvas.photos = photo_refs
        # 更新画布滚动边界
        self.char_canvas.configure(scrollregion=self.char_canvas.bbox("all"))

    def _load_image(self) -> None:
        """导入图片按钮触发函数：弹出文件选择框读取本地图片"""
        image_path = filedialog.askopenfilename(
            title="选择待识别车牌图片",
            filetypes=[
                ("图像文件", "*.jpg *.jpeg *.png *.bmp"),
                ("所有文件", "*.*"),
            ],
        )
        # 用户取消选择直接返回
        if not image_path:
            return
        # 记录当前图片路径，启用识别按钮
        self.current_image_path = image_path
        self.recognize_button.config(state=tk.NORMAL)
        self.status_var.set(f"已加载图片: {os.path.basename(image_path)}")
        # 重置结果文字
        self.result_label.config(text="图片已导入，请点击开始识别", foreground="#333333")
        self.extra_label.config(text="置信度: -    车牌颜色: -")
        # 清空所有标签画布、字符预览
        for title in self.tabs:
            self.tabs[title].canvas.delete("all")
        self.char_canvas.delete("all")
        # 加载原图并绘制到「原图」标签页
        try:
            image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is not None:
                self._display_image("原图", image)
        except Exception:
            pass

    def _show_output(self, output: RecognitionOutput) -> None:
        """接收识别结果对象，刷新所有画布、结果文字、字符预览"""
        # 遍历所有处理步骤图，逐个绘制对应标签页
        for title, image in output.stages.items():
            if title in self.tabs:
                self._display_image(title, image)
        # 绘制分割字符预览
        self._display_chars(output.char_images)
        # 根据识别成功/失败修改文字颜色
        if output.success:
            self.result_label.config(
                text=f"识别结果: {output.plate_text}",
                foreground="#0a8f3d",
            )
        else:
            self.result_label.config(text=output.message, foreground="#c62828")
        # 拼接置信度、车牌颜色；CCPD数据集追加真实标注文本
        extra_text = f"置信度: {output.confidence:.3f}    车牌颜色: {output.plate_color}"
        if output.reference_text:
            extra_text += f"    CCPD标注: {output.reference_text}"
        self.extra_label.config(text=extra_text)
        # 更新底部状态栏提示
        self.status_var.set(output.message)

    def _run_recognition(self) -> None:
        """「开始识别」按钮触发：调用识别系统执行全流程"""
        # 未导入图片弹窗警告
        if not self.current_image_path:
            messagebox.showwarning("提示", "请先导入图片")
            return
        self.status_var.set("正在识别，请稍候...")
        # 刷新界面，避免窗口卡死
        self.root.update_idletasks()
        try:
            # 调用系统识别接口，传入图片路径
            output = self.system.recognize_path(self.current_image_path)
            # 渲染所有识别结果到界面
            self._show_output(output)
        except Exception as exc:
            # 捕获任意识别异常，弹窗报错
            messagebox.showerror("错误", f"识别失败: {exc}")
            self.status_var.set(f"识别失败: {exc}")

    def _reset(self) -> None:
        """清空结果按钮：重置整个界面到初始就绪状态"""
        self.current_image_path = None
        # 禁用识别按钮
        self.recognize_button.config(state=tk.DISABLED)
        # 重置结果文字
        self.result_label.config(text="请先导入车牌图片", foreground="#333333")
        self.extra_label.config(text="置信度: -    车牌颜色: -")
        self.status_var.set("已清空")
        # 清空所有标签画布，释放图片引用
        for frame in self.tabs.values():
            frame.canvas.delete("all")
            if hasattr(frame, "photo"):
                delattr(frame, "photo")
        # 清空字符预览画布
        self.char_canvas.delete("all")
