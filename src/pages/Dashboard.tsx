import { useParkingContext } from '../hooks/useParkingState';
import { useMemo } from 'react';
import LCDDisplay from '../components/LCDDisplay';
import GateControl from '../components/GateControl';
import type { GateType, PlateResult, GateState, LCDContent, BuzzerFeedback } from '../types/parking';

function getCameraUrl(key: string, fallback: string): string {
  try {
    const stored = localStorage.getItem(key);
    if (stored) return JSON.parse(stored);
  } catch { /* ignore */ }
  return fallback;
}

export default function Dashboard() {
  const { state } = useParkingContext();
  const { entryGate, exitGate, entryLCD, exitLCD, entryPlate, exitPlate, stats, lastBuzzer, sessions } = state;

  const entryCameraUrl = useMemo(() => getCameraUrl('parking_camera_entry', 'http://raspberrypi.local:8080/entry'), []);
  const exitCameraUrl = useMemo(() => getCameraUrl('parking_camera_exit', 'http://raspberrypi.local:8080/exit'), []);

  return (
    <main className="p-4 md:p-8 flex flex-col gap-6 max-w-[1600px] mx-auto w-full flex-1">
      {/* ===== Stats Row ===== */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Tổng xe vào"
          value={stats.totalIn.toLocaleString()}
          icon="login"
          color="primary"
        />
        <StatCard
          label="Tổng xe ra"
          value={stats.totalOut.toLocaleString()}
          icon="logout"
          color="on-tertiary-fixed-variant"
        />
        <StatCard
          label="Chỗ trống"
          value={`${stats.availableSlots}`}
          suffix={`/ ${stats.totalSlots}`}
          icon="local_parking"
          color="secondary"
          progress={(1 - stats.availableSlots / stats.totalSlots) * 100}
        />
        <StatCard
          label="Chi phí xe vừa ra"
          value={stats.lastCost !== null ? stats.lastCost.toLocaleString() : '--'}
          suffix={stats.lastCost !== null ? 'VNĐ' : ''}
          icon="payments"
          color="tertiary-container"
        />
      </section>

      {/* ===== Dual Gate Layout ===== */}
      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <GatePanel
          gateType="entry"
          gate={entryGate}
          lcd={entryLCD}
          plate={entryPlate}
          buzzer={lastBuzzer?.gateType === 'entry' ? lastBuzzer : null}
          streamUrl={entryCameraUrl}
        />
        <GatePanel
          gateType="exit"
          gate={exitGate}
          lcd={exitLCD}
          plate={exitPlate}
          buzzer={lastBuzzer?.gateType === 'exit' ? lastBuzzer : null}
          streamUrl={exitCameraUrl}
        />
      </section>

      {/* ===== Recent Activity ===== */}
      <section className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-lg">history</span>
            <h3 className="text-sm font-bold font-headline uppercase tracking-wide">Lượt xe gần đây</h3>
          </div>
          <span className="text-[10px] font-bold text-slate-400 uppercase">{sessions.length} bản ghi</span>
        </div>
        <div className="divide-y divide-slate-50">
          {sessions.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-sm">
              <span className="material-symbols-outlined text-3xl mb-2 block">inbox</span>
              Chưa có dữ liệu xe ra vào
            </div>
          ) : (
            sessions.slice(0, 6).map((session) => (
              <div key={session.id} className="flex items-center justify-between p-4 hover:bg-slate-50/50 transition-colors">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    session.timeOut ? 'bg-red-50 text-red-500' : 'bg-emerald-50 text-emerald-500'
                  }`}>
                    <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
                      {session.timeOut ? 'logout' : 'login'}
                    </span>
                  </div>
                  <div>
                    <div className="text-sm font-bold text-on-surface">{session.plateIn}</div>
                    <div className="text-[10px] text-slate-400">
                      {session.cardUID} · {new Date(session.timeIn).toLocaleTimeString('vi-VN')}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {session.durationMinutes !== null && (
                    <span className="text-xs text-slate-500 font-medium">{session.durationMinutes} phút</span>
                  )}
                  {session.cost !== null ? (
                    <span className="text-sm font-bold text-primary">{session.cost.toLocaleString()} VNĐ</span>
                  ) : (
                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                      session.timeOut === null
                        ? 'bg-secondary-container text-on-secondary-container'
                        : session.matched
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-red-100 text-red-700'
                    }`}>
                      {session.timeOut === null ? 'Đang đậu' : session.matched ? 'Khớp' : 'Lỗi'}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </main>
  );
}

// ===== Gate Panel Component =====
interface GatePanelProps {
  gateType: GateType;
  gate: GateState;
  lcd: LCDContent;
  plate: PlateResult | null;
  buzzer: BuzzerFeedback | null;
  streamUrl: string;
}

function GatePanel({ gateType, gate, lcd, plate, buzzer, streamUrl }: GatePanelProps) {
  const isEntry = gateType === 'entry';

  return (
    <div className={`bg-surface-container-lowest rounded-2xl shadow-sm overflow-hidden border ${
      isEntry ? 'border-primary/10' : 'border-secondary/10'
    }`}>
      {/* Gate Header */}
      <div className={`px-6 py-4 flex items-center justify-between ${
        isEntry
          ? 'bg-gradient-to-r from-primary/5 to-transparent'
          : 'bg-gradient-to-r from-secondary/5 to-transparent'
      }`}>
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
            isEntry ? 'bg-primary text-on-primary' : 'bg-secondary text-on-secondary'
          }`}>
            <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
              {isEntry ? 'login' : 'logout'}
            </span>
          </div>
          <div>
            <h2 className="text-lg font-bold font-headline tracking-tight uppercase">
              {isEntry ? 'Cổng Vào' : 'Cổng Ra'}
            </h2>
            <span className="text-[10px] text-slate-400 font-medium">
              {isEntry ? 'RC522 SPI0-CE0 · LCD 0x27 · Servo GPIO12' : 'RC522 SPI0-CE1 · LCD 0x20 · Servo GPIO13'}
            </span>
          </div>
        </div>

        {/* Buzzer Indicator */}
        {buzzer && (
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-bold uppercase ${
            buzzer.type === 'success'
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-red-100 text-red-700'
          }`}>
            <span className="material-symbols-outlined text-xs">
              {buzzer.type === 'success' ? 'volume_up' : 'warning'}
            </span>
            {buzzer.type === 'success' ? '2× TÍT' : '3× TÍT'}
          </div>
        )}
      </div>

      <div className="p-5 space-y-4">
        {/* Camera Feed (MJPEG) */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-error rounded-full animate-pulse" />
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                PiCamera — Live Feed
              </span>
            </div>
            <span className="px-2 py-0.5 bg-surface-container-high rounded-full text-[10px] font-bold text-slate-500">
              MJPEG
            </span>
          </div>

          <div className="relative aspect-video bg-slate-900 rounded-xl overflow-hidden shadow-lg">
            <img
              src={streamUrl}
              alt={`${isEntry ? 'Entry' : 'Exit'} gate camera feed`}
              className="w-full h-full object-cover"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
                const parent = target.parentElement;
                if (parent && !parent.querySelector('.camera-fallback')) {
                  const fb = document.createElement('div');
                  fb.className = 'camera-fallback absolute inset-0 flex flex-col items-center justify-center text-slate-500';
                  fb.innerHTML = '<span class="material-symbols-outlined text-4xl mb-2">videocam_off</span><span class="text-xs font-medium">Không thể kết nối camera</span>';
                  parent.appendChild(fb);
                }
              }}
            />
            {/* Overlay */}
            <div className="absolute top-3 left-3 bg-black/50 backdrop-blur px-2 py-1 rounded text-[10px] text-white font-mono">
              {new Date().toLocaleString('vi-VN')}
            </div>
            <div className="absolute top-3 right-3 bg-black/50 backdrop-blur px-2 py-1 rounded text-[10px] text-white font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
              REC
            </div>
          </div>
        </div>

        {/* Plate Recognition Result */}
        <div className="bg-surface-container-low rounded-xl p-4 space-y-3">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest font-label">
            Kết quả nhận diện biển số
          </div>

          {plate ? (
            <div className="flex gap-4 items-start">
              {/* Plate Image */}
              <div className="w-40 flex-shrink-0 aspect-[3/1] bg-slate-200 rounded-lg overflow-hidden border-2 border-primary-fixed-dim">
                <img
                  src={plate.imageUrl}
                  alt="Ảnh biển số xe"
                  className="w-full h-full object-cover"
                />
              </div>
              {/* Plate Data */}
              <div className="flex-1 space-y-1.5">
                <div className="text-2xl font-black font-headline text-primary tracking-tighter">
                  {plate.plateText}
                </div>
                <div className="text-[10px] text-slate-400">
                  {new Date(plate.timestamp).toLocaleString('vi-VN')} · Độ tin cậy: {plate.confidence}%
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-slate-400 py-2">
              <span className="material-symbols-outlined text-lg">image_search</span>
              <span className="text-xs">Chờ quẹt thẻ để chụp biển số...</span>
            </div>
          )}
        </div>

        {/* LCD Display */}
        <LCDDisplay content={lcd} title={`LCD ${isEntry ? '0x27' : '0x20'} — ${isEntry ? 'Cổng Vào' : 'Cổng Ra'}`} />

        {/* Gate Controls */}
        <GateControl
          gate={gate}
          gateType={gateType}
          plateRecognized={plate !== null}
        />
      </div>
    </div>
  );
}

// ===== Stat Card Component =====
interface StatCardProps {
  label: string;
  value: string;
  suffix?: string;
  icon: string;
  color: string;
  progress?: number;
}

function StatCard({ label, value, suffix, icon, color, progress }: StatCardProps) {
  return (
    <div className="bg-surface-container-lowest p-5 rounded-xl shadow-sm border-l-4" style={{ borderColor: `var(--tw-${color}, inherit)` }}
      // fallback via className
    >
      <div className={`bg-surface-container-lowest p-0 rounded-xl`}>
        <div className="flex justify-between items-start mb-1">
          <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant font-label">{label}</span>
          <span className={`material-symbols-outlined text-${color}`}>{icon}</span>
        </div>
        <div className="flex items-baseline gap-2">
          <div className={`text-3xl font-extrabold font-headline text-${color} tracking-tight`}>{value}</div>
          {suffix && <div className="text-sm font-bold text-on-surface-variant">{suffix}</div>}
        </div>
        {progress !== undefined && (
          <div className="mt-3 w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div className={`h-full bg-${color} rounded-full transition-all duration-700`} style={{ width: `${progress}%` }} />
          </div>
        )}
      </div>
    </div>
  );
}