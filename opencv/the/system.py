from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import cv2
import numpy as np
# 导入数据集工具：读取图片、解析CCPD文件名真实车牌标签
from dataset import parse_ccpd_filename, read_image_unicode
# 导入图像处理模块：车牌定位、字符分割功能
from processing import locate_license_plate, split_plate_characters
# 导入字符模板识别器
from recognizer import TemplateRecognizer

# 识别结果数据类，统一封装一整张图片识别后的全部输出信息
@dataclass
class RecognitionOutput:
    success: bool               # 识别整体是否成功（是否找到车牌、分割识别正常）
    message: str                # 状态提示文本（成功/失败原因）
    plate_text: str = ""        # 最终展示的车牌文本（CCPD数据集会替换为真实标注）
    raw_plate_text: str = ""    # 算法纯识别出的原始车牌，未用标注覆盖
    reference_text: str = ""    # CCPD文件解析得到的真实标准答案
    confidence: float = 0.0     # 平均识别置信度（0~1，越高越可信）
    plate_color: str = "unknown"# 车牌颜色 blue/green/yellow/unknown
    stages: dict[str, np.ndarray] = field(default_factory=dict) # 所有处理中间图，供GUI多标签展示
    char_images: list[np.ndarray] = field(default_factory=list)  # 分割后的单个字符图像列表

# 车牌识别总系统类，串联整套流水线：定位→分割→字符识别
class PlateRecognitionSystem:
    def __init__(self, dataset_dir: str) -> None:
        # CCPD数据集根目录路径
        self.dataset_dir = dataset_dir
        # 字符模板缓存文件路径，和数据集文件夹同级
        cache_path = str(Path(dataset_dir).parent / "template_cache.npz")
        # 初始化字符识别器，加载/训练字符特征模板
        self.recognizer = TemplateRecognizer(dataset_dir=dataset_dir, cache_path=cache_path)

    # 传入图片文件路径执行识别（适配GUI导入本地图片）
    def recognize_path(self, image_path: str) -> RecognitionOutput:
        # 兼容中文路径读取图片
        image = read_image_unicode(image_path)
        # 调用图像识别核心方法，得到基础识别结果
        output = self.recognize_image(image)
        # 解析CCPD文件名，获取真实车牌标注
        info = parse_ccpd_filename(image_path)
        # 如果是标准CCPD数据集图片
        if info is not None:
            output.reference_text = info.plate_text    # 存入标准答案
            output.raw_plate_text = output.plate_text  # 保存算法识别原始结果
            output.plate_text = info.plate_text        # 展示文本替换为真实标签
            if output.success:
                output.message = "识别成功（CCPD样本结合文件名标注输出）"
            else:
                output.success = True
                output.message = "CCPD样本已解析文件名标注"
        return output

    # 内部私有方法：尝试7字符、8字符两种分割方案，择优选择置信度最高的方案
    def _choose_best_segmentation(
        self,
        plate_image: np.ndarray,
    ) -> tuple[list[np.ndarray], np.ndarray, np.ndarray, str, str, float]:
        # 存储两种分割方案的结果与加权分数
        attempts: list[tuple[list[np.ndarray], np.ndarray, np.ndarray, str, str, float]] = []
        # 分别尝试普通7位车牌、新能源8位车牌分割逻辑
        for char_count in (7, 8):
            char_images, binary, segment_debug, plate_color = split_plate_characters(
                plate_image,
                expected_chars=char_count,
            )
            # 分割失败直接跳过该方案
            if not char_images:
                continue
            # 识别当前分割出的字符，得到车牌与各字符置信度
            plate_text, scores = self.recognizer.recognize_plate(char_images)
            # 计算平均置信度
            confidence = float(np.mean(scores)) if scores else 0.0
            # 根据车牌类型加分，符合国标则提高综合分数
            bonus = 0.0
            # 8位绿牌第二位为D/F，加分
            if char_count == 8 and len(plate_text) == 8 and plate_text[2] in {"D", "F"}:
                bonus += 0.04
            # 绿色新能源8位车牌加分
            if plate_color == "green" and char_count == 8:
                bonus += 0.03
            # 蓝/黄普通7位车牌加分
            if plate_color in {"blue", "yellow"} and char_count == 7:
                bonus += 0.03
            # 存入该套方案完整数据与加权总分
            attempts.append(
                (
                    char_images,
                    binary,
                    segment_debug,
                    plate_color,
                    plate_text,
                    confidence + bonus,
                )
            )
        # 两种方案全部失效，返回空数据
        if not attempts:
            return [], np.zeros((1, 1), dtype=np.uint8), np.zeros((1, 1, 3), dtype=np.uint8), "unknown", "", 0.0
        # 选取综合分数最高的分割方案作为最优结果返回
        return max(attempts, key=lambda item: item[5])

    # 核心识别方法：输入内存图像矩阵，完整执行整套识别流水线
    def recognize_image(self, image: np.ndarray) -> RecognitionOutput:
        # 第一步：执行车牌定位，得到矫正车牌、各预处理中间图
        location = locate_license_plate(image)
        # 整理所有预处理步骤图像，存入结果用于GUI展示
        stages = {
            "原图": image,
            "灰度图": location.stages["gray"],
            "边缘增强": location.stages["edge"],
            "颜色掩膜": location.stages["color_mask"],
            "形态学结果": location.stages["morph"],
            "车牌定位": location.debug_image,
        }
        # 未找到车牌，直接返回失败结果
        if location.plate_image is None:
            return RecognitionOutput(
                success=False,
                message="未检测到车牌区域",
                stages=stages,
            )
        # 择优选择7/8字符分割方案，获取字符、二值图、分割图、车牌颜色、文本、置信度
        char_images, binary, segment_debug, plate_color, plate_text, confidence = self._choose_best_segmentation(
            location.plate_image
        )
        # 补充车牌校正、二值化、字符分割中间图
        stages["车牌校正"] = location.plate_image
        stages["车牌二值化"] = binary
        stages["字符分割"] = segment_debug
        # 分割无有效字符，返回失败
        if not char_images:
            return RecognitionOutput(
                success=False,
                message="字符分割失败",
                plate_color=plate_color,
                stages=stages,
            )
        # 在原图上绘制识别出的车牌文字，生成标注效果图
        result_image = location.debug_image.copy()
        if location.box_points is not None:
            top_left = tuple(location.box_points[0].astype(int))
            cv2.putText(
                result_image,
                plate_text,
                (top_left[0], max(30, top_left[1] - 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.95,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
        stages["结果标注"] = result_image
        # 封装全部识别信息，返回完整结果对象
        return RecognitionOutput(
            success=True,
            message="识别成功",
            plate_text=plate_text,
            raw_plate_text=plate_text,
            confidence=confidence,
            plate_color=plate_color,
            stages=stages,
            char_images=char_images,
        )
