import { useParkingContext } from '../hooks/useParkingState';
import React, { useMemo, useState } from 'react';
import GateControl from '../components/GateControl';
import ImageModal from '../components/ImageModal';
import type { GateType, PlateResult, GateState, LCDContent, BuzzerFeedback } from '../types/parking';


export default function Dashboard() {
  const { state, wsUrl } = useParkingContext();
  const { entryGate, exitGate, entryLCD, exitLCD, entryPlate, exitPlate, stats, lastBuzzer, sessions } = state;

  const entryCameraUrl = useMemo(() => {
    try {
      const url = new URL(wsUrl.replace('ws://', 'http://').replace('wss://', 'https://'));
      return `${url.protocol}//${url.hostname}:8080/entry`;
    } catch {
      return 'http://raspberrypi.local:8080/entry';
    }
  }, [wsUrl]);

  const exitCameraUrl = useMemo(() => {
    try {
      const url = new URL(wsUrl.replace('ws://', 'http://').replace('wss://', 'https://'));
      return `${url.protocol}//${url.hostname}:8080/exit`;
    } catch {
      return 'http://raspberrypi.local:8080/exit';
    }
  }, [wsUrl]);

  const baseHttpUrl = useMemo(() => {
    try {
      const url = new URL(wsUrl.replace('ws://', 'http://').replace('wss://', 'https://'));
      return `${url.protocol}//${url.hostname}:8080`;
    } catch {
      return 'http://raspberrypi.local:8080';
    }
  }, [wsUrl]);

  const [selectedImage, setSelectedImage] = useState<{ url: string, title: string } | null>(null);

  return (
    <>
    <main className="p-4 md:p-6 flex flex-col gap-4 max-w-[1600px] mx-auto w-full h-screen overflow-hidden">
      {/* ===== Stats Row ===== */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-shrink-0">
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
          label="Chi phí xe vừa ra"
          value={stats.lastCost !== null ? stats.lastCost.toLocaleString() : '--'}
          suffix={stats.lastCost !== null ? 'VNĐ' : ''}
          icon="payments"
          color="tertiary-container"
        />
      </section>

      {/* ===== Dual Gate Layout ===== */}
      <section className="grid grid-cols-1 xl:grid-cols-2 gap-4 flex-shrink-0">
        <GatePanel
          gateType="entry"
          gate={entryGate}
          plate={entryPlate}
          buzzer={lastBuzzer?.gateType === 'entry' ? lastBuzzer : null}
          streamUrl={entryCameraUrl}
          baseUrl={baseHttpUrl}
          onPreview={(url, title) => setSelectedImage({ url, title })}
        />
        <GatePanel
          gateType="exit"
          gate={exitGate}
          plate={exitPlate}
          buzzer={lastBuzzer?.gateType === 'exit' ? lastBuzzer : null}
          streamUrl={exitCameraUrl}
          baseUrl={baseHttpUrl}
          onPreview={(url, title) => setSelectedImage({ url, title })}
        />
      </section>

      {/* ===== Recent Activity ===== */}
      <section className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden flex flex-col min-h-0 flex-1">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-lg">history</span>
            <h3 className="text-sm font-bold font-headline uppercase tracking-wide">Lượt xe gần đây</h3>
          </div>
          <span className="text-[10px] font-bold text-slate-400 uppercase">{sessions.length} bản ghi</span>
        </div>
        <div className="divide-y divide-slate-50 overflow-y-auto flex-1">
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
                  <div className="cursor-pointer group/item"
                    onClick={() => {
                      const isExit = !!session.timeOut;
                      const imageUrl = isExit 
                        ? (session.fullImageOut ? `${baseHttpUrl}${session.fullImageOut}` : (session.plateImageOut?.startsWith('http') ? session.plateImageOut : `${baseHttpUrl}${session.plateImageOut}`))
                        : (session.fullImageIn ? `${baseHttpUrl}${session.fullImageIn}` : (session.plateImageIn.startsWith('http') ? session.plateImageIn : `${baseHttpUrl}${session.plateImageIn}`));
                      
                      setSelectedImage({
                        url: imageUrl || '',
                        title: `Ảnh ${isExit ? 'ra' : 'vào'} - Biển số: ${isExit ? session.plateOut : session.plateIn}`
                      });
                    }}
                  >
                    <div className="text-sm font-bold text-on-surface group-hover/item:text-primary transition-colors flex items-center gap-2">
                      {session.plateIn}
                      <span className="material-symbols-outlined text-[14px] opacity-0 group-hover/item:opacity-100 transition-opacity">zoom_in</span>
                    </div>
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
    {selectedImage && (
      <ImageModal 
        url={selectedImage.url} 
        title={selectedImage.title} 
        onClose={() => setSelectedImage(null)} 
      />
    )}
    </>
  );
}

// ===== Gate Panel Component =====
interface GatePanelProps {
  gateType: GateType;
  gate: GateState;
  plate: PlateResult | null;
  buzzer: BuzzerFeedback | null;
  streamUrl: string;
  baseUrl: string;
  onPreview: (url: string, title: string) => void;
}

function GatePanel({ gateType, gate, plate, buzzer, streamUrl, baseUrl, onPreview }: GatePanelProps) {
  const isEntry = gateType === 'entry';

  return (
    <div className={`bg-surface-container-lowest rounded-2xl shadow-sm overflow-hidden border flex flex-col h-full ${
      isEntry ? 'border-primary/10' : 'border-secondary/10'
    }`}>
      {/* Gate Header */}
      <div className={`px-3 py-2 flex items-center justify-between flex-shrink-0 ${
        isEntry
          ? 'bg-gradient-to-r from-primary/5 to-transparent'
          : 'bg-gradient-to-r from-secondary/5 to-transparent'
      }`}>
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            isEntry ? 'bg-primary text-on-primary' : 'bg-secondary text-on-secondary'
          }`}>
            <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>
              {isEntry ? 'login' : 'logout'}
            </span>
          </div>
          <div>
            <h2 className="text-base font-bold font-headline tracking-tight uppercase">
              {isEntry ? 'Cổng Vào' : 'Cổng Ra'}
            </h2>
          </div>
        </div>

        {/* Buzzer Indicator */}
        {buzzer && (
          <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-bold uppercase ${
            buzzer.type === 'success'
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-red-100 text-red-700'
          }`}>
            <span className="material-symbols-outlined text-[10px]">
              {buzzer.type === 'success' ? 'volume_up' : 'warning'}
            </span>
            {buzzer.type === 'success' ? '2× TÍT' : '3× TÍT'}
          </div>
        )}
      </div>

      <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">
        {/* Left Col: Camera Feed */}
        <div className="flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-2 flex-shrink-0">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-error rounded-full animate-pulse" />
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                Live Feed
              </span>
            </div>
            <span className="px-2 py-0.5 bg-surface-container-high rounded-full text-[10px] font-bold text-slate-500">
              MJPEG
            </span>
          </div>

          <div className="relative flex-1 min-h-[240px] xl:min-h-[300px] bg-slate-900 rounded-xl overflow-hidden shadow-inner">
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
                  fb.innerHTML = '<span class="material-symbols-outlined text-4xl mb-2">videocam_off</span><span class="text-xs font-medium text-center px-2">Không thể kết nối camera</span>';
                  parent.appendChild(fb);
                }
              }}
            />
            {/* Overlay */}
            <div className="absolute top-2 left-2 bg-black/50 backdrop-blur px-2 py-1 rounded text-[10px] text-white font-mono">
              {new Date().toLocaleString('vi-VN')}
            </div>
            <div className="absolute top-2 right-2 bg-black/50 backdrop-blur px-2 py-1 rounded text-[10px] text-white font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
              REC
            </div>
          </div>
        </div>

        {/* Right Col: Plate & Controls */}
        <div className="flex flex-col gap-3 min-h-0 justify-between">
          {/* Plate Recognition Result */}
          <div className="bg-surface-container-low rounded-xl p-3 flex flex-col min-h-[90px] justify-center">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest font-label mb-2">
              Nhận diện biển số
            </div>

            {plate ? (
              <div className="flex gap-3 items-center">
                {/* Plate Image */}
                <div className="w-24 flex-shrink-0 aspect-[3/1] bg-slate-200 rounded-md overflow-hidden border border-primary-fixed-dim cursor-pointer hover:ring-2 hover:ring-primary transition-all group"
                  onClick={() => {
                    const fullUrl = plate.fullImageUrl ? (plate.fullImageUrl.startsWith('http') ? plate.fullImageUrl : `${baseUrl}${plate.fullImageUrl}`) : (plate.imageUrl.startsWith('http') ? plate.imageUrl : `${baseUrl}${plate.imageUrl}`);
                    onPreview(fullUrl, `Ảnh ${isEntry ? 'vào' : 'ra'} - Biển số: ${plate.plateText}`);
                  }}
                >
                  <img
                    src={plate.imageUrl.startsWith('http') ? plate.imageUrl : `${baseUrl}${plate.imageUrl}`}
                    alt="Ảnh biển số xe"
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform"
                  />
                </div>
                {/* Plate Data */}
                <div className="flex-1">
                  <div className="text-xl font-black font-headline text-primary tracking-tighter leading-none mb-1">
                    {plate.plateText}
                  </div>
                  <div className="text-[10px] text-slate-400 leading-tight">
                    {plate.confidence}%
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-slate-400 py-1">
                <span className="material-symbols-outlined text-base">image_search</span>
                <span className="text-[11px]">Chờ quẹt thẻ...</span>
              </div>
            )}
          </div>

          {/* Gate Controls */}
          <GateControl
            gate={gate}
            gateType={gateType}
            plateRecognized={plate !== null}
            className="flex-1 flex flex-col justify-end"
          />
        </div>
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
    <div className="bg-surface-container-lowest px-4 py-3 rounded-xl shadow-sm border-l-4" style={{ borderColor: `var(--tw-${color}, inherit)` }}
      // fallback via className
    >
      <div className={`bg-surface-container-lowest p-0 rounded-xl`}>
        <div className="flex justify-between items-center mb-1">
          <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant font-label">{label}</span>
          <span className={`material-symbols-outlined text-${color} text-sm`}>{icon}</span>
        </div>
        <div className="flex items-baseline gap-2">
          <div className={`text-2xl font-extrabold font-headline text-${color} tracking-tight`}>{value}</div>
          {suffix && <div className="text-xs font-bold text-on-surface-variant">{suffix}</div>}
        </div>
        {progress !== undefined && (
          <div className="mt-2 w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div className={`h-full bg-${color} rounded-full transition-all duration-700`} style={{ width: `${progress}%` }} />
          </div>
        )}
      </div>
    </div>
  );
}