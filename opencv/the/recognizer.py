from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import cv2
import numpy as np
# 从同目录dataset导入数据集解析相关工具、字符常量
from dataset import ALPHABETS, ADS, PROVINCES, iter_ccpd_images, parse_ccpd_filename, read_image_unicode, warp_plate_from_points
# 从同目录processing导入字符归一化、车牌字符分割函数
from processing import normalize_character, split_plate_characters


class TemplateRecognizer:
    """
    基于模板特征匹配的车牌字符识别器
    1. 自动读取CCPD训练集生成各字符平均特征模板，缓存npz文件避免重复训练
    2. 无数据集/缺少字符时自动生成内置文字模板兜底
    3. 提取字符轮廓、投影、不变矩多维特征，余弦相似度匹配识别单字符
    4. 根据车牌位置限制候选字符集（第一位省份、第二位字母、新能源第三位D/F）提升准确率
    """
    def __init__(
        self,
        dataset_dir: str,
        cache_path: str | None = None,
        max_samples_per_char: int = 18,
        max_train_images: int = 1200,
    ) -> None:
        # CCP数据集根目录
        self.dataset_dir = dataset_dir
        # 模板特征缓存文件路径，默认数据集同级template_cache.npz
        self.cache_path = cache_path or str(Path(dataset_dir).parent / "template_cache.npz")
        # 单个字符最多采集多少张样本用于求平均特征
        self.max_samples_per_char = max_samples_per_char
        # 训练最多读取多少张CCPD图片，防止训练耗时过长
        self.max_train_images = max_train_images
        # 存储每个字符的平均特征向量 {字符:特征数组}
        self.prototype_features: dict[str, np.ndarray] = {}
        # 存储每个字符训练样本数量
        self.prototype_counts: dict[str, int] = {}
        # 当前拥有可识别字符集合
        self.available_characters: set[str] = set()
        # 加载缓存或重新训练模板
        self._load_or_build()

    def _load_or_build(self) -> None:
        """读取缓存文件，存在则直接加载模板；不存在则执行训练并保存缓存"""
        cache_file = Path(self.cache_path)
        # 判断缓存文件是否存在
        if cache_file.exists():
            try:
                # 加载npz缓存
                cache = np.load(cache_file, allow_pickle=True)
                feature_map = cache["feature_map"].item()
                count_map = cache["count_map"].item()
                # 转换为浮点数组存入实例变量
                self.prototype_features = {
                    key: np.asarray(value, dtype=np.float32)
                    for key, value in feature_map.items()
                }
                self.prototype_counts = {
                    key: int(value) for key, value in count_map.items()
                }
                self.available_characters = set(self.prototype_features.keys())
                # 补齐缺失字符的内置兜底模板
                self._add_ascii_fallback_templates()
                return
            except Exception:
                # 缓存损坏/读取失败，跳过缓存重新训练
                pass
        # 无可用缓存，执行数据集训练
        self._build_from_dataset()
        # 创建父目录，压缩保存模板缓存
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            cache_file,
            feature_map=self.prototype_features,
            count_map=self.prototype_counts,
        )

    def _build_from_dataset(self) -> None:
        """遍历CCPD训练集图片，提取所有字符特征，计算每类字符平均模板"""
        # 字典：key=字符，value=该字符所有样本特征列表
        feature_samples: dict[str, list[np.ndarray]] = defaultdict(list)
        processed_images = 0
        # 遍历训练集所有图片路径
        for image_path in iter_ccpd_images(self.dataset_dir, split="train"):
            # 达到最大训练图片数量，提前终止循环
            if processed_images >= self.max_train_images:
                break
            # 解析文件名获取真实车牌标注信息
            info = parse_ccpd_filename(image_path)
            if info is None:
                continue
            try:
                # 读取图片、四点透视矫正得到标准车牌
                image = read_image_unicode(image_path)
                plate_image = warp_plate_from_points(image, info.vertices, output_size=(440, 140))
                # 按真实字符数量分割车牌单字符
                characters, _, _, _ = split_plate_characters(
                    plate_image,
                    expected_chars=len(info.plate_text),
                )
            except Exception:
                # 单张图片读取/分割失败，跳过该样本
                continue
            # 分割字符数量和标注车牌长度不一致，样本无效跳过
            if len(characters) != len(info.plate_text):
                continue
            # 遍历图片每个字符，采集特征
            for char, char_image in zip(info.plate_text, characters):
                # 该字符样本已达上限，不再新增
                if len(feature_samples[char]) >= self.max_samples_per_char:
                    continue
                # 提取字符特征存入列表
                feature_samples[char].append(self.extract_features(char_image))
            processed_images += 1
            # 关键数字字母样本充足且训练超过300张，提前停止训练节省时间
            enough_samples = all(
                len(feature_samples[char]) >= min(4, self.max_samples_per_char)
                for char in {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "D", "F"}
                if char in feature_samples
            )
            if enough_samples and processed_images >= 300:
                break
        # 对每个字符所有样本取均值，生成标准模板特征
        self.prototype_features = {
            char: np.mean(np.stack(samples, axis=0), axis=0).astype(np.float32)
            for char, samples in feature_samples.items()
            if samples
        }
        # 记录每个字符样本数量
        self.prototype_counts = {
            char: len(samples)
            for char, samples in feature_samples.items()
            if samples
        }
        self.available_characters = set(self.prototype_features.keys())
        # 补充内置兜底字符模板
        self._add_ascii_fallback_templates()

    @staticmethod
    def extract_features(char_image: np.ndarray) -> np.ndarray:
        """
        静态方法：提取单字符多维特征向量
        特征包含：水平投影、垂直投影、4×2网格灰度均值、7阶Hu不变矩
        输入：归一化后的单字符黑白图
        返回：拼接完成的一维特征向量
        """
        # 统一字符标准尺寸
        char_image = normalize_character(char_image)
        binary = (char_image > 0).astype(np.float32)
        h, w = binary.shape
        # 水平投影特征：每行白色像素占比
        horizontal = np.sum(binary, axis=1) / max(w, 1)
        # 垂直投影特征：每列白色像素占比
        vertical = np.sum(binary, axis=0) / max(h, 1)
        grid_features = []
        grid_rows, grid_cols = 4, 2
        cell_h = h // grid_rows
        cell_w = w // grid_cols
        # 4行2列网格分块，每块平均亮度作为局部特征
        for row in range(grid_rows):
            for col in range(grid_cols):
                cell = binary[
                    row * cell_h : (row + 1) * cell_h,
                    col * cell_w : (col + 1) * cell_w,
                ]
                grid_features.append(float(np.mean(cell)))
        # 计算Hu不变矩（抗缩放、旋转、形变特征）
        moments = cv2.moments(char_image)
        hu = cv2.HuMoments(moments).flatten()
        # 对数压缩处理hu矩数值，避免极值影响相似度
        hu = np.sign(hu) * np.log10(np.abs(hu) + 1e-8)
        # 拼接所有特征为一维向量
        features = np.concatenate(
            [
                horizontal,
                vertical,
                np.array(grid_features, dtype=np.float32),
                hu.astype(np.float32),
            ]
        )
        return features.astype(np.float32)

    def _render_ascii_template(self, char: str) -> np.ndarray:
        """绘制内置标准字符图像，用于数据集缺失字符兜底"""
        canvas = np.zeros((40, 20), dtype=np.uint8)
        # 在黑色画布写入白色标准字符
        cv2.putText(
            canvas,
            char,
            (1, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.95,
            255,
            2,
            cv2.LINE_AA,
        )
        # 二值化纯黑白
        _, canvas = cv2.threshold(canvas, 0, 255, cv2.THRESH_BINARY)
        return normalize_character(canvas)

    def _add_ascii_fallback_templates(self) -> None:
        """遍历所有车牌字符，为训练缺失字符生成内置模板补齐"""
        for char in ALPHABETS + [str(i) for i in range(10)]:
            # 已有数据集模板则跳过
            if char in self.prototype_features:
                continue
            # 生成内置字符图并提取特征存入模板库
            template = self._render_ascii_template(char)
            self.prototype_features[char] = self.extract_features(template)
            self.prototype_counts[char] = 0
        # 更新可用字符集合
        self.available_characters = set(self.prototype_features.keys())

    def recognize_character(
        self,
        char_image: np.ndarray,
        allowed_characters: list[str] | None = None,
    ) -> tuple[str, float]:
        """
        单字符匹配识别
        :param char_image: 分割归一化后的字符图
        :param allowed_characters: 限定候选字符集（优化识别，如第一位仅省份）
        :return (识别字符, 余弦相似度分数 0~1 越高越匹配)
        """
        # 提取待识别字符特征
        feature = self.extract_features(char_image)
        # 候选字符列表，未指定则全部可用字符参与匹配
        candidates = allowed_characters or sorted(self.available_characters)
        best_char = "?"
        best_score = -1.0
        # 遍历所有候选字符计算余弦相似度
        for candidate in candidates:
            if candidate not in self.prototype_features:
                continue
            template_feature = self.prototype_features[candidate]
            # 余弦相似度公式
            denominator = np.linalg.norm(feature) * np.linalg.norm(template_feature)
            similarity = float(np.dot(feature, template_feature) / denominator) if denominator > 0 else 0.0
            # 更新最优匹配字符与分数
            if similarity > best_score:
                best_score = similarity
        return best_char, best_score

    def recognize_plate(self, char_images: list[np.ndarray]) -> tuple[str, list[float]]:
        """
        完整车牌批量识别
        :param char_images: 分割完成的单字符图像列表
        :return (拼接完整车牌字符串, 每个字符对应置信度列表)
        """
        recognized_chars: list[str] = []
        scores: list[float] = []
        char_count = len(char_images)
        # 逐字符识别，按车牌位置限制候选字符缩小匹配范围
        for index, char_image in enumerate(char_images):
            if index == 0:
                # 第0位：只能是省份汉字
                candidates = [char for char in PROVINCES if char in self.available_characters]
                if not candidates:
                    candidates = list(PROVINCES)
            elif index == 1:
                # 第1位：只能是大写字母
                candidates = list(ALPHABETS)
            elif char_count == 8 and index == 2:
                # 新能源绿牌第2位仅D/F
                candidates = ["D", "F"]
            else:
                # 其余位置：字母+数字
                candidates = list(ADS)
            # 执行单字符识别
            char, score = self.recognize_character(char_image, candidates)
            recognized_chars.append(char)
            scores.append(score)
        # 拼接车牌文本、返回全部置信度
        return "".join(recognized_chars), scores
