from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import cv2
import numpy as np

# 定义全国省份汉字列表，CCPD文件名中数字下标对应这里的省份
PROVINCES = [
    "皖", "沪", "津", "渝", "冀", "晋", "蒙", "辽", "吉", "黑",
    "苏", "浙", "京", "闽", "赣", "鲁", "豫", "鄂", "湘", "粤",
    "桂", "琼", "川", "贵", "云", "藏", "陕", "甘", "青", "宁",
    "新",
]
# 车牌可用大写字母，去掉I、O避免和数字混淆
ALPHABETS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M",
    "N", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
]
# 字母+0-9数字组合，车牌后半段字符库
ADS = ALPHABETS + [str(i) for i in range(10)]

# 数据实体类：存储单张CCPD图片完整标注信息
@dataclass
class CCPDInfo:
    image_path: str       # 图片完整路径
    plate_text: str       # 完整车牌字符串（如苏A88888）
    bbox: tuple[int, int, int, int]  # 车牌外接矩形 (x,y,宽,高)
    vertices: np.ndarray  # 车牌四个角点坐标数组

def read_image_unicode(image_path: str) -> np.ndarray:
    """
    兼容中文路径读取图片
    原生cv2.imread中文路径会读取失败，改用二进制缓冲读取
    :param image_path: 图片文件路径（支持中文文件夹/文件名）
    :return: cv2 BGR格式图像矩阵
    """
    # 二进制读取文件缓冲
    buffer = np.fromfile(image_path, dtype=np.uint8)
    # 二进制解码为图像
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    # 解码失败抛出异常提示
    if image is None:
        raise ValueError(f"无法读取图像: {image_path}")
    return image

def order_points(points: np.ndarray) -> np.ndarray:
    """
    无序四点标准化排序
    输入乱序四个角点，输出固定顺序：左上、右上、右下、左下
    :param points: 4行2列坐标数组
    :return: 排序后的四点坐标
    """
    pts = np.asarray(points, dtype=np.float32)
    # x+y之和最小=左上，x+y最大=右下
    s = pts.sum(axis=1)
    # x-y差值最小=右上，x-y最大=左下
    diff = np.diff(pts, axis=1).reshape(-1)
    ordered = np.zeros((4, 2), dtype=np.float32)
    ordered[0] = pts[np.argmin(s)]
    ordered[2] = pts[np.argmax(s)]
    ordered[1] = pts[np.argmin(diff)]
    ordered[3] = pts[np.argmax(diff)]
    return ordered

def warp_plate_from_points(
    image: np.ndarray,
    points: np.ndarray,
    output_size: tuple[int, int] = (440, 140),
) -> np.ndarray:
    """
    车牌透视矫正函数
    根据车牌四点，把倾斜、畸变车牌矫正为标准矩形车牌
    :param image: 原图矩阵
    :param points: 车牌四个角点
    :param output_size: 矫正后固定宽高
    :return: 拉直后的标准车牌图像
    """
    # 先标准化四点顺序
    rect = order_points(points)
    # 定义目标标准矩形四个顶点坐标
    dst = np.array(
        [
            [0, 0],
            [output_size[0] - 1, 0],
            [output_size[0] - 1, output_size[1] - 1],
            [0, output_size[1] - 1],
        ],
        dtype=np.float32,
    )
    # 计算透视变换矩阵
    transform = cv2.getPerspectiveTransform(rect, dst)
    # 执行透视映射，输出标准尺寸车牌
    return cv2.warpPerspective(image, transform, output_size)

def parse_ccpd_filename(image_path: str) -> CCPDInfo | None:
    """
    CCPD数据集文件名解析核心函数
    CCPD无独立标注文件，车牌坐标、文字全部藏在文件名内
    :param image_path: 图片完整路径
    :return: 解析成功返回CCPDInfo，格式损坏返回None
    """
    # 取出不带后缀的文件名
    stem = Path(image_path).stem
    # 按横杠分割文件名各信息段
    parts = stem.split("-")
    # 分段不足5段，不是标准CCPD文件，直接返回空
    if len(parts) < 5:
        return None
    try:
        # 第二段：车牌外接矩形坐标
        bbox_tokens = parts[2].split("_")
        left_top = tuple(int(v) for v in bbox_tokens[0].split("&"))
        right_bottom = tuple(int(v) for v in bbox_tokens[1].split("&"))
        # 第三段：车牌四个角点坐标
        vertex_tokens = parts[3].split("_")
        vertices = np.array(
            [
                [int(item.split("&")[0]), int(item.split("&")[1])]
                for item in vertex_tokens
            ],
            dtype=np.float32,
        )
        # 第四段：车牌字符下标数字序列
        label_tokens = [int(v) for v in parts[4].split("_")]
        if len(label_tokens) < 3:
            return None
        # 第一位=省份，第二位=字母，后面=数字/字母
        plate_chars = [PROVINCES[label_tokens[0]], ALPHABETS[label_tokens[1]]]
        plate_chars.extend(ADS[index] for index in label_tokens[2:])
        # 封装标注对象返回
        return CCPDInfo(
            image_path=image_path,
            plate_text="".join(plate_chars),
            bbox=(
                left_top[0],
                left_top[1],
                right_bottom[0] - left_top[0],
                right_bottom[1] - left_top[1],
            ),
            vertices=vertices,
        )
    # 下标越界、数字转换失败等异常直接返回None
    except (IndexError, ValueError):
        return None

def iter_ccpd_images(dataset_dir: str, split: str = "train") -> Iterable[str]:
    """
    批量遍历CCPD指定子集下所有图片路径
    :param dataset_dir: CCPD数据集根目录
    :param split: 子集名称 train/val/test，默认训练集
    :return: 该子集下全部图片路径列表
    """
    root = Path(dataset_dir)
    # 数据集文件夹不存在，返回空列表
    if not root.exists():
        return []
    image_files: list[str] = []
    # 递归遍历所有子文件夹
    for current_root, _, files in os.walk(dataset_dir):
        current_path = Path(current_root)
        # 只匹配对应子集文件夹，跳过其他文件夹
        if current_path.name.lower() != split.lower():
            continue
        # 筛选图片后缀
        for file_name in files:
            if file_name.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                image_files.append(str(current_path / file_name))
    # 路径排序后返回
    image_files.sort()
    return image_files
