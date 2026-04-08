"""
calibrate_zones.py – Công cụ vẽ vùng đậu xe qua trình duyệt web.

Cách dùng:
    python calibrate_zones.py

Sau đó mở trình duyệt:
    http://<IP_RASPBERRY_PI>:5555
    hoặc http://localhost:5555 (nếu chạy trực tiếp trên Pi có màn hình)

Thao tác trên web:
    - Kéo chuột trên ảnh webcam để vẽ hình chữ nhật.
    - Nhấn "Thêm vùng" để lưu vùng vừa vẽ.
    - Nhấn "Xóa cuối" để xóa vùng cuối cùng.
    - Nhấn "Lưu & Xong" để ghi kết quả vào slot_rois.json và tắt server.
"""

import json
import os
import threading
import time
import cv2
import numpy as np
from flask import Flask, Response, request, jsonify
from functools import wraps

ROI_FILE = os.path.join(os.path.dirname(__file__), 'slot_rois.json')

app = Flask(__name__)

# ── CORS helper – allow React dashboard to fetch /rois ────────
def cors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        resp = f(*args, **kwargs)
        if isinstance(resp, Response):
            r = resp
        else:
            r = jsonify(resp) if isinstance(resp, dict) else resp
        r.headers['Access-Control-Allow-Origin']  = '*'
        r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return r
    return wrapper


# Shared state
saved_rois: list = []
_stop_event = threading.Event()

# ── Webcam ────────────────────────────────────────────────────
from webcam_manager import init_webcam
webcam = None


def get_snapshot_jpeg() -> bytes:
    """Lấy 1 frame JPEG từ webcam (có vẽ overlay vùng đã lưu)."""
    frame = webcam.read_frame() if webcam and webcam.available else None
    if frame is None:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, "Webcam not available", (120, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)

    # Vẽ các vùng đã lưu
    for i, (x, y, w, h) in enumerate(saved_rois):
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 220, 80), 2)
        label = f"S{i + 1}"
        cv2.rectangle(frame, (x, y - 22), (x + 40, y), (0, 220, 80), -1)
        cv2.putText(frame, label, (x + 4, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return buf.tobytes()


def gen_mjpeg():
    """MJPEG stream để hiển thị live trong <img>."""
    while not _stop_event.is_set():
        jpg = get_snapshot_jpeg()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')
        time.sleep(0.04)   # ~25 FPS



# ── HTML giao diện ────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Calibrate Zones – Smart Parking</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background:#111; color:#eee; display:flex;
         flex-direction:column; align-items:center; padding:20px; gap:14px; }
  h1 { font-size:1.3rem; color:#4ade80; }
  #hint { font-size:.85rem; color:#aaa; text-align:center; max-width:680px; }
  #canvas-wrap { position:relative; display:inline-block; border:2px solid #4ade80;
                 border-radius:8px; overflow:hidden; cursor:crosshair; }
  #feed { display:block; }
  #overlay { position:absolute; top:0; left:0; pointer-events:none; }
  .btn-row { display:flex; gap:10px; flex-wrap:wrap; justify-content:center; }
  button { padding:9px 20px; border:none; border-radius:6px; font-size:.9rem;
           cursor:pointer; font-weight:600; transition:.15s; }
  #btn-add   { background:#4ade80; color:#111; }
  #btn-add:hover { background:#22c55e; }
  #btn-undo  { background:#f59e0b; color:#111; }
  #btn-undo:hover { background:#d97706; }
  #btn-clear { background:#ef4444; color:#fff; }
  #btn-clear:hover { background:#dc2626; }
  #btn-save  { background:#6366f1; color:#fff; }
  #btn-save:hover { background:#4f46e5; }
  #roi-list  { width:100%; max-width:680px; }
  #roi-list h2 { font-size:.95rem; color:#4ade80; margin-bottom:6px; }
  #roi-table { width:100%; border-collapse:collapse; font-size:.82rem; }
  #roi-table th, #roi-table td { padding:5px 10px; border:1px solid #333; text-align:center; }
  #roi-table th { background:#1f2937; }
  #msg { font-size:.9rem; min-height:1.4em; color:#4ade80; }
</style>
</head>
<body>
<h1>🅿️ Vẽ Vùng Đậu Xe</h1>
<p id="hint">Kéo chuột trên ảnh để vẽ vùng → nhấn <b>Thêm vùng</b> → lặp lại cho từng ô →
nhấn <b>Lưu &amp; Xong</b> khi hoàn tất.</p>

<div id="canvas-wrap">
  <img id="feed" src="/stream" width="640" height="480">
  <canvas id="overlay" width="640" height="480"></canvas>
</div>

<div class="btn-row">
  <button id="btn-add">➕ Thêm vùng</button>
  <button id="btn-undo">↩ Xóa cuối</button>
  <button id="btn-clear">🗑 Xóa tất cả</button>
  <button id="btn-save">💾 Lưu &amp; Xong</button>
</div>
<p id="msg"></p>

<div id="roi-list">
  <h2>Danh sách vùng đã lưu</h2>
  <table id="roi-table">
    <thead><tr><th>Slot</th><th>x</th><th>y</th><th>w</th><th>h</th></tr></thead>
    <tbody id="roi-tbody"></tbody>
  </table>
</div>

<script>
const canvas = document.getElementById('overlay');
const ctx    = canvas.getContext('2d');
const wrap   = document.getElementById('canvas-wrap');

let startX=0, startY=0, endX=0, endY=0, drawing=false;

function getXY(e) {
  const r = canvas.getBoundingClientRect();
  return [Math.round(e.clientX - r.left), Math.round(e.clientY - r.top)];
}
function draw(x,y,w,h, color='#fb923c') {
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.strokeStyle = color;
  ctx.lineWidth   = 2;
  ctx.strokeRect(x,y,w,h);
}

canvas.style.pointerEvents = 'auto';
canvas.addEventListener('mousedown', e=>{
  [startX,startY]=getXY(e); drawing=true;
});
canvas.addEventListener('mousemove', e=>{
  if(!drawing) return;
  [endX,endY]=getXY(e);
  draw(Math.min(startX,endX), Math.min(startY,endY),
       Math.abs(endX-startX), Math.abs(endY-startY));
});
canvas.addEventListener('mouseup', e=>{
  [endX,endY]=getXY(e); drawing=false;
});

function msg(t,ok=true){ document.getElementById('msg').style.color=ok?'#4ade80':'#f87171';
                          document.getElementById('msg').textContent=t; }

function refreshTable(rois){
  const tb=document.getElementById('roi-tbody'); tb.innerHTML='';
  rois.forEach((r,i)=>{
    tb.innerHTML+=`<tr><td>S${i+1}</td><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td></tr>`;
  });
}

document.getElementById('btn-add').onclick = async ()=>{
  const x=Math.min(startX,endX), y=Math.min(startY,endY);
  const w=Math.abs(endX-startX),  h=Math.abs(endY-startY);
  if(w<5||h<5){msg('Hãy kéo chuột để vẽ vùng trước!',false);return;}
  const res = await fetch('/add_roi',{method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({x,y,w,h})});
  const d = await res.json();
  msg(`✅ Đã thêm Slot ${d.rois.length}: (${x},${y},${w},${h})`);
  ctx.clearRect(0,0,canvas.width,canvas.height);
  refreshTable(d.rois);
};

document.getElementById('btn-undo').onclick = async ()=>{
  const res = await fetch('/undo_roi',{method:'POST'});
  const d = await res.json();
  msg(`↩ Đã xóa Slot ${d.removed+1}`); refreshTable(d.rois);
};

document.getElementById('btn-clear').onclick = async ()=>{
  const res = await fetch('/clear_rois',{method:'POST'});
  const d = await res.json();
  msg('🗑 Đã xóa tất cả'); refreshTable(d.rois);
};

document.getElementById('btn-save').onclick = async ()=>{
  const res = await fetch('/save',{method:'POST'});
  const d = await res.json();
  if(d.ok){ msg(`💾 Đã lưu ${d.count} vùng vào slot_rois.json. Server đang tắt...`); }
  else { msg(d.error, false); }
};

// Load existing rois on start
fetch('/rois').then(r=>r.json()).then(d=>refreshTable(d.rois));
</script>
</body>
</html>
"""


# ── API endpoints ─────────────────────────────────────────────
@app.route('/')
def index():
    return HTML


@app.route('/stream')
def stream():
    return Response(gen_mjpeg(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/rois')
@cors
def get_rois():
    return jsonify({'rois': saved_rois})



@app.route('/add_roi', methods=['POST'])
def add_roi():
    d = request.json
    saved_rois.append([d['x'], d['y'], d['w'], d['h']])
    print(f"  ✅ Thêm Slot {len(saved_rois)}: ({d['x']},{d['y']},{d['w']},{d['h']})")
    return jsonify({'rois': saved_rois})


@app.route('/undo_roi', methods=['POST'])
def undo_roi():
    removed = len(saved_rois) - 1
    if saved_rois:
        saved_rois.pop()
    return jsonify({'rois': saved_rois, 'removed': removed})


@app.route('/clear_rois', methods=['POST'])
def clear_rois():
    saved_rois.clear()
    return jsonify({'rois': saved_rois})


@app.route('/save', methods=['POST'])
def save():
    if not saved_rois:
        return jsonify({'ok': False, 'error': 'Chưa có vùng nào! Hãy vẽ ít nhất 1 vùng.'})
    with open(ROI_FILE, 'w') as f:
        json.dump(saved_rois, f, indent=2)
    print(f"\n💾 Đã lưu {len(saved_rois)} vùng vào {ROI_FILE}")
    for i, r in enumerate(saved_rois):
        print(f"   Slot {i+1}: {tuple(r)}")
    # Tắt server sau 1 giây
    threading.Timer(1.0, _stop_event.set).start()
    return jsonify({'ok': True, 'count': len(saved_rois)})


# ── Main ──────────────────────────────────────────────────────
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.WARNING)

    webcam = init_webcam(0)
    if not webcam.available:
        print('[WARNING] Không mở được webcam, sẽ dùng ảnh đen.')

    # Load vùng cũ nếu có
    if os.path.exists(ROI_FILE):
        try:
            with open(ROI_FILE) as f:
                saved_rois.extend(json.load(f))
            print(f'[INFO] Đã nạp {len(saved_rois)} vùng cũ từ {ROI_FILE}')
        except Exception:
            pass

    PORT = 5555
    print(f'\n{"="*50}')
    print(f'  Calibrate Zones – Smart Parking')
    print(f'  Mở trình duyệt: http://localhost:{PORT}')
    print(f'  hoặc từ máy khác: http://<IP_RPI>:{PORT}')
    print(f'{"="*50}\n')

    # Chạy Flask trong thread riêng để có thể dừng sau khi save
    t = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT,
                                                 debug=False, use_reloader=False))
    t.daemon = True
    t.start()

    _stop_event.wait()   # Chờ cho đến khi user nhấn "Lưu & Xong"
    print('\nServer đã tắt. Kết quả đã lưu vào slot_rois.json.')
    if webcam:
        webcam.cleanup()
