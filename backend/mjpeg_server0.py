"""
MJPEG HTTP Streaming Server.

Cung cấp 3 endpoints:
  /entry   - PiCamera stream cổng vào
  /exit    - PiCamera stream cổng ra
  /parking - Webcam stream quét bãi đậu

Sử dụng shared CameraManager để tránh xung đột PiCamera2.
Dashboard dùng: <img src="http://192.168.1.9:8080/entry">
"""

from flask import Flask, Response, request, jsonify
import cv2
import json
import os
import time
import logging
from threading import Thread

logger = logging.getLogger('MJPEG')
app = Flask(__name__)

# Shared camera manager (set từ main_server.py)
_camera_manager = None


def set_camera_manager(cam_mgr):
    """Nhận shared CameraManager từ main_server."""
    global _camera_manager
    _camera_manager = cam_mgr
    logger.info("MJPEG: Đã nhận shared CameraManager")


# ===== CORS Middleware =====
@app.after_request
def add_cors_headers(response):
    """Thêm CORS headers để frontend từ domain khác có thể truy cập."""
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


def gen_picam_frames():
    """Generator MJPEG frames từ shared PiCamera."""
    import numpy as np
    while True:
        frame = None
        if _camera_manager is not None and _camera_manager.available:
            frame = _camera_manager.capture_frame()

        if frame is None:
            # Placeholder frame khi camera không khả dụng
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "PiCamera not available",
                       (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)

        # Resize hoặc fix màu nếu bị ngược (BGR vs RGB)
        # Sửa lỗi sai màu: Swap Red và Blue channel do mjpeg/browser hiển thị
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
               + buf.tobytes() + b'\r\n')
        time.sleep(0.066)  # ~15 FPS


from webcam_manager import get_webcam
import numpy as np

def gen_webcam_frames():
    webcam = get_webcam()
    while True:
        frame = webcam.read_frame()
        if frame is None:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "Webcam not available", (120, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
        # Sửa lỗi sai màu cho webcam
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n'
        time.sleep(0.1)


@app.route('/entry')
def entry_stream():
    return Response(gen_picam_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/exit')
def exit_stream():
    return Response(gen_picam_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/parking')
def parking_stream():
    return Response(gen_webcam_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return '''
    <h1>Smart Parking MJPEG Server</h1>
    <p><a href="/entry">Entry Camera</a></p>
    <p><a href="/exit">Exit Camera</a></p>
    <p><a href="/parking">Parking Webcam</a></p>
    <p><a href="/rois">Parking ROIs (JSON)</a></p>
    '''


@app.route('/rois')
def get_rois():
    """Trả về danh sách ROI đã cài đặt từ slot_rois.json."""
    roi_file = os.path.join(os.path.dirname(__file__), 'slot_rois.json')
    try:
        with open(roi_file) as f:
            rois = json.load(f)
    except FileNotFoundError:
        rois = []
    except Exception as e:
        logger.warning(f'Cannot read slot_rois.json: {e}')
        rois = []
    return jsonify({'rois': rois})


def run_server(host='0.0.0.0', port=8080):
    """Chạy HTTP server."""
    logger.info(f"MJPEG server starting on http://{host}:{port}")
    app.run(host=host, port=port, threaded=True)


def start_mjpeg_thread(host='0.0.0.0', port=8080, camera_manager=None):
    """Chạy MJPEG server trong background thread (gọi từ main_server.py)."""
    if camera_manager is not None:
        set_camera_manager(camera_manager)
    thread = Thread(target=run_server, args=(host, port), daemon=True)
    thread.start()
    logger.info(f"MJPEG server thread started on http://{host}:{port}")
    return thread


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Standalone mode: tạo camera manager riêng
    from camera_manager import init_camera
    cam = init_camera()
    set_camera_manager(cam)
    run_server()
