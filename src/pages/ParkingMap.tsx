import { useMemo, useEffect, useRef, useState, useCallback } from 'react';
import { useParkingContext } from '../hooks/useParkingState';
import ParkingSlotComponent from '../components/ParkingSlot';

function getCameraUrl(key: string, fallback: string): string {
  try {
    const stored = localStorage.getItem(key);
    if (stored) return JSON.parse(stored);
  } catch { /* ignore */ }
  return fallback;
}

// ROI type from slot_rois.json: [x, y, w, h]
type RoiTuple = [number, number, number, number];

// Extract base URL from stream URL (e.g. http://host:port)
function getBaseUrl(streamUrl: string): string {
  try {
    const u = new URL(streamUrl);
    return `${u.protocol}//${u.host}`;
  } catch {
    return 'http://raspberrypi.local:8080';
  }
}

export default function ParkingMap() {
  const { state } = useParkingContext();
  const { slots } = state;

  const webcamStreamUrl = useMemo(() => getCameraUrl('parking_camera_parking', 'http://raspberrypi.local:8080/parking'), []);

  // ── ROI overlay state ──────────────────────────────────────
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef    = useRef<HTMLImageElement>(null);
  const [rois, setRois] = useState<RoiTuple[]>([]);
  const [now, setNow]   = useState(() => new Date());

  // Live clock – updates every second
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  // Fetch ROIs from mjpeg_server (port 8080) – same server as the video stream
  const roiApiBase = useMemo(() => getBaseUrl(webcamStreamUrl), [webcamStreamUrl]);

  const fetchRois = useCallback(async () => {
    try {
      const res = await fetch(`${roiApiBase}/rois`, { signal: AbortSignal.timeout(2000) });
      if (res.ok) {
        const data = await res.json();
        setRois(data.rois as RoiTuple[]);
      }
    } catch {
      // silently ignore – backend may not be running
    }
  }, [roiApiBase]);

  useEffect(() => {
    fetchRois();
    // Re-fetch every 10 s in case user updates calibration
    const id = setInterval(fetchRois, 10_000);
    return () => clearInterval(id);
  }, [fetchRois]);

  // Draw ROI boxes onto canvas whenever rois or slots change
  const drawRois = useCallback(() => {
    const canvas = canvasRef.current;
    const img    = imgRef.current;
    if (!canvas || !img) return;

    // Match canvas size to rendered image size
    const { offsetWidth: W, offsetHeight: H } = img;
    if (W === 0 || H === 0) return;
    canvas.width  = W;
    canvas.height = H;

    // Scale factors: stream native is 640×480
    const scaleX = W / 640;
    const scaleY = H / 480;

    const ctx = canvas.getContext('2d')!;
    ctx.clearRect(0, 0, W, H);

    rois.forEach(([x, y, w, h], i) => {
      const slot  = slots[i];
      const color = slot?.status === 'occupied' ? '#ef4444' : '#4ade80';
      const sx = x * scaleX, sy = y * scaleY, sw = w * scaleX, sh = h * scaleY;

      // Glow shadow
      ctx.shadowColor = color;
      ctx.shadowBlur  = 8;

      // Box
      ctx.strokeStyle = color;
      ctx.lineWidth   = 2.5;
      ctx.strokeRect(sx, sy, sw, sh);

      // Label background
      ctx.shadowBlur  = 0;
      ctx.fillStyle   = color;
      ctx.fillRect(sx, sy - 20, 36, 20);

      // Label text
      ctx.fillStyle   = slot?.status === 'occupied' ? '#fff' : '#111';
      ctx.font        = 'bold 11px Inter, sans-serif';
      ctx.fillText(`S${i + 1}`, sx + 6, sy - 6);
    });
  }, [rois, slots]);

  useEffect(() => {
    drawRois();
  }, [drawRois]);

  // Also redraw on window resize
  useEffect(() => {
    const obs = new ResizeObserver(drawRois);
    if (imgRef.current) obs.observe(imgRef.current);
    return () => obs.disconnect();
  }, [drawRois]);

  const freeCount = slots.filter((s) => s.status === 'free').length;
  const occupiedCount = slots.filter((s) => s.status === 'occupied').length;
  const occupancyRate = slots.length > 0 ? Math.round((occupiedCount / slots.length) * 100) : 0;

  return (
    <main className="flex-1 p-4 md:p-8">
      <div className="max-w-[1400px] mx-auto space-y-6">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h2 className="text-3xl font-extrabold tracking-tight text-primary font-headline mb-1">
              Bản đồ bãi đậu xe
            </h2>
            <p className="text-on-surface-variant text-sm font-body">
              Giám sát thời gian thực 8 vị trí đậu xe qua Webcam
            </p>
          </div>

          {/* Quick Stats */}
          <div className="flex gap-3">
            <div className="flex items-center gap-2 px-4 py-2 bg-emerald-50 rounded-xl border border-emerald-200">
              <span className="w-3 h-3 rounded-full bg-emerald-500" />
              <span className="text-sm font-bold text-emerald-700">{freeCount}</span>
              <span className="text-[10px] font-medium text-emerald-600 uppercase">Trống</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-red-50 rounded-xl border border-red-200">
              <span className="w-3 h-3 rounded-full bg-red-500" />
              <span className="text-sm font-bold text-red-700">{occupiedCount}</span>
              <span className="text-[10px] font-medium text-red-600 uppercase">Đã đậu</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-slate-50 rounded-xl border border-slate-200">
              <span className="material-symbols-outlined text-sm text-slate-500">percent</span>
              <span className="text-sm font-bold text-slate-700">{occupancyRate}%</span>
              <span className="text-[10px] font-medium text-slate-500 uppercase">Lấp đầy</span>
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Webcam Feed — Left 2/3 */}
          <div className="lg:col-span-2 space-y-4">
            {/* Webcam Section */}
            <div className="bg-surface-container-lowest rounded-2xl shadow-sm overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-error rounded-full animate-pulse" />
                  <span className="text-xs font-bold font-headline uppercase tracking-tight">
                    Webcam — Quét vùng bãi đậu
                  </span>
                </div>
                <div className="flex gap-2">
                  <span className="px-2 py-0.5 bg-surface-container-high rounded-full text-[10px] font-bold text-slate-500">
                    MJPEG
                  </span>
                  <span className="px-2 py-0.5 bg-surface-container-high rounded-full text-[10px] font-bold text-slate-500">
                    USB CAM
                  </span>
                </div>
              </div>

              {/* ── Webcam + ROI Canvas Overlay ── */}
              <div className="relative aspect-video bg-slate-900">
                <img
                  ref={imgRef}
                  src={webcamStreamUrl}
                  alt="Webcam quét vùng bãi đậu xe"
                  className="w-full h-full object-cover"
                  onLoad={drawRois}
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    const parent = target.parentElement;
                    if (parent && !parent.querySelector('.camera-fallback')) {
                      const fb = document.createElement('div');
                      fb.className = 'camera-fallback absolute inset-0 flex flex-col items-center justify-center text-slate-500 bg-slate-900';
                      fb.innerHTML = '<span class="material-symbols-outlined text-5xl mb-3 text-slate-600">videocam_off</span><span class="text-sm font-medium text-slate-400">Không thể kết nối Webcam</span>';
                      parent.appendChild(fb);
                    }
                  }}
                />

                {/* ROI Canvas – absolute on top of stream */}
                <canvas
                  ref={canvasRef}
                  className="absolute inset-0 w-full h-full pointer-events-none"
                  style={{ mixBlendMode: 'normal' }}
                />

                {/* HUD overlays */}
                <div className="absolute inset-0 pointer-events-none">
                  {/* Top-left: live clock */}
                  <div className="absolute top-3 left-3 bg-black/60 backdrop-blur px-3 py-1.5 rounded-lg flex items-center gap-2">
                    <span className="text-[10px] text-white font-mono">
                      {now.toLocaleString('vi-VN')}
                    </span>
                  </div>

                  {/* Top-right: status badge */}
                  <div className="absolute top-3 right-3 bg-black/60 backdrop-blur px-3 py-1.5 rounded-lg flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
                    <span className="text-[10px] text-white font-bold">ZONE DETECTION ACTIVE</span>
                  </div>

                  {/* ROI count badge */}
                  {rois.length > 0 && (
                    <div className="absolute top-3 left-1/2 -translate-x-1/2 bg-emerald-600/80 backdrop-blur px-3 py-1.5 rounded-lg flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-white text-xs">crop_free</span>
                      <span className="text-[10px] text-white font-bold">{rois.length} ROI loaded</span>
                    </div>
                  )}

                  {/* Bottom: slot status bar */}
                  <div className="absolute bottom-3 left-3 right-3 bg-black/50 backdrop-blur rounded-lg p-2">
                    <div className="grid grid-cols-8 gap-1">
                      {slots.map((slot) => (
                        <div
                          key={slot.id}
                          className={`text-center py-1 rounded text-[10px] font-bold transition-colors duration-300 ${
                            slot.status === 'occupied'
                              ? 'bg-red-500/90 text-white'
                              : 'bg-emerald-500/90 text-white'
                          }`}
                        >
                          S{slot.id}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Detection Info */}
            <div className="bg-surface-container-lowest rounded-xl p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <span className="material-symbols-outlined text-primary">psychology</span>
                <h3 className="text-sm font-bold font-headline uppercase tracking-tight">
                  Chiến lược phát hiện chỗ đậu
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <InfoCard
                  icon="crop_free"
                  title="ROI Detection"
                  desc="8 vùng quan tâm (Region of Interest) được định nghĩa cố định. Chỉ phân tích các vùng nhỏ thay vì toàn frame."
                />
                <InfoCard
                  icon="blur_on"
                  title="Background Subtraction"
                  desc="Sử dụng MOG2 để phát hiện thay đổi. Chỉ gửi cập nhật khi trạng thái slot thay đổi (event-driven)."
                />
                <InfoCard
                  icon="palette"
                  title="Color + Edge Analysis"
                  desc="Phân tích % pixel thay đổi so với background trống (calibrate trước). Ngưỡng ~40-60% = có xe."
                />
                <InfoCard
                  icon="schedule"
                  title="Adaptive Polling"
                  desc="Ban đêm: quét 1 lần/10s. Giờ cao điểm: quét 1 lần/2s. Tiết kiệm CPU cho nhận diện biển số."
                />
              </div>
            </div>
          </div>

          {/* Parking Slots Grid — Right 1/3 */}
          <div className="space-y-4">
            <div className="bg-surface-container-lowest rounded-2xl shadow-sm p-5">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">grid_view</span>
                  <h3 className="text-sm font-bold font-headline uppercase tracking-tight">Sơ đồ vị trí</h3>
                </div>
                <span className="text-[10px] font-bold text-slate-400">{freeCount}/{slots.length} trống</span>
              </div>

              {/* Parking Grid 2×4 */}
              <div className="grid grid-cols-2 gap-3 mb-5">
                {slots.map((slot) => (
                  <ParkingSlotComponent key={slot.id} slot={slot} />
                ))}
              </div>

              {/* Legend */}
              <div className="flex items-center justify-center gap-6 pt-4 border-t border-slate-100">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded bg-emerald-500" />
                  <span className="text-[10px] font-medium text-slate-500">Trống</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded bg-red-500" />
                  <span className="text-[10px] font-medium text-slate-500">Đã đậu</span>
                </div>
              </div>
            </div>

            {/* Occupancy Gauge */}
            <div className="bg-surface-container-lowest rounded-2xl shadow-sm p-5">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">
                Tỷ lệ lấp đầy
              </div>
              <div className="flex items-center justify-center">
                <div className="relative w-36 h-36">
                  <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
                    <circle
                      cx="60" cy="60" r="52"
                      fill="none" stroke="#e2e8f0" strokeWidth="10"
                    />
                    <circle
                      cx="60" cy="60" r="52"
                      fill="none"
                      stroke={occupancyRate > 80 ? '#ef4444' : occupancyRate > 50 ? '#f59e0b' : '#22c55e'}
                      strokeWidth="10"
                      strokeLinecap="round"
                      strokeDasharray={`${(occupancyRate / 100) * 327} 327`}
                      className="transition-all duration-1000"
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-3xl font-extrabold font-headline text-on-surface">{occupancyRate}</span>
                    <span className="text-[10px] font-bold text-slate-400 uppercase">%</span>
                  </div>
                </div>
              </div>
              <div className="text-center mt-3">
                <span className={`text-xs font-bold ${
                  occupancyRate > 80 ? 'text-red-600' : occupancyRate > 50 ? 'text-amber-600' : 'text-emerald-600'
                }`}>
                  {occupancyRate > 80 ? 'Gần đầy!' : occupancyRate > 50 ? 'Vừa phải' : 'Còn nhiều chỗ'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

// ===== Info Card =====
function InfoCard({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="flex gap-3 p-3 bg-surface-container-low rounded-lg">
      <span className="material-symbols-outlined text-secondary text-lg flex-shrink-0 mt-0.5">{icon}</span>
      <div>
        <div className="text-xs font-bold text-on-surface mb-0.5">{title}</div>
        <div className="text-[10px] text-slate-500 leading-relaxed">{desc}</div>
      </div>
    </div>
  );
}
