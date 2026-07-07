from __future__ import annotations
from dataclasses import dataclass
import cv2
import numpy as np
# 从同目录dataset模块导入四点排序、透视矫正函数
from dataset import order_points, warp_plate_from_points

# 数据类：存储车牌定位整套结果，包含中间图、矫正车牌、四点坐标，供GUI可视化展示
@dataclass
class PlateLocation:
    plate_image: np.ndarray | None   # 透视矫正后的标准车牌图像，没检测到车牌则为None
    box_points: np.ndarray | None    # 检测到车牌的四个角坐标数组
    debug_image: np.ndarray          # 原图+绘制候选框、最终车牌标注的调试图
    stages: dict[str, np.ndarray]    # 字典存储所有预处理中间图像（灰度/边缘/掩膜等）

def preprocess_image(image: np.ndarray) -> dict[str, np.ndarray]:
    """
    图像预处理主函数：降噪、提取垂直边缘、HSV车牌颜色掩膜、形态学融合
    输入：原始BGR车辆图片
    返回：各类中间处理图像字典，用于后续定位与GUI分步展示
    """
    # 1. 彩色图转灰度图，减少计算量，彩色三通道只保留亮度信息
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 2. 5*5高斯模糊，平滑图片，消除细小噪点，避免误产生边缘
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    # 3. Sobel X算子，只提取垂直边缘（车牌文字都是竖线，过滤水平干扰线条）
    grad_x = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3)
    # 把梯度负数转为正数，方便二值化
    grad_x = cv2.convertScaleAbs(grad_x)
    # OTSU自适应二值化，自动分割文字边缘与背景，得到黑白边缘图
    _, edge_binary = cv2.threshold(grad_x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 4. 转换HSV色彩空间，HSV对光照鲁棒，精准筛选蓝/绿/黄车牌底色
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # 蓝牌HSV阈值区间
    blue_mask = cv2.inRange(hsv, np.array([95, 70, 70]), np.array([140, 255, 255]))
    # 新能源绿牌HSV阈值区间
    green_mask = cv2.inRange(hsv, np.array([35, 40, 40]), np.array([95, 255, 255]))
    # 黄牌HSV阈值区间
    yellow_mask = cv2.inRange(hsv, np.array([10, 60, 60]), np.array([40, 255, 255]))
    # 按位或：合并三种车牌颜色掩膜，只要像素属于任意车牌色就保留白色
    color_mask = cv2.bitwise_or(blue_mask, green_mask)
    color_mask = cv2.bitwise_or(color_mask, yellow_mask)

    # 5. 融合边缘图+颜色掩膜，双重约束，大幅减少广告牌、车身误检
    combined = cv2.bitwise_or(edge_binary, color_mask)
    # 形态闭运算：填补字符间隙，把分散的车牌文字连成完整矩形区域
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 5))
    morph = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_close, iterations=2)
    # 形态开运算：消除细小杂色噪点、无关小色块
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
    morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel_open, iterations=1)
    # 轻微膨胀，扩充车牌区域，避免轮廓断裂
    morph = cv2.dilate(morph, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 3)), 1)

    # 返回所有处理中间图，供GUI多标签页展示每一步效果
    return {
        "gray": gray,
        "blur": blur,
        "edge": edge_binary,
        "color_mask": color_mask,
        "morph": morph,
    }

def _score_candidate(
    contour: np.ndarray,
    image_shape: tuple[int, int, int],
    color_mask: np.ndarray,
) -> tuple[float, np.ndarray] | None:
    """
    私有函数：对单个轮廓打分，判断是否为真实车牌
    参数：轮廓、原图尺寸、车牌颜色掩膜
    返回：(综合得分, 车牌四点坐标) 不符合条件返回None
    """
    # 获取轮廓最小外接矩形（倾斜矩形）
    rect = cv2.minAreaRect(contour)
    (center_x, center_y), (width, height), _ = rect
    # 过滤极小轮廓
    if width <= 1 or height <= 1:
        return None
    # 统一宽>高，方便计算车牌标准长宽比
    if width < height:
        width, height = height, width
    # 国标车牌长宽比范围 2.2~6.5，超出直接丢弃
    ratio = width / max(height, 1e-6)
    if not (2.2 <= ratio <= 6.5):
        return None
    # 面积过滤：太小色块直接排除
    area = width * height
    image_area = image_shape[0] * image_shape[1]
    if area < image_area * 0.002:
        return None

    # 获取矩形四个角点，并标准化四点顺序（左上、右上、右下、左下）
    box = cv2.boxPoints(rect).astype(np.float32)
    box = order_points(box)
    # 取矩形在图中的范围，防止坐标越界
    x, y, w, h = cv2.boundingRect(box.astype(np.int32))
    x = max(0, x)
    y = max(0, y)
    w = min(image_shape[1] - x, w)
    h = min(image_shape[0] - y, h)
    if w <= 0 or h <= 0:
        return None

    # 统计该区域内车牌颜色像素占比，占比越高越像车牌（权重最高）
    region_mask = color_mask[y : y + h, x : x + w]
    color_ratio = float(np.mean(region_mask > 0))
    # 轮廓规整度：越接近矩形分数越高
    contour_area = cv2.contourArea(contour)
    rectangularity = contour_area / max(area, 1.0)
    # 车牌大多在图片垂直中部区域，偏离中间扣分
    vertical_bias = 1.0 - abs((center_y / image_shape[0]) - 0.55)

    # 加权综合打分，颜色占比权重最大，是判断核心依据
    score = (
        2.5 * color_ratio
        + 1.2 * rectangularity
        + 1.5 * min(area / image_area, 0.08) / 0.08
        + 0.5 * vertical_bias
    )
    return score, box

def locate_license_plate(image: np.ndarray) -> PlateLocation:
    """
    车牌定位主函数：预处理→提取轮廓→打分筛选最优车牌→透视矫正
    输入：原始车辆BGR图
    返回：PlateLocation对象（矫正车牌、四点、调试图、所有中间处理图）
    """
    # 执行全套图像预处理，拿到形态图与各中间图
    stages = preprocess_image(image)
    morph = stages["morph"]
    color_mask = stages["color_mask"]
    # 查找所有白色连通区域轮廓
    contours_result = cv2.findContours(
        morph.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    # 兼容不同OpenCV版本返回格式
    contours = contours_result[0] if len(contours_result) == 2 else contours_result[1]
    # 复制原图作为调试绘图画布
    debug = image.copy()
    best_score = -1.0   # 记录最高轮廓分数
    best_box = None     # 最优车牌四点坐标

    # 遍历全部轮廓逐一打分筛选
    for contour in contours:
        candidate = _score_candidate(contour, image.shape, color_mask)
        if candidate is None:
            continue
        score, box = candidate
        # 橙色绘制所有候选车牌框，方便调试查看候选区域
        cv2.polylines(
            debug, [box.astype(np.int32)], True, (255, 180, 0), 2, cv2.LINE_AA
        )
        # 更新最优车牌
        if score > best_score:
            best_score = score
            best_box = box

    plate_image = None
    # 如果筛选到有效车牌，执行透视变换矫正倾斜畸变
    if best_box is not None:
        plate_image = warp_plate_from_points(image, best_box, output_size=(440, 140))
        # 绿色粗线绘制最终识别到的车牌框
        cv2.polylines(
            debug, [best_box.astype(np.int32)], True, (0, 255, 0), 3, cv2.LINE_AA
        )
        # 在车牌左上角标注Plate文字
        cv2.putText(
            debug,
            "Plate",
            tuple(best_box[0].astype(int) + np.array([0, -8])),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    # 封装定位结果返回
    return PlateLocation(
        plate_image=plate_image,
        box_points=best_box,
        debug_image=debug,
        stages=stages,
    )

def detect_plate_color(plate_image: np.ndarray) -> str:
    """
    判断矫正后车牌底色：blue蓝 / green新能源绿 / yellow黄 / unknown未知
    输入：矫正完成的标准车牌图像
    返回：车牌颜色字符串
    """
    h, w = plate_image.shape[:2]
    # 裁剪车牌中间核心区域，去除上下边框干扰
    roi = plate_image[int(h * 0.12) : int(h * 0.88), int(w * 0.08) : int(w * 0.92)]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # 分别生成三种车牌颜色掩膜
    masks = {
        "blue": cv2.inRange(hsv, np.array([95, 60, 40]), np.array([140, 255, 255])),
        "green": cv2.inRange(hsv, np.array([35, 25, 25]), np.array([95, 255, 255])),
        "yellow": cv2.inRange(hsv, np.array([10, 60, 60]), np.array([40, 255, 255])),
    }
    # 计算每种颜色像素占比
    ratios = {name: float(np.mean(mask > 0)) for name, mask in masks.items()}
    # 取占比最高的颜色，占比低于8%判定为未知
    color, ratio = max(ratios.items(), key=lambda item: item[1])
    return color if ratio >= 0.08 else "unknown"

def normalize_character(char_image: np.ndarray) -> np.ndarray:
    """
    字符归一化函数：将分割出的任意大小字符统一为40*20标准黑白图
    输入：单字符灰度/彩色图
    返回：居中标准化40×20字符模板图
    """
    # 彩色转灰度
    if len(char_image.shape) == 3:
        char_image = cv2.cvtColor(char_image, cv2.COLOR_GRAY2BGR)
        char_image = cv2.cvtColor(char_image, cv2.COLOR_GRAY2BGR)
    # 找到字符白色像素坐标，判断是否为空字符
    ys, xs = np.where(char_image > 0)
    if len(xs) == 0 or len(ys) == 0:
        return np.zeros((40, 20), dtype=np.uint8)
    # 裁剪字符有效区域，去掉四周空白
    char_crop = char_image[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    h, w = char_crop.shape
    # 固定字符高度32，等比例缩放宽度
    target_h = 32
    scale = target_h / max(h, 1)
    new_w = max(1, int(round(w * scale)))
    resized = cv2.resize(char_crop, (new_w, target_h), interpolation=cv2.INTER_AREA)
    # 创建40*20黑色画布，居中放置字符
    canvas = np.zeros((40, 20), dtype=np.uint8)
    if new_w > 18:
        resized = cv2.resize(resized, (18, target_h), interpolation=cv2.INTER_AREA)
        new_w = 18
    x_offset = (20 - new_w) // 2
    y_offset = (40 - target_h) // 2
    canvas[y_offset : y_offset + target_h, x_offset : x_offset + new_w] = resized
    # 二值化，纯黑白字符，消除灰度干扰
    _, canvas = cv2.threshold(canvas, 127, 255, cv2.THRESH_BINARY)
    return canvas

def _estimate_slots(width: int, char_count: int) -> list[tuple[int, int]]:
    """
    预估每个字符的左右分割区间：区分7位普通牌、8位新能源绿牌间隔
    参数：车牌宽度、字符数量7/8
    返回：每个字符左右坐标列表
    """
    margin = int(width * 0.04)
    # 绿牌第二位后间隔更大，国标格式
    gap = int(width * (0.05 if char_count == 7 else 0.035))
    available = width - margin * 2 - gap
    char_width = available / char_count
    slots: list[tuple[int, int]] = []
    cursor = float(margin)
    for index in range(char_count):
        left = int(round(cursor))
        right = int(round(cursor + char_width))
        slots.append((left, right))
        cursor += char_width
        # 第二个字符后增加间隔（绿牌区分D/F）
        if index == 1:
            cursor += gap
    return slots

def _refine_slots(projection: np.ndarray, slots: list[tuple[int, int]]) -> list[tuple[int]]:
    """
    利用垂直投影直方图优化分割线，修正预估区间误差
    参数：垂直投影数组、初步预估分割区间
    返回：优化后的精准分割坐标
    """
    if len(slots) <= 1:
        return slots
    width = len(projection)
    refined_bounds = [slots[0][0]]
    search_radius = max(4, width // 35)
    # 在预估分割线附近找像素最少的间隙（字符分割谷值）
    for current, nxt in zip(slots, slots[1:]):
        boundary = (current[1] + nxt[0]) // 2
        left = max(0, boundary - search_radius)
        right = min(width - 1, boundary + search_radius)
        local_projection = projection[left : right + 1]
        refined_bounds.append(left + int(np.argmin(local_projection)))
    refined_bounds.append(slots[-1][1])
    refined_slots = []
    for index in range(len(refined_bounds) - 1):
        left = refined_bounds[index]
        right = refined_bounds[index + 1]
        if right - left < 4:
            left, right = slots[index]
        refined_slots.append((left, right))
    return refined_slots

def _trim_foreground(char_region: np.ndarray) -> np.ndarray:
    """裁剪字符四周空白区域，只保留文字像素"""
    if np.count_nonzero(char_region) == 0:
        return char_region
    row_projection = np.sum(char_region > 0, axis=1)
    col_projection = np.sum(char_region > 0, axis=0)
    rows = np.where(row_projection > 0)[0]
    cols = np.where(col_projection > 0)[0]
    return char_region[rows[0] : rows[-1] + 1, cols[0] : cols[-1]]

def split_plate_characters(
    plate_image: np.ndarray,
    expected_chars: int | None = None,
) -> tuple[list[np.ndarray], np.ndarray, np.ndarray, str]:
    """
    车牌字符分割总函数：根据底色7/8位分割，输出标准化单个字符
    输入：矫正后车牌、指定字符数量（None自动识别颜色判断）
    返回：[分割字符列表, 车牌二值图, 分割标注调试图, 车牌颜色]
    """
    # 先识别车牌颜色，自动确定分割7/8个字符
    plate_color = detect_plate_color(plate_image)
    if expected_chars is None:
        expected_chars = 8 if plate_color == "green" else 7
    # 车牌转灰度、轻微降噪
    gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    # 不同车牌底色选用相反二值模式
    if plate_color == "blue":
        # 蓝牌：黑字白底，正常二值
        threshold_type = cv2.THRESH_BINARY + cv2.THRESH_OTSU
    else:
        # 黄/绿牌：白字黑底，反向二值
        threshold_type = cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    _, binary = cv2.threshold(blur, 0, 255, threshold_type)

    # 裁剪车牌无用上下左右边框
    h, w = binary.shape
    top = int(h * 0.16)
    bottom = int(h * 0.92)
    left = int(w * 0.03)
    right = int(w * 0.97)
    roi = binary[top:bottom, left:right]
    # 开运算去除细小噪点
    roi = cv2.morphologyEx(
        roi,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)),
        iterations=1,
    )
    # 垂直投影：每一列白色像素总和，谷值就是字符分割缝隙
    projection = np.sum(roi > 0, axis=0).astype(np.float32)
    # 先预估分割区间，再用投影精准修正
    slots = _estimate_slots(roi.shape[1], expected_chars)
    slots = _refine_slots(projection, slots)
    # 创建画布绘制分割框，用于GUI展示
    debug = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
    characters: list[np.ndarray] = []

    # 逐区间裁剪单个字符，归一化存入列表
    for index, (x1, x2) in enumerate(slots):
        x1 = max(0, x1)
        x2 = min(roi.shape[1], x2)
        char_region = roi[:, x1:x2]
        # 裁剪空白
        char_region = _trim_foreground(char_region)
        # 标准化统一尺寸
        normalized = normalize_character(char_region)
        characters.append(normalized)
        # 在调试图画绿色分割框、编号
        cv2.rectangle(debug, (x1, 0), (x2, roi.shape[0] - 1), (0, 255, 0), 1)
        cv2.putText(
            debug,
            str(index),
            (x1 + 2, 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )
    return characters, binary, debug, plate_color
