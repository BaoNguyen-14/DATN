"""
zone_scanner.py – Quét vùng bãi đậu xe (cải tiến theo quetvung3.py).

Kiến trúc 2 thread:
  Thread A (Camera)   → đọc webcam liên tục → đẩy frame vào queue
  Thread B (Detector) → lấy frame → phân tích → cập nhật _state + JPEG

Thuật toán phát hiện (học từ quetvung3.py):
  1. Tiền xử lý: Grayscale → GaussianBlur → CLAHE
  2. MOG2 dùng CHUNG toàn frame (varThreshold=25, history=300)
  3. Canny edge detection trên cùng frame gray
  4. Với mỗi ROI: tính % pixel MOG2 và % pixel Edge
  5. Logic OR: occupied = (mog2_pct > 15%) OR (edge_pct > 3%)
  6. Warm-up 45 frame (~3s) trước khi bắt đầu phán quyết
"""

import cv2
import numpy as np
import time
import queue
import logging
import json
import os
import asyncio
import threading
from typing import List, Tuple, Optional, Callable
from datetime import datetime

logger = logging.getLogger('ZoneScanner')

ROI_FILE = os.path.join(os.path.dirname(__file__), 'slot_rois.json')

# ══════════════════════════════════════════════════════════════
# CẤU HÌNH — học từ quetvung3.py
# ══════════════════════════════════════════════════════════════

CAM_WIDTH        = 640
CAM_HEIGHT       = 480
CAM_FPS          = 15

# Ngưỡng phát hiện (OR logic — dễ nhận hơn AND)
MOG2_PCT_THRESH  = 0.15   # 15% pixel tiền cảnh
EDGE_THRESH      = 0.03   # 3%  pixel cạnh

# MOG2 toàn frame
MOG2_HISTORY     = 300
MOG2_VAR_THRESH  = 25
MOG2_DETECT_SHAD = False

# Tiền xử lý
BLUR_KSIZE       = 5
CLAHE_CLIP       = 2.0
MORPH_KSIZE      = 3

# Warm-up trước khi phán quyết
WARMUP_FRAMES    = 45     # ~3s @ 15 fps


# ── Default ROIs (x, y, w, h) — cập nhật từ slot_rois.json ──
DEFAULT_SLOT_ROIS: List[Tuple[int, int, int, int]] = [
    (41,  59, 132, 171),
    (184, 59, 125, 171),
    (320, 59, 117, 171),
    (447, 59, 104, 171),
    (41,  240, 132, 172),
    (184, 240, 125, 172),
    (320, 240, 117, 172),
    (447, 240, 104, 172),
]


def _load_rois() -> List[Tuple[int, int, int, int]]:
    if os.path.exists(ROI_FILE):
        try:
            with open(ROI_FILE) as f:
                data = json.load(f)
            rois = [tuple(r) for r in data]
            logger.info(f"Nạp {len(rois)} vùng từ {ROI_FILE}")
            return rois
        except Exception as e:
            logger.warning(f"Không đọc được {ROI_FILE}: {e}. Dùng DEFAULT.")
    else:
        logger.warning(f"Chưa có {ROI_FILE}. Dùng ROI mặc định.")
    return list(DEFAULT_SLOT_ROIS)


# ══════════════════════════════════════════════════════════════
# Shared detection objects (học từ quetvung3.py: 1 MOG2 chung)
# ══════════════════════════════════════════════════════════════

def _make_mog2():
    return cv2.createBackgroundSubtractorMOG2(
        history=MOG2_HISTORY,
        varThreshold=MOG2_VAR_THRESH,
        detectShadows=MOG2_DETECT_SHAD,
    )

_clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=(8, 8))
_morph_kernel = cv2.getStructuringElement(
    cv2.MORPH_ELLIPSE, (MORPH_KSIZE, MORPH_KSIZE)
)


def _preprocess(frame_bgr: np.ndarray) -> np.ndarray:
    """Gray → Blur → CLAHE (giống quetvung3.py)."""
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (BLUR_KSIZE, BLUR_KSIZE), 0)
    gray = _clahe.apply(gray)
    return gray


# ══════════════════════════════════════════════════════════════
# ZoneScanner class
# ══════════════════════════════════════════════════════════════

class ZoneScanner:
    """
    Quét vùng bãi đậu xe qua webcam USB.

    Kiến trúc 2 thread (Camera + Detector) học theo quetvung3.py.
    Kết quả và JPEG được chia sẻ qua _state + _lock.
    """

    def __init__(
        self,
        slot_rois: Optional[List[Tuple[int, int, int, int]]] = None,
        webcam_index: int = 0,
        on_status_change: Optional[Callable] = None,
    ):
        self._rois: List[Tuple[int, int, int, int]] = (
            list(slot_rois) if slot_rois is not None else _load_rois()
        )
        self._webcam_index  = webcam_index
        self.on_status_change = on_status_change

        # MOG2 dùng chung 1 instance toàn frame (khác cũ: 1 mog2/slot)
        self._mog2 = _make_mog2()
        self._warmup_count = 0

        # Trạng thái hiện tại của các slot (string: 'free' | 'occupied')
        self._slot_statuses: List[str] = ['free'] * len(self._rois)
        self._slot_updated: List[str]  = [datetime.now().isoformat()] * len(self._rois)

        # Shared state (giống quetvung3.py: _state + _lock)
        self._lock  = threading.Lock()
        self._state = {
            'results':  {},    # {slot_id(int): {occupied, pct, edge_pct}}
            'jpeg':     None,  # bytes JPEG đã vẽ overlay
            'fps':      0.0,
            'ts':       '',
            'warming':  True,
        }

        self._frame_q: queue.Queue = queue.Queue(maxsize=1)
        self._running  = False
        self._stop_evt = threading.Event()

        # Async loop reference (để gọi on_status_change từ thread)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ── Public helpers ────────────────────────────────────────

    def get_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._state['jpeg']

    def get_results(self) -> dict:
        with self._lock:
            return dict(self._state['results'])

    def get_all_statuses(self) -> List[dict]:
        """Trả về list dict tương thích với WebSocket handler."""
        with self._lock:
            out = []
            for i, (status, updated) in enumerate(
                zip(self._slot_statuses, self._slot_updated)
            ):
                out.append({
                    'id':          i + 1,
                    'status':      status,
                    'lastUpdated': updated,
                })
        return out

    def get_state(self) -> dict:
        with self._lock:
            return dict(self._state)

    def reload_rois(self):
        """Tải lại ROI từ slot_rois.json (dùng sau khi calibrate lại)."""
        new_rois = _load_rois()
        with self._lock:
            self._rois            = new_rois
            self._slot_statuses   = ['free'] * len(new_rois)
            self._slot_updated    = [datetime.now().isoformat()] * len(new_rois)
            self._mog2            = _make_mog2()
            self._warmup_count    = 0
            self._state['warming'] = True
        logger.info(f"Đã reload {len(new_rois)} ROI")

    # ── Detection core (học từ quetvung3.py._detect) ─────────

    def _detect(self, frame_bgr: np.ndarray) -> Tuple[dict, np.ndarray, bool]:
        """
        Phân tích frame, trả về (results, canvas, is_warming).

        results = {slot_index(int): {occupied, pct, edge_pct}}
        """
        fh, fw = frame_bgr.shape[:2]
        gray   = _preprocess(frame_bgr)

        # learningRate: -1 trong warm-up (học nhanh), 0.003 sau warm-up
        lr = -1 if self._warmup_count < WARMUP_FRAMES else 0.003
        fg_mask = self._mog2.apply(gray, learningRate=lr)

        # Làm sạch mask
        _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        fg_mask    = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN,  _morph_kernel)
        fg_mask    = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, _morph_kernel)

        # Canny edge
        edges = cv2.Canny(gray, threshold1=25, threshold2=70)

        warming = self._warmup_count < WARMUP_FRAMES
        if warming:
            self._warmup_count += 1

        canvas = frame_bgr.copy()

        # Hiển thị warm-up overlay
        if warming:
            pct = int(self._warmup_count / WARMUP_FRAMES * 100)
            overlay = canvas.copy()
            cv2.rectangle(overlay, (0, 0), (fw, fh), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.35, canvas, 0.65, 0, canvas)
            cv2.putText(canvas, f"Khoi dong MOG2... {pct}%",
                        (fw // 2 - 160, fh // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2)

        results = {}
        changes = []

        for i, roi in enumerate(self._rois):
            x, y, w, h = roi
            slot_id = i + 1

            if x + w > fw or y + h > fh or w < 1 or h < 1:
                results[i] = {'occupied': False, 'pct': 0.0, 'edge_pct': 0.0}
                continue

            area     = w * h
            mog2_pct = cv2.countNonZero(fg_mask[y:y+h, x:x+w]) / area
            edge_pct = cv2.countNonZero(edges[y:y+h,   x:x+w]) / area

            # OR logic (học từ quetvung3.py)
            if warming:
                occupied = False
            else:
                occupied = (mog2_pct > MOG2_PCT_THRESH) or (edge_pct > EDGE_THRESH)

            results[i] = {
                'occupied': occupied,
                'pct':      round(mog2_pct * 100, 1),
                'edge_pct': round(edge_pct  * 100, 1),
            }

            # Cập nhật _slot_statuses và ghi nhận thay đổi
            new_status = 'occupied' if occupied else 'free'
            if new_status != self._slot_statuses[i]:
                self._slot_statuses[i]  = new_status
                self._slot_updated[i]   = datetime.now().isoformat()
                changes.append({
                    'id':          slot_id,
                    'status':      new_status,
                    'lastUpdated': self._slot_updated[i],
                })
                logger.info(f"Slot {slot_id}: → {new_status} "
                            f"(M:{mog2_pct*100:.0f}% E:{edge_pct*100:.0f}%)")

            # Vẽ ROI lên canvas (xanh = trống, đỏ = có xe)
            color = (30, 30, 220) if occupied else (34, 197, 94)
            cv2.rectangle(canvas, (x, y), (x+w, y+h), color, 2)
            cv2.putText(canvas, f"S{slot_id}:{'Xe' if occupied else 'OK'}",
                        (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
            cv2.putText(canvas,
                        f"M:{mog2_pct*100:.0f}% E:{edge_pct*100:.0f}%",
                        (x+2, y+h-6), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)

        # Tổng hợp lên canvas
        free  = sum(1 for v in results.values() if not v['occupied'])
        total = len(self._rois)
        cv2.putText(canvas,
                    f"Trong: {free}/{total}  Co xe: {total-free}/{total}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 200, 0), 2)

        # Gọi callback nếu có thay đổi
        if changes and self.on_status_change and not warming:
            all_statuses = self.get_all_statuses()
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.on_status_change(all_statuses), self._loop
                )

        return results, canvas, warming

    # ── Thread A: Camera ─────────────────────────────────────

    def _camera_thread(self):
        from webcam_manager import get_webcam
        webcam = get_webcam()

        if not webcam.available:
            logger.error("Webcam không khả dụng, camera thread dừng.")
            return

        logger.info(f"[Camera] Bắt đầu @ {CAM_FPS} fps")
        frame_interval = 1.0 / CAM_FPS
        next_tick = time.monotonic()

        while not self._stop_evt.is_set():
            frame = webcam.read_frame()
            if frame is None:
                logger.warning("[Camera] Đọc frame thất bại, thử lại...")
                time.sleep(0.1)
                continue

            # Queue size=1: drop frame cũ nếu detector chưa kịp xử lý
            if self._frame_q.full():
                try:
                    self._frame_q.get_nowait()
                except queue.Empty:
                    pass
            try:
                self._frame_q.put_nowait(frame)
            except queue.Full:
                pass

            next_tick += frame_interval
            sleep_t = next_tick - time.monotonic()
            if sleep_t > 0:
                time.sleep(sleep_t)
            else:
                next_tick = time.monotonic()

        logger.info("[Camera] Dừng")

    # ── Thread B: Detector ────────────────────────────────────

    def _detector_thread(self):
        fps_counter = 0
        fps_timer   = time.time()
        fps_value   = 0.0

        logger.info(f"[Detector] Warm-up {WARMUP_FRAMES} frames (~{WARMUP_FRAMES//CAM_FPS}s)...")

        while not self._stop_evt.is_set():
            try:
                frame_bgr = self._frame_q.get(timeout=1.0)
            except queue.Empty:
                continue

            results, canvas, warming = self._detect(frame_bgr)

            _, buf = cv2.imencode('.jpg', canvas, [cv2.IMWRITE_JPEG_QUALITY, 65])
            jpeg_bytes = buf.tobytes()

            fps_counter += 1
            now = time.time()
            if now - fps_timer >= 2.0:
                fps_value   = fps_counter / (now - fps_timer)
                fps_counter = 0
                fps_timer   = now

            with self._lock:
                self._state['results'] = results
                self._state['jpeg']    = jpeg_bytes
                self._state['fps']     = round(fps_value, 1)
                self._state['ts']      = time.strftime('%H:%M:%S')
                self._state['warming'] = warming

        logger.info("[Detector] Dừng")

    # ── Lifecycle ─────────────────────────────────────────────

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Khởi động 2 thread Camera + Detector."""
        if self._running:
            return
        self._running = True
        self._stop_evt.clear()
        self._loop = loop

        t_cam = threading.Thread(target=self._camera_thread,
                                 daemon=True, name='ZS-Camera')
        t_det = threading.Thread(target=self._detector_thread,
                                 daemon=True, name='ZS-Detector')
        t_cam.start()
        t_det.start()
        logger.info("ZoneScanner started (Camera + Detector threads)")

    def stop(self):
        """Dừng scanner."""
        self._running = False
        self._stop_evt.set()
        logger.info("ZoneScanner stopped")

    # ── Legacy async API (tương thích main_server.py cũ) ─────

    async def run_async(self):
        """Giữ tương thích với code cũ gọi await scanner.run_async()."""
        self._loop = asyncio.get_running_loop()
        self.start(loop=self._loop)
        # Giữ task sống cho đến khi bị cancel
        while self._running:
            await asyncio.sleep(1)

    def init_camera(self) -> bool:
        """Tương thích với code cũ."""
        from webcam_manager import get_webcam
        wc = get_webcam()
        return wc.available

    def calibrate(self, num_frames: int = 30):
        """Không cần thiết nữa — MOG2 tự warm-up 45 frames."""
        logger.info("calibrate() không cần thiết, MOG2 tự warm-up 45 frames")
