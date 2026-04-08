"""
Nhận diện ký tự biển số xe bằng KNN.

Hỗ trợ 2 loại model:
  1. sklearn KNeighborsClassifier (knn_plate_model.pkl) — model chính đã train sẵn
  2. OpenCV KNN (fallback khi không có sklearn model)

Model pkl đã train:
  - Input: ảnh grayscale 64×64, flatten / 255.0
  - Output: ký tự string ('0'-'9', 'A'-'Z')
  - k=3, metric=euclidean
"""

import cv2
import numpy as np
import os
import json
import pickle
import logging
from typing import Tuple, Optional, List

logger = logging.getLogger(__name__)

# Ký tự hợp lệ trên biển số xe Việt Nam
VALID_DIGITS = '0123456789'
VALID_LETTERS = 'ABCDEFGHKLMNPSTUVXYZ'
VALID_CHARS = VALID_DIGITS + VALID_LETTERS

# Kích thước ảnh ký tự — phải khớp với model đã train
CHAR_W_PKL = 64   # Kích thước cho model pkl (sklearn)
CHAR_H_PKL = 64
CHAR_SIZE_CV = 20  # Kích thước cho model OpenCV (fallback)


class KNNRecognizer:
    """Nhận diện ký tự bằng KNN (sklearn hoặc OpenCV)."""

    def __init__(self, k: int = 3):
        self.k = k
        self.is_trained = False
        self._model = None          # sklearn KNeighborsClassifier
        self._knn_cv = None         # OpenCV KNN (fallback)
        self._char_labels: List[str] = []
        self._use_sklearn = False
        self._char_w = CHAR_W_PKL
        self._char_h = CHAR_H_PKL

    # ================================================================
    # LOAD MODEL PKL (sklearn) — phương thức chính
    # ================================================================
    def load_pkl_model(self, pkl_path: str) -> bool:
        """
        Tải model KNN đã train từ file .pkl (sklearn KNeighborsClassifier).

        File này được tạo bởi retrain_knn.py:
          - Input: ảnh 64×64 grayscale, flatten / 255.0
          - Output: ký tự string
          - k=3, metric=euclidean

        Args:
            pkl_path: Đường dẫn đến file knn_plate_model.pkl

        Returns:
            True nếu load thành công
        """
        if not os.path.exists(pkl_path):
            logger.error(f"Không tìm thấy file model: {pkl_path}")
            return False

        try:
            with open(pkl_path, 'rb') as f:
                self._model = pickle.load(f)

            self._use_sklearn = True
            self._char_w = CHAR_W_PKL
            self._char_h = CHAR_H_PKL
            self.is_trained = True

            # Lấy danh sách classes từ model
            if hasattr(self._model, 'classes_'):
                self._char_labels = list(self._model.classes_)

            logger.info(f"Loaded sklearn KNN model: {pkl_path}")
            logger.info(f"  Classes: {self._char_labels}")
            logger.info(f"  Input size: {self._char_w}×{self._char_h}")
            if hasattr(self._model, 'n_neighbors'):
                logger.info(f"  k={self._model.n_neighbors}")

            return True

        except Exception as e:
            logger.error(f"Lỗi load model pkl: {e}")
            return False

    # ================================================================
    # PREDICT
    # ================================================================
    def predict(self, char_image: np.ndarray) -> Tuple[str, float]:
        """
        Nhận diện 1 ký tự.

        Args:
            char_image: Ảnh ký tự grayscale (binary hoặc gray)

        Returns:
            Tuple (ký_tự, confidence 0-100)
        """
        if not self.is_trained:
            logger.error("KNN chưa được train/load")
            return ('?', 0.0)

        # Resize về kích thước model yêu cầu
        resized = cv2.resize(char_image, (self._char_w, self._char_h))

        if self._use_sklearn:
            return self._predict_sklearn(resized)
        else:
            return self._predict_opencv(resized)

    def _predict_sklearn(self, char_image: np.ndarray) -> Tuple[str, float]:
        """Predict bằng sklearn KNeighborsClassifier."""
        # Flatten + normalize (giống lúc train)
        sample = np.float32(char_image.flatten() / 255.0).reshape(1, -1)

        # Predict
        char = self._model.predict(sample)[0]

        # Tính confidence từ predict_proba
        try:
            proba = self._model.predict_proba(sample)[0]
            confidence = float(np.max(proba) * 100)
        except Exception:
            # Fallback: dùng kneighbors distance
            try:
                distances, indices = self._model.kneighbors(sample)
                avg_dist = float(np.mean(distances))
                max_possible = self._char_w * self._char_h  # rough max
                confidence = max(0, min(100, (1 - avg_dist / max_possible) * 100))
            except Exception:
                confidence = 50.0

        return (str(char), round(confidence, 1))

    def _predict_opencv(self, char_image: np.ndarray) -> Tuple[str, float]:
        """Predict bằng OpenCV KNN (fallback)."""
        if self._knn_cv is None:
            return ('?', 0.0)

        sample = char_image.reshape(1, -1).astype(np.float32)
        ret, result, neighbours, dist = self._knn_cv.findNearest(sample, self.k)

        label = int(result[0][0])
        if 0 <= label < len(self._char_labels):
            char = self._char_labels[label]
        else:
            char = '?'

        avg_dist = float(np.mean(dist))
        max_dist = self._char_w * self._char_h * 255
        confidence = max(0, min(100, (1 - avg_dist / max_dist) * 100))

        return (char, round(confidence, 1))

    def predict_plate(self, char_images: List[np.ndarray]) -> Tuple[str, float]:
        """
        Nhận diện chuỗi ký tự biển số.

        Args:
            char_images: List ảnh ký tự (grayscale)

        Returns:
            Tuple (chuỗi_biển_số, confidence trung bình)
        """
        if not char_images:
            return ('', 0.0)

        chars = []
        confidences = []

        for img in char_images:
            char, conf = self.predict(img)
            chars.append(char)
            confidences.append(conf)

        plate_text = ''.join(chars)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # Format biển số VN
        plate_text = self._format_plate(plate_text)

        logger.info(f"Nhận diện biển số: {plate_text} (confidence={avg_confidence:.1f}%)")
        return (plate_text, round(avg_confidence, 1))

    def _format_plate(self, raw: str) -> str:
        """
        Format chuỗi ký tự thành biển số VN.
        Ví dụ: 51G88888 → 51G-888.88
        """
        if len(raw) < 4:
            return raw

        if len(raw) >= 7:
            part1 = raw[:3]
            part2 = raw[3:]
            if len(part2) >= 5:
                return f"{part1}-{part2[:3]}.{part2[3:]}"
            elif len(part2) >= 3:
                return f"{part1}-{part2}"

        return raw

    # ================================================================
    # LEGACY: Load/Save OpenCV model
    # ================================================================
    def load_model(self, path: str) -> bool:
        """Tải model OpenCV KNN từ file .xml."""
        model_path = path + '.xml'
        meta_path = path + '_meta.json'

        if not os.path.exists(model_path) or not os.path.exists(meta_path):
            logger.error(f"Không tìm thấy file model: {path}")
            return False

        with open(meta_path, 'r') as f:
            meta = json.load(f)
            self._char_labels = meta['char_labels']
            self.k = meta.get('k', 5)

        self._knn_cv = cv2.ml.KNearest.load(model_path)
        self._use_sklearn = False
        self._char_w = CHAR_SIZE_CV
        self._char_h = CHAR_SIZE_CV
        self.is_trained = True
        return True

    def save_model(self, path: str):
        """Lưu model ra file (chỉ cho OpenCV KNN)."""
        if self._use_sklearn and self._model is not None:
            pkl_path = path + '.pkl'
            with open(pkl_path, 'wb') as f:
                pickle.dump(self._model, f)
            logger.info(f"Model pkl đã lưu: {pkl_path}")
        elif self._knn_cv is not None:
            model_path = path + '.xml'
            self._knn_cv.save(model_path)
            meta_path = path + '_meta.json'
            with open(meta_path, 'w') as f:
                json.dump({'char_labels': self._char_labels, 'k': self.k}, f)
            logger.info(f"Model OpenCV đã lưu: {model_path}")

    def train_from_generated(self) -> bool:
        """Train KNN từ ký tự tự sinh (fallback cuối cùng)."""
        samples = []
        labels = []

        for i, char in enumerate(VALID_CHARS):
            for variation in range(20):
                img = self._generate_char_image(char, variation)
                sample = img.reshape(1, -1).astype(np.float32)
                samples.append(sample)
                labels.append(i)

        self._char_labels = list(VALID_CHARS)
        train_data = np.vstack(samples)
        train_labels = np.array(labels, dtype=np.float32).reshape(-1, 1)

        self._knn_cv = cv2.ml.KNearest.create()
        self._knn_cv.setDefaultK(self.k)
        self._knn_cv.setIsClassifier(True)
        self._knn_cv.train(train_data, cv2.ml.ROW_SAMPLE, train_labels)

        self._use_sklearn = False
        self._char_w = CHAR_SIZE_CV
        self._char_h = CHAR_SIZE_CV
        self.is_trained = True
        logger.info(f"KNN trained (generated): {len(samples)} mẫu")
        return True

    def _generate_char_image(self, char: str, variation: int) -> np.ndarray:
        """Sinh ảnh ký tự với biến thể nhẹ."""
        sz = CHAR_SIZE_CV
        img = np.zeros((sz, sz), dtype=np.uint8)
        font_scale = 0.5 + (variation % 5) * 0.05
        thickness = 1 + (variation // 10)
        text_size = cv2.getTextSize(char, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        x = max(0, (sz - text_size[0]) // 2 + (variation % 3) - 1)
        y = max(text_size[1], (sz + text_size[1]) // 2 + (variation % 3) - 1)
        cv2.putText(img, char, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, 255, thickness)
        if variation % 4 == 0:
            noise = np.random.randint(0, 30, img.shape, dtype=np.uint8)
            img = cv2.add(img, noise)
        if variation % 3 == 0:
            img = cv2.GaussianBlur(img, (3, 3), 0)
        return img
