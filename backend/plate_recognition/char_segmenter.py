"""
Phân tách ký tự từ ảnh biển số xe.

Pipeline (khớp với platenewmodel.py):
  1. Preprocess (HSV → TopHat/BlackHat → Gaussian → Adaptive Threshold)
  2. Morphology dilate để nối nét ký tự
  3. Tìm contour → lọc theo tỷ lệ ký tự
  4. Sắp xếp contour trái→phải, chia 2 dòng nếu cần
  5. Crop từng ký tự → resize 64×64 cho KNN sklearn model
"""

import cv2
import numpy as np
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

# Kích thước output khớp với model pkl đã train
RESIZED_IMAGE_WIDTH = 64
RESIZED_IMAGE_HEIGHT = 64

# Giới hạn kích thước ký tự (tỷ lệ diện tích ký tự / diện tích ROI)
Min_char = 0.01
Max_char = 0.09

# Tỷ lệ w/h hợp lệ cho ký tự
MIN_CHAR_RATIO = 0.25
MAX_CHAR_RATIO = 0.7


class CharSegmenter:
    """Phân tách từng ký tự từ ảnh biển số (ROI đã crop + threshold)."""

    def __init__(self, debug: bool = False):
        self.debug = debug

    def segment(self, plate_image_thresh: np.ndarray, plate_image_bgr: np.ndarray = None) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Phân tách ký tự từ ảnh biển số.

        Args:
            plate_image_thresh: Ảnh threshold đã xử lý (binary, 1 channel)
            plate_image_bgr: Ảnh BGR gốc (optional, để debug)

        Returns:
            List of (char_image_64x64, (x, y, w, h)) sắp xếp theo thứ tự đọc
        """
        if plate_image_thresh is None or plate_image_thresh.size == 0:
            return []

        h_roi, w_roi = plate_image_thresh.shape[:2]
        roi_area = h_roi * w_roi

        # Morphology dilate (giống platenewmodel.py)
        kernel3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thre_mor = cv2.morphologyEx(plate_image_thresh, cv2.MORPH_DILATE, kernel3)

        # Tìm contour ký tự
        contours, _ = cv2.findContours(thre_mor, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Lọc contour theo kích thước ký tự (giống platenewmodel.py)
        char_x_ind = {}
        char_x = []

        for ind, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            if h == 0:
                continue
            ratio_char = w / h
            char_area = w * h

            if (Min_char * roi_area < char_area < Max_char * roi_area) \
                    and (MIN_CHAR_RATIO < ratio_char < MAX_CHAR_RATIO):
                # Xử lý trùng x (giống platenewmodel.py)
                cx = x
                if cx in char_x:
                    cx += 1
                char_x.append(cx)
                char_x_ind[cx] = ind

        # Sắp xếp theo x (trái → phải)
        char_x = sorted(char_x)

        if not char_x:
            logger.warning("Không tìm thấy ký tự nào trong biển số")
            return []

        # Crop và resize từng ký tự
        result = []
        for xi in char_x:
            cnt = contours[char_x_ind[xi]]
            x, y, w, h = cv2.boundingRect(cnt)

            # Crop từ ảnh morphology
            char_crop = thre_mor[y:y + h, x:x + w]

            # Resize về 64×64 (khớp model pkl)
            char_resized = cv2.resize(char_crop, (RESIZED_IMAGE_WIDTH, RESIZED_IMAGE_HEIGHT))

            result.append((char_resized, (x, y, w, h)))

        if self.debug and plate_image_bgr is not None:
            self._draw_debug(plate_image_bgr, result)

        logger.info(f"Tìm thấy {len(result)} ký tự")
        return result

    def segment_two_lines(
        self,
        char_results: List[Tuple[np.ndarray, Tuple[int, int, int, int]]],
        roi_height: int
    ) -> Tuple[List[Tuple[np.ndarray, Tuple[int, int, int, int]]], List[Tuple[np.ndarray, Tuple[int, int, int, int]]]]:
        """
        Chia ký tự thành 2 dòng (biển số 2 dòng).

        Returns:
            (first_line, second_line) — mỗi dòng sắp xếp trái→phải
        """
        half_h = roi_height / 2
        first_line = []
        second_line = []

        for char_img, (x, y, w, h) in char_results:
            if y < half_h:
                first_line.append((char_img, (x, y, w, h)))
            else:
                second_line.append((char_img, (x, y, w, h)))

        return first_line, second_line

    def _draw_debug(self, plate_bgr, char_results):
        """Vẽ bounding box ký tự trên ảnh biển số."""
        debug = plate_bgr.copy()
        for i, (_, (x, y, w, h)) in enumerate(char_results):
            cv2.rectangle(debug, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(debug, str(i), (x, y - 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        cv2.imwrite('debug_char_segment.jpg', debug)
