"""
Phát hiện và cắt vùng biển số xe từ ảnh chụp PiCamera.

Pipeline:
  1. Chuyển ảnh sang grayscale
  2. Lọc nhiễu (Bilateral Filter) 
  3. Phát hiện cạnh (Canny Edge)
  4. Tìm contour hình chữ nhật → ứng viên biển số
  5. Lọc theo tỷ lệ khung hình (aspect ratio biển số VN)
  6. Crop và trả về vùng biển số
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)

# Tỷ lệ biển số xe Việt Nam
# Biển 1 dòng: ~34cm x 9cm → ratio ~3.8
# Biển 2 dòng: ~19cm x 15cm → ratio ~1.27
PLATE_ASPECT_RATIO_1LINE = (2.5, 5.0)   # min, max cho biển 1 dòng
PLATE_ASPECT_RATIO_2LINE = (0.8, 1.8)   # min, max cho biển 2 dòng
MIN_PLATE_AREA_RATIO = 0.005             # Tỷ lệ diện tích tối thiểu so với ảnh gốc
MAX_PLATE_AREA_RATIO = 0.3               # Tỷ lệ diện tích tối đa


class PlateDetector:
    """Phát hiện và cắt vùng biển số xe từ ảnh."""

    def __init__(self, debug: bool = False):
        self.debug = debug

    def detect(self, image: np.ndarray) -> Optional[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Phát hiện biển số xe trong ảnh.

        Args:
            image: Ảnh BGR từ camera (numpy array)

        Returns:
            Tuple (plate_image, (x, y, w, h)) hoặc None nếu không tìm thấy
        """
        if image is None or image.size == 0:
            logger.warning("Ảnh đầu vào rỗng")
            return None

        img_h, img_w = image.shape[:2]
        img_area = img_h * img_w

        # Bước 1: Chuyển sang grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Bước 2: Lọc nhiễu giữ cạnh
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)

        # Bước 3: Phát hiện cạnh
        edges = cv2.Canny(filtered, 30, 200)

        # Bước 4: Tìm contour
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Sắp xếp theo diện tích giảm dần, lấy top 30
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:30]

        candidates: List[Tuple[np.ndarray, Tuple[int, int, int, int], float]] = []

        for contour in contours:
            # Xấp xỉ đa giác
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

            # Biển số thường là hình chữ nhật (4 đỉnh)
            if len(approx) >= 4 and len(approx) <= 6:
                x, y, w, h = cv2.boundingRect(approx)
                area = w * h
                aspect_ratio = w / h if h > 0 else 0

                # Kiểm tra diện tích
                area_ratio = area / img_area
                if area_ratio < MIN_PLATE_AREA_RATIO or area_ratio > MAX_PLATE_AREA_RATIO:
                    continue

                # Kiểm tra tỷ lệ khung hình (biển 1 dòng hoặc 2 dòng)
                is_1line = PLATE_ASPECT_RATIO_1LINE[0] <= aspect_ratio <= PLATE_ASPECT_RATIO_1LINE[1]
                is_2line = PLATE_ASPECT_RATIO_2LINE[0] <= aspect_ratio <= PLATE_ASPECT_RATIO_2LINE[1]

                if is_1line or is_2line:
                    # Tính điểm ưu tiên: ưu tiên vùng ở giữa-dưới ảnh (vị trí biển số thường thấy)
                    center_y = y + h / 2
                    y_score = center_y / img_h  # 0..1, ưu tiên phần dưới
                    area_score = area_ratio      # ưu tiên diện tích lớn hơn
                    score = y_score * 0.4 + area_score * 0.6

                    candidates.append((approx, (x, y, w, h), score))

        if not candidates:
            logger.info("Không tìm thấy biển số trong ảnh")
            # Thử phương pháp thay thế: Morphological approach
            return self._detect_morphological(image)

        # Chọn ứng viên có điểm cao nhất
        candidates.sort(key=lambda c: c[2], reverse=True)
        _, (x, y, w, h), score = candidates[0]

        # Mở rộng vùng crop thêm một chút
        pad_x = int(w * 0.05)
        pad_y = int(h * 0.1)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(img_w, x + w + pad_x)
        y2 = min(img_h, y + h + pad_y)

        plate_img = image[y1:y2, x1:x2]

        if self.debug:
            debug_img = image.copy()
            cv2.rectangle(debug_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.imwrite('debug_plate_detect.jpg', debug_img)

        logger.info(f"Phát hiện biển số tại ({x},{y},{w},{h}), score={score:.3f}")
        return plate_img, (x1, y1, x2 - x1, y2 - y1)

    def _detect_morphological(self, image: np.ndarray) -> Optional[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Phương pháp thay thế: Dùng morphological operations để tìm biển số.
        Hiệu quả khi contour approach thất bại.
        """
        img_h, img_w = image.shape[:2]
        img_area = img_h * img_w

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Blackhat: làm nổi vùng tối trên nền sáng (chữ trên biển số)
        rect_kern = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, rect_kern)

        # Threshold
        _, thresh = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Dilation để nối các ký tự
        sq_kern = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 5))
        dilated = cv2.dilate(thresh, sq_kern, iterations=1)

        # Tìm contour
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            aspect_ratio = w / h if h > 0 else 0
            area_ratio = area / img_area

            if area_ratio < MIN_PLATE_AREA_RATIO:
                continue

            is_1line = PLATE_ASPECT_RATIO_1LINE[0] <= aspect_ratio <= PLATE_ASPECT_RATIO_1LINE[1]
            is_2line = PLATE_ASPECT_RATIO_2LINE[0] <= aspect_ratio <= PLATE_ASPECT_RATIO_2LINE[1]

            if is_1line or is_2line:
                pad_x = int(w * 0.05)
                pad_y = int(h * 0.15)
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(img_w, x + w + pad_x)
                y2 = min(img_h, y + h + pad_y)

                plate_img = image[y1:y2, x1:x2]
                logger.info(f"Phát hiện biển số (morphological) tại ({x},{y},{w},{h})")
                return plate_img, (x1, y1, x2 - x1, y2 - y1)

        logger.info("Không tìm thấy biển số (cả 2 phương pháp)")
        return None
