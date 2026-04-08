"""
Pipeline xử lý biển số xe hoàn chỉnh.

Kết hợp (khớp với platenewmodel.py):
  Preprocess.py    → HSV → TopHat/BlackHat → Gaussian → Adaptive Threshold
  PlateDetector    → Canny → Contour 4 đỉnh → Xoay → Crop → Phóng to 3×
  CharSegmenter    → Morphology dilate → Contour ký tự → Resize 64×64
  KNNRecognizer    → sklearn pkl model → Predict từng ký tự

Flow:
  Ảnh gốc → Color Correct → Preprocess → Detect plate → Segment chars → KNN predict → Kết quả
"""

import cv2
import numpy as np
import os
import math
import time
import logging
from typing import Optional, List, Tuple
from datetime import datetime

from .char_segmenter import CharSegmenter
from .knn_recognizer import KNNRecognizer

# Import Preprocess module (cùng thư mục)
from . import Preprocess

logger = logging.getLogger(__name__)

# Thông số detect biển số (giống platenewmodel.py)
IMG_W, IMG_H = 1280, 720
PLATE_RATIO_MIN = 1.0
PLATE_RATIO_MAX = 7.0
PLATE_AREA_MIN = 0.002
PLATE_AREA_MAX = 0.30
MIN_CHARS = 3
DETECT_SCALES = [1.0, 0.65, 1.5]


class PlateResult:
    """Kết quả nhận diện biển số."""

    def __init__(self, plate_text='', confidence=0.0, plate_image_path='',
                 full_image_path='', success=False, error='', timestamp='',
                 first_line='', second_line=''):
        self.plate_text = plate_text
        self.confidence = confidence
        self.plate_image_path = plate_image_path
        self.full_image_path = full_image_path
        self.success = success
        self.error = error
        self.timestamp = timestamp or datetime.now().isoformat()
        self.first_line = first_line
        self.second_line = second_line

    def to_dict(self) -> dict:
        return {
            'plateText': self.plate_text,
            'confidence': self.confidence,
            'plateImagePath': self.plate_image_path,
            'fullImagePath': self.full_image_path,
            'success': self.success,
            'error': self.error,
            'timestamp': self.timestamp,
        }


class PlateProcessor:
    """
    Pipeline xử lý biển số xe hoàn chỉnh.

    Sử dụng:
    - Shared CameraManager để chụp ảnh (tránh xung đột PiCamera2)
    - Model knn_plate_model.pkl đã train sẵn
    - Color correction CLAHE giống platenewmodel.py
    """

    def __init__(
        self,
        model_path: str = 'knn_plate_model.pkl',
        output_dir: str = 'captures',
        camera_manager=None,
        debug: bool = False,
    ):
        self.model_path = model_path
        self.output_dir = output_dir
        self.camera_manager = camera_manager  # Shared CameraManager
        self.debug = debug

        self.segmenter = CharSegmenter(debug=debug)
        self.recognizer = KNNRecognizer(k=3)

        os.makedirs(output_dir, exist_ok=True)

    def init(self) -> bool:
        """
        Khởi tạo: tải model KNN pkl.

        Returns:
            True nếu khởi tạo thành công
        """
        # Thử load model pkl (sklearn) — ưu tiên
        if os.path.exists(self.model_path):
            logger.info(f"Đang tải KNN model: {self.model_path}")
            if self.recognizer.load_pkl_model(self.model_path):
                logger.info("✅ KNN model (sklearn pkl) đã sẵn sàng")
                return True

        # Thử tìm ở các vị trí khác
        alt_paths = [
            os.path.join(os.path.dirname(__file__), '..', 'knn_plate_model.pkl'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'knn_plate_model.pkl'),
            'models/knn_plate_model.pkl',
        ]
        for alt in alt_paths:
            if os.path.exists(alt):
                logger.info(f"Tìm thấy model tại: {alt}")
                if self.recognizer.load_pkl_model(alt):
                    return True

        # Fallback: train từ ký tự tự sinh
        logger.warning("Không tìm thấy knn_plate_model.pkl, dùng model tự sinh (kém chính xác)")
        return self.recognizer.train_from_generated()

    def process_image(self, image: np.ndarray, gate_type: str = 'entry') -> PlateResult:
        """
        Xử lý biển số từ 1 ảnh.

        Pipeline khớp với platenewmodel.py:
        1. Color correct (CLAHE)
        2. Resize → 1280×720
        3. Preprocess (HSV → TopHat/BlackHat → Gaussian → Adaptive Threshold)
        4. Canny → Contour 4 đỉnh → Lọc ratio/area
        5. Xoay + Crop ROI → Phóng to 3×
        6. Morphology dilate → Tìm contour ký tự → Resize 64×64
        7. KNN predict từng ký tự → Ghép biển số

        Args:
            image: Ảnh BGR từ camera (đã color correct nếu từ capture_still)
            gate_type: 'entry' hoặc 'exit'

        Returns:
            PlateResult
        """
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')

        # Lưu ảnh gốc
        full_img_filename = f"{gate_type}_{timestamp_str}_full.jpg"
        full_img_path = os.path.join(self.output_dir, full_img_filename)
        cv2.imwrite(full_img_path, image)

        # Resize chuẩn
        img = cv2.resize(image, (IMG_W, IMG_H))

        # Multi-scale detection (giống platenewmodel.py)
        best_result = None

        for scale in DETECT_SCALES:
            result = self._detect_at_scale(img, scale, gate_type, timestamp_str, full_img_path)
            if result is not None and result.success:
                best_result = result
                break  # Đã tìm thấy ở scale này

        if best_result:
            best_result.timestamp = timestamp.isoformat()
            return best_result

        return PlateResult(
            success=False,
            error='Không phát hiện được biển số trong ảnh',
            full_image_path=full_img_path,
            timestamp=timestamp.isoformat(),
        )

    def _detect_at_scale(self, img_bgr: np.ndarray, scale: float,
                          gate_type: str, timestamp_str: str,
                          full_img_path: str) -> Optional[PlateResult]:
        """
        Detect biển số ở 1 scale cụ thể.
        Logic giống hệt _detect_at_scale trong platenewmodel.py.
        """
        if scale != 1.0:
            new_w = int(IMG_W * scale)
            new_h = int(IMG_H * scale)
            img_s = cv2.resize(img_bgr, (new_w, new_h))
        else:
            new_w, new_h = IMG_W, IMG_H
            img_s = img_bgr.copy()

        area_s = new_w * new_h

        # Preprocess giống platenewmodel.py
        imgGrayscale, imgThresh = Preprocess.preprocess(img_s)

        # Canny + Dilate
        canny = cv2.Canny(imgThresh, 250, 255)
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(canny, kernel, iterations=1)

        # Tìm contour
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:30]

        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.06 * peri, True)
            if len(approx) != 4:
                continue

            bx, by, bw, bh = cv2.boundingRect(approx)
            if bh == 0:
                continue
            ratio = bw / bh
            plate_area = (bw * bh) / area_s

            if not (PLATE_RATIO_MIN <= ratio <= PLATE_RATIO_MAX):
                continue
            if not (PLATE_AREA_MIN <= plate_area <= PLATE_AREA_MAX):
                continue

            # Xoay theo góc nghiêng (giống platenewmodel.py)
            pts = sorted(approx[:, 0].tolist(), key=lambda p: p[1], reverse=True)
            (px1, py1), (px2, py2) = pts[0], pts[1]
            ke = abs(px1 - px2)
            doi = abs(py1 - py2)
            angle = math.atan(doi / ke) * (180.0 / math.pi) if ke != 0 else 0

            mask = np.zeros(imgGrayscale.shape, np.uint8)
            cv2.drawContours(mask, [approx], 0, 255, -1)
            rx, ry = np.where(mask == 255)
            topx, topy = int(np.min(rx)), int(np.min(ry))
            botx, boty = int(np.max(rx)), int(np.max(ry))

            roi = img_s[topx:botx, topy:boty].copy()
            imgThreshROI = imgThresh[topx:botx, topy:boty].copy()
            if roi.size == 0:
                continue

            # Xoay
            ptCenter = ((botx - topx) / 2, (boty - topy) / 2)
            sign = -1 if px1 < px2 else 1
            rotMat = cv2.getRotationMatrix2D(ptCenter, sign * angle, 1.0)
            warp_size = (boty - topy, botx - topx)
            roi = cv2.warpAffine(roi, rotMat, warp_size)
            imgThreshROI = cv2.warpAffine(imgThreshROI, rotMat, warp_size)

            # Phóng to 3× (giống platenewmodel.py)
            roi = cv2.resize(roi, (0, 0), fx=3, fy=3)
            imgThreshROI = cv2.resize(imgThreshROI, (0, 0), fx=3, fy=3)

            # Tách ký tự
            char_results = self.segmenter.segment(imgThreshROI, roi)

            if len(char_results) < MIN_CHARS:
                continue

            # Nhận diện từng ký tự bằng KNN
            h_roi = roi.shape[0]
            first_line = ""
            second_line = ""
            confidences = []

            for char_img, (cx, cy, cw, ch) in char_results:
                char, conf = self.recognizer.predict(char_img)
                confidences.append(conf)
                if cy < h_roi / 2:
                    first_line += char
                else:
                    second_line += char

            if first_line == "" and second_line == "":
                continue

            plate_str = (first_line + "-" + second_line).strip("-")
            avg_conf = sum(confidences) / len(confidences) if confidences else 0

            # Lưu ảnh biển số đã crop
            plate_img_filename = f"{gate_type}_{timestamp_str}_plate.jpg"
            plate_img_path = os.path.join(self.output_dir, plate_img_filename)
            cv2.imwrite(plate_img_path, roi)

            logger.info(f"[{gate_type.upper()}] scale={scale} Biển số: {plate_str} "
                       f"({len(char_results)} ký tự, conf={avg_conf:.1f}%)")

            return PlateResult(
                plate_text=plate_str,
                confidence=round(avg_conf, 1),
                plate_image_path=plate_img_path,
                full_image_path=full_img_path,
                success=True,
                first_line=first_line,
                second_line=second_line,
            )

        return None

    def capture_and_process(self, gate_type: str = 'entry') -> PlateResult:
        """
        Chụp ảnh từ shared camera và xử lý biển số.
        Dùng CameraManager.capture_still() — có color correction CLAHE.
        """
        if self.camera_manager is None:
            return PlateResult(
                success=False,
                error='Camera manager chưa được thiết lập',
                timestamp=datetime.now().isoformat(),
            )

        image = self.camera_manager.capture_still()
        if image is None:
            return PlateResult(
                success=False,
                error='Không thể chụp ảnh từ PiCamera',
                timestamp=datetime.now().isoformat(),
            )
        return self.process_image(image, gate_type)

    def process_from_file(self, image_path: str, gate_type: str = 'entry') -> PlateResult:
        """Xử lý biển số từ file ảnh (dùng để test)."""
        image = cv2.imread(image_path)
        if image is None:
            return PlateResult(
                success=False,
                error=f'Không đọc được file ảnh: {image_path}',
                timestamp=datetime.now().isoformat(),
            )
        return self.process_image(image, gate_type)

    def cleanup(self):
        """Giải phóng tài nguyên (camera do CameraManager quản lý riêng)."""
        pass
