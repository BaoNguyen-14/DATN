import { useMemo, useEffect, useState } from 'react';
import { useParkingContext } from '../hooks/useParkingState';
import ParkingSlotComponent from '../components/ParkingSlot';

export default function ParkingMap() {
  const { state, wsUrl } = useParkingContext();
  const { slots } = state;

  const webcamStreamUrl = useMemo(() => {
    try {
      const url = new URL(wsUrl.replace('ws://', 'http://').replace('wss://', 'https://'));
      return `${url.protocol}//${url.hostname}:8080/parking`;
    } catch {
      return 'http://raspberrypi.local:8080/parking';
    }
  }, [wsUrl]);

  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const freeCount = slots.filter((s) => s.status === 'free').length;
  const occupiedCount = slots.filter((s) => s.status === 'occupied').length;
  const occupancyRate = slots.length > 0 ? Math.round((occupiedCount / slots.length) * 100) : 0;

  return (
    <main className="p-4 md:p-6 flex flex-col gap-4 max-w-[1600px] mx-auto w-full h-screen overflow-hidden">
      {/* Page Header */}
      <section className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 flex-shrink-0">
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
      </section>

      {/* Main Content */}
      <section className="flex flex-col gap-4 flex-1 min-h-0">
        {/* Webcam Feed — Top */}
        <div className="bg-surface-container-lowest rounded-2xl shadow-sm overflow-hidden flex flex-col flex-1 min-h-0">
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

          {/* ── Webcam Overlay ── */}
          <div className="relative flex-1 bg-slate-900 min-h-0">
            <img
              src={webcamStreamUrl}
              alt="Webcam quét vùng bãi đậu xe"
              className="w-full h-full object-contain"
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


            </div>
          </div>
        </div>

        {/* Parking Slots Grid — Bottom */}
        <div className="bg-surface-container-lowest rounded-2xl shadow-sm p-4 flex-shrink-0">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">grid_view</span>
              <h3 className="text-sm font-bold font-headline uppercase tracking-tight">Sơ đồ vị trí</h3>
            </div>
            <span className="text-[10px] font-bold text-slate-400">{freeCount}/{slots.length} trống</span>
          </div>

          {/* Parking Grid 1×8 (Horizontal) */}
          <div className="grid grid-cols-4 lg:grid-cols-8 gap-3 mb-2">
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
      </section>
    </main>
  );
}
