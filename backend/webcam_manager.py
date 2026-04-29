"""
Webcam Manager - Shared webcam instance.

Tránh xung đột khi mjpeg_server và zone_scanner cùng mở /dev/video0.
Thread-safe với threading.Lock.
"""

import cv2
import numpy as np
import logging
from threading import Lock, Thread
from typing import Optional

logger = logging.getLogger('WebcamManager')

WEBCAM_W, WEBCAM_H = 640, 480   # kích thước output sau khi resize phần mềm
WEBCAM_FPS = 10                  # FPS capture


class WebcamManager:
    """Singleton webcam, thread-safe, dùng chung cho MJPEG + ZoneScanner."""

    def __init__(self, index: int = 0):
        self._index = index
        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = Lock()
        self._available = False
        self._latest_frame: Optional[np.ndarray] = None
        self._thread: Optional[Thread] = None
        self._running = False

    def init(self) -> bool:
        """Mở webcam và bắt đầu capture thread."""
        import os
        # Trên Raspberry Pi, PiCamera2 thường tạo nhiều /dev/video* (0, 1, 2, 3...),
        # nên USB Webcam thường có index từ 1, 2, 4, hoặc 8. Ta sẽ dò tìm.
        indices_to_try = [self._index] if os.name == 'nt' else [0, 1, 2, 4, 5, 8, 10]
        
        for idx in indices_to_try:
            logger.info(f"Đang thử mở Webcam ở index {idx}...")
            if os.name == 'nt':
                self._cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            else:
                self._cap = cv2.VideoCapture(idx)
                
            if self._cap.isOpened():
                # KHÔNG set WIDTH/HEIGHT ở đây để tránh driver crop hình (zoom in).
                # Camera sẽ chạy ở native resolution; frame được resize bằng phần mềm
                # trong _capture_loop → giữ nguyên góc nhìn đầy đủ của webcam.
                self._cap.set(cv2.CAP_PROP_FPS, WEBCAM_FPS)

                # Đọc thử 1 frame để chắc chắn đây là camera thật (không phải luồng data của PiCam)
                ret, frame = self._cap.read()
                if ret and frame is not None:
                    self._index = idx
                    logger.info(f"✅ Đã kết nối Webcam tại index {idx}")
                    break
                else:
                    logger.warning(f"Index {idx} mở được nhưng không đọc được frame. Bỏ qua.")
                    self._cap.release()
                    
        if self._cap is None or not self._cap.isOpened():
            logger.error(f"Không mở được webcam nào cả.")
            return False

        self._available = True
        self._running = True

        # Capture liên tục trong thread riêng để tránh blocking
        self._thread = Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

        logger.info(f"✅ Webcam sẵn sàng ({WEBCAM_W}×{WEBCAM_H}@{WEBCAM_FPS}fps)")
        return True

    def _capture_loop(self):
        """Capture frame liên tục, lưu vào _latest_frame."""
        import time
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                break
            ret, frame = self._cap.read()
            if ret:
                # Resize phần mềm về kích thước chuẩn (không crop, không zoom)
                frame = cv2.resize(frame, (WEBCAM_W, WEBCAM_H),
                                   interpolation=cv2.INTER_LINEAR)
                with self._lock:
                    self._latest_frame = frame
            time.sleep(1 / WEBCAM_FPS)

    @property
    def available(self) -> bool:
        return self._available

    def read_frame(self) -> Optional[np.ndarray]:
        """
        Đọc frame mới nhất (BGR).
        Dùng cho cả MJPEG streaming và ZoneScanner.
        Thread-safe.
        """
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def cleanup(self):
        """Giải phóng webcam."""
        self._running = False
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._available = False
        logger.info("Webcam đã đóng")


# Singleton
_webcam_instance: Optional[WebcamManager] = None


def get_webcam(index: int = 0) -> WebcamManager:
    global _webcam_instance
    if _webcam_instance is None:
        _webcam_instance = WebcamManager(index)
    return _webcam_instance


def init_webcam(index: int = 0) -> WebcamManager:
    cam = get_webcam(index)
    if not cam.available:
        cam.init()
    return cam