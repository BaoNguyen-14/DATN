"""
Camera Manager - Shared PiCamera2 instance.

Quản lý 1 instance PiCamera2 dùng chung giữa:
  - PlateProcessor (chụp ảnh nhận diện biển số)
  - MJPEG Server (stream live video)

Thread-safe với threading.Lock.
"""

import cv2
import numpy as np
import time
import logging
from threading import Lock
from typing import Optional

logger = logging.getLogger('CameraManager')

# Camera resolution
CAM_W, CAM_H = 1280, 720


class CameraManager:
    """Quản lý PiCamera2 dùng chung, thread-safe."""

    def __init__(self):
        self._picam = None
        self._lock = Lock()
        self._available = False

    def init(self) -> bool:
        """Khởi tạo PiCamera2 (gọi 1 lần duy nhất)."""
        try:
            from picamera2 import Picamera2
            self._picam = Picamera2()

            # Dùng preview_configuration (vừa stream vừa capture được)
            # Giống platenewmodel.py: create_preview_configuration
            config = self._picam.create_preview_configuration(
                main={"format": "RGB888", "size": (CAM_W, CAM_H)}
            )
            self._picam.configure(config)
            self._picam.start()

            logger.info("Chờ camera ổn định (2s)...")
            time.sleep(2.0)

            # Thiết lập camera controls (giống platenewmodel.py)
            try:
                ctrl = {
                    "AeEnable": True,
                    "AwbEnable": True,
                    "AwbMode": 0,
                    "Sharpness": 1.5,
                }
                self._picam.set_controls(ctrl)
                logger.info("Camera controls đã áp dụng")
            except Exception as e:
                logger.warning(f"set_controls: {e}")

            self._available = True
            logger.info(f"✅ PiCamera2 sẵn sàng ({CAM_W}×{CAM_H})")
            return True

        except ImportError:
            logger.warning("picamera2 không khả dụng (không phải Raspberry Pi)")
            return False
        except Exception as e:
            logger.error(f"Lỗi khởi tạo PiCamera2: {e}")
            return False

    @property
    def available(self) -> bool:
        return self._available

    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Chụp 1 frame từ camera (BGR).
        Dùng cho MJPEG streaming.
        Thread-safe.
        """
        if not self._available or self._picam is None:
            return None
        try:
            with self._lock:
                img_rgb = self._picam.capture_array()
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            return img_bgr
        except Exception as e:
            logger.error(f"capture_frame error: {e}")
            return None

    def capture_still(self) -> Optional[np.ndarray]:
        """
        Chụp 1 ảnh tĩnh từ camera (BGR) với color correction.
        Dùng cho nhận diện biển số.
        Thread-safe.
        """
        if not self._available or self._picam is None:
            return None
        try:
            with self._lock:
                img_rgb = self._picam.capture_array()
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            # Color correction CLAHE (giống platenewmodel.py)
            img_bgr = color_correct(img_bgr)
            return img_bgr
        except Exception as e:
            logger.error(f"capture_still error: {e}")
            return None

    def cleanup(self):
        """Giải phóng camera."""
        if self._picam is not None:
            try:
                self._picam.stop()
                self._picam.close()
                logger.info("PiCamera2 đã đóng")
            except Exception:
                pass
            self._picam = None
            self._available = False


def color_correct(img_bgr: np.ndarray) -> np.ndarray:
    """
    Color correction bằng CLAHE trên kênh L (LAB).
    Giống hàm color_correct() trong platenewmodel.py.
    Giúp cải thiện chất lượng ảnh trước khi nhận diện.
    """
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


# Singleton instance
_camera_instance: Optional[CameraManager] = None


def get_camera() -> CameraManager:
    """Lấy singleton camera manager."""
    global _camera_instance
    if _camera_instance is None:
        _camera_instance = CameraManager()
    return _camera_instance


def init_camera() -> CameraManager:
    """Khởi tạo và trả về camera manager."""
    cam = get_camera()
    if not cam.available:
        cam.init()
    return cam
