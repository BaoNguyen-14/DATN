import { useParkingContext } from '../hooks/useParkingState';
import { useState, useEffect } from 'react';

// Helper to load from localStorage with fallback
function loadSetting<T>(key: string, fallback: T): T {
  try {
    const stored = localStorage.getItem(key);
    if (stored !== null) {
      return JSON.parse(stored) as T;
    }
  } catch {
    // ignore parse errors
  }
  return fallback;
}

function saveSetting(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value));
}

export default function Settings() {
  const { wsUrl, setWsUrl, sendCommand } = useParkingContext();
  const [localWsUrl, setLocalWsUrl] = useState(wsUrl);
  const [costPerMinute, setCostPerMinute] = useState(() => loadSetting('parking_cost_per_minute', 1000));
  const [cameraEntry, setCameraEntry] = useState(() => loadSetting('parking_camera_entry', 'http://raspberrypi.local:8080/entry'));
  const [cameraExit, setCameraExit] = useState(() => loadSetting('parking_camera_exit', 'http://raspberrypi.local:8080/exit'));
  const [cameraParking, setCameraParking] = useState(() => loadSetting('parking_camera_parking', 'http://raspberrypi.local:8080/parking'));
  const [parkingName, setParkingName] = useState(() => loadSetting('parking_name', 'Smart Parking Central'));
  const [parkingAddress, setParkingAddress] = useState(() => loadSetting('parking_address', 'Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội'));
  const [saved, setSaved] = useState(false);

  // Sync localWsUrl when wsUrl changes from outside
  useEffect(() => {
    setLocalWsUrl(wsUrl);
  }, [wsUrl]);

  const handleSave = () => {
    // Save WebSocket URL
    setWsUrl(localWsUrl);

    // Save all settings to localStorage
    saveSetting('parking_cost_per_minute', costPerMinute);
    saveSetting('parking_camera_entry', cameraEntry);
    saveSetting('parking_camera_exit', cameraExit);
    saveSetting('parking_camera_parking', cameraParking);
    saveSetting('parking_name', parkingName);
    saveSetting('parking_address', parkingAddress);

    // Send cost update to backend
    sendCommand({
      type: 'update_settings',
      payload: { costPerMinute },
    });

    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <section className="p-4 md:p-8 max-w-5xl mx-auto w-full flex-1">
      <div className="mb-10">
        <h2 className="text-4xl font-extrabold text-primary tracking-tight mb-2">Cài đặt hệ thống</h2>
        <p className="text-on-surface-variant font-body">Cấu hình các tham số vận hành và kết nối Raspberry Pi.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
        {/* Pricing Configuration */}
        <div className="md:col-span-12 lg:col-span-5">
          <div className="bg-primary-container p-8 rounded-xl shadow-sm relative overflow-hidden">
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-on-primary">
                  <span className="material-symbols-outlined">payments</span>
                </div>
                <h3 className="text-xl font-bold text-white">Cấu hình phí</h3>
              </div>

              <div className="space-y-4">
                <label className="block">
                  <span className="text-blue-100 text-xs font-bold uppercase tracking-wider mb-2 block">Mức phí gửi xe (VNĐ/Phút)</span>
                  <div className="relative">
                    <input
                      className="w-full bg-white/10 border-white/20 text-white text-3xl font-bold py-4 px-5 rounded-lg focus:ring-2 focus:ring-secondary focus:border-transparent placeholder-white/30"
                      placeholder="0"
                      type="number"
                      value={costPerMinute}
                      onChange={(e) => setCostPerMinute(Number(e.target.value))}
                    />
                    <div className="absolute right-5 top-1/2 -translate-y-1/2 text-white/50 font-bold">VNĐ</div>
                  </div>
                </label>
                <p className="text-blue-200 text-xs italic">Lưu ý: Mức phí này sẽ được áp dụng ngay lập tức cho tất cả lượt gửi mới.</p>
              </div>
            </div>

            <div className="absolute -right-10 -bottom-10 w-48 h-48 bg-white/5 rounded-full blur-3xl" />
          </div>
        </div>

        {/* Connection & General Settings */}
        <div className="md:col-span-12 lg:col-span-7 space-y-6">
          {/* WebSocket Configuration */}
          <div className="bg-surface-container-lowest p-8 rounded-xl shadow-sm">
            <h3 className="text-lg font-bold text-primary mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">wifi</span>
              Kết nối Raspberry Pi
            </h3>

            <div className="space-y-5">
              <div>
                <label className="block text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-2">WebSocket URL</label>
                <input
                  className="w-full bg-surface-container-low border-none rounded-lg py-3 px-4 focus:ring-2 focus:ring-primary focus:bg-surface-container-lowest transition-all font-mono text-sm"
                  type="text"
                  value={localWsUrl}
                  onChange={(e) => setLocalWsUrl(e.target.value)}
                  placeholder="ws://raspberrypi.local:8765"
                />
                <p className="text-[10px] text-slate-400 mt-1">URL WebSocket server trên Raspberry Pi</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-2">Camera MJPEG - Cổng Vào</label>
                <input
                  className="w-full bg-surface-container-low border-none rounded-lg py-3 px-4 focus:ring-2 focus:ring-primary focus:bg-surface-container-lowest transition-all font-mono text-sm"
                  type="text"
                  value={cameraEntry}
                  onChange={(e) => setCameraEntry(e.target.value)}
                  placeholder="http://raspberrypi.local:8080/entry"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-2">Camera MJPEG - Cổng Ra</label>
                <input
                  className="w-full bg-surface-container-low border-none rounded-lg py-3 px-4 focus:ring-2 focus:ring-primary focus:bg-surface-container-lowest transition-all font-mono text-sm"
                  type="text"
                  value={cameraExit}
                  onChange={(e) => setCameraExit(e.target.value)}
                  placeholder="http://raspberrypi.local:8080/exit"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-2">Webcam MJPEG - Quét bãi đậu</label>
                <input
                  className="w-full bg-surface-container-low border-none rounded-lg py-3 px-4 focus:ring-2 focus:ring-primary focus:bg-surface-container-lowest transition-all font-mono text-sm"
                  type="text"
                  value={cameraParking}
                  onChange={(e) => setCameraParking(e.target.value)}
                  placeholder="http://raspberrypi.local:8080/parking"
                />
              </div>
            </div>
          </div>

          {/* General Information */}
          <div className="bg-surface-container-lowest p-8 rounded-xl shadow-sm">
            <h3 className="text-lg font-bold text-primary mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">info</span>
              Thông tin bãi xe
            </h3>

            <div className="grid grid-cols-1 gap-6">
              <div>
                <label className="block text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-2">Tên bãi xe</label>
                <input
                  className="w-full bg-surface-container-low border-none rounded-lg py-3 px-4 focus:ring-2 focus:ring-primary focus:bg-surface-container-lowest transition-all"
                  type="text"
                  value={parkingName}
                  onChange={(e) => setParkingName(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-2">Địa chỉ bãi xe</label>
                <textarea
                  className="w-full bg-surface-container-low border-none rounded-lg py-3 px-4 focus:ring-2 focus:ring-primary focus:bg-surface-container-lowest transition-all"
                  rows={2}
                  value={parkingAddress}
                  onChange={(e) => setParkingAddress(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Hardware Pinout Reference */}
          <div className="bg-surface-container-lowest p-8 rounded-xl shadow-sm">
            <h3 className="text-lg font-bold text-primary mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">memory</span>
              Sơ đồ phần cứng (tham khảo)
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50">
                    <th className="px-4 py-2 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Thiết bị</th>
                    <th className="px-4 py-2 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Kết nối</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr><td className="px-4 py-2.5 font-medium">Webcam</td><td className="px-4 py-2.5 font-mono text-xs text-primary">USB</td></tr>
                  <tr><td className="px-4 py-2.5 font-medium">Buzzer</td><td className="px-4 py-2.5 font-mono text-xs text-primary">GPIO 26</td></tr>
                  <tr><td className="px-4 py-2.5 font-medium">Servo cổng VÀO</td><td className="px-4 py-2.5 font-mono text-xs text-primary">GPIO 12 (PWM0)</td></tr>
                  <tr><td className="px-4 py-2.5 font-medium">Servo cổng RA</td><td className="px-4 py-2.5 font-mono text-xs text-primary">GPIO 13 (PWM1)</td></tr>
                  <tr><td className="px-4 py-2.5 font-medium">IR cổng VÀO</td><td className="px-4 py-2.5 font-mono text-xs text-primary">GPIO 23</td></tr>
                  <tr><td className="px-4 py-2.5 font-medium">IR cổng RA</td><td className="px-4 py-2.5 font-mono text-xs text-primary">GPIO 24</td></tr>
                  <tr><td className="px-4 py-2.5 font-medium">RC522 cổng VÀO</td><td className="px-4 py-2.5 font-mono text-xs text-primary">SPI0-CE0 (GPIO8), RST=GPIO17</td></tr>
                  <tr><td className="px-4 py-2.5 font-medium">RC522 cổng RA</td><td className="px-4 py-2.5 font-mono text-xs text-primary">SPI0-CE1 (GPIO7), RST=GPIO27</td></tr>
                  <tr><td className="px-4 py-2.5 font-medium">LCD cổng VÀO</td><td className="px-4 py-2.5 font-mono text-xs text-primary">I2C1 addr=0x27</td></tr>
                  <tr><td className="px-4 py-2.5 font-medium">LCD cổng RA</td><td className="px-4 py-2.5 font-mono text-xs text-primary">I2C1 addr=0x20</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="mt-12 flex justify-end items-center gap-4">
        {saved && (
          <span className="text-secondary font-bold text-sm flex items-center gap-1 animate-pulse">
            <span className="material-symbols-outlined text-sm">check_circle</span>
            Đã lưu thành công!
          </span>
        )}
        <button
          onClick={handleSave}
          className="bg-gradient-to-br from-primary to-primary-container text-on-primary px-10 py-4 rounded-full font-headline font-bold text-lg shadow-xl hover:shadow-primary/20 active:scale-95 transition-all flex items-center gap-3"
        >
          <span className="material-symbols-outlined">save</span>
          Lưu cài đặt
        </button>
      </div>
    </section>
  );
}