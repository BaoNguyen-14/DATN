import { useParkingContext } from '../hooks/useParkingState';

export default function History() {
  const { state } = useParkingContext();
  const { sessions } = state;

  const todayCount = sessions.length;
  const totalRevenue = sessions.reduce((sum, s) => sum + (s.cost || 0), 0);

  return (
    <main className="flex-1 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Page Header & Stats */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
          <div className="lg:col-span-2 flex flex-col justify-end">
            <h2 className="text-4xl font-extrabold tracking-tight text-primary mb-2">Truy xuất dữ liệu</h2>
            <p className="text-on-surface-variant font-body">Danh sách chi tiết các lượt xe ra vào được ghi nhận bởi hệ thống cảm biến và RFID.</p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border-l-4 border-secondary flex flex-col justify-between">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Hôm nay</span>
            <div className="flex items-end justify-between">
              <span className="text-3xl font-headline font-extrabold text-on-surface">{todayCount.toLocaleString()}</span>
            </div>
            <span className="text-xs text-slate-500 font-medium mt-1">Lượt xe ra vào</span>
          </div>

          <div className="bg-primary p-6 rounded-xl shadow-sm flex flex-col justify-between text-white">
            <span className="text-[10px] font-bold uppercase tracking-widest text-blue-300/60">Doanh thu ngày</span>
            <div className="flex items-end justify-between">
              <span className="text-2xl font-headline font-extrabold">{totalRevenue.toLocaleString()}</span>
              <span className="text-blue-300 text-xs font-bold mb-1">VNĐ</span>
            </div>
            <div className="h-1 w-full bg-blue-900 rounded-full mt-2 overflow-hidden">
              <div className="h-full bg-blue-400 w-3/4" />
            </div>
          </div>
        </div>

        {/* Table Section */}
        <div className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden border border-outline-variant/10">
          {/* Filter Bar */}
          <div className="p-6 border-b border-surface-container flex flex-wrap items-center justify-between gap-4">
            <div className="flex gap-2">
              <button className="px-4 py-2 rounded-full bg-primary text-white text-xs font-bold flex items-center gap-2 active:scale-95 transition-transform">
                <span className="material-symbols-outlined text-sm">filter_list</span>
                Lọc kết quả
              </button>
              <button className="px-4 py-2 rounded-full bg-surface-container-high text-on-surface text-xs font-bold flex items-center gap-2 hover:bg-slate-200 transition-colors">
                <span className="material-symbols-outlined text-sm">download</span>
                Xuất Excel
              </button>
            </div>
            <div className="flex items-center gap-4 text-xs font-medium text-slate-500">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-secondary" /> Xe vào</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-error" /> Xe ra</span>
            </div>
          </div>

          {/* Table Content */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/50">
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-surface-container">Thời gian</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-surface-container">UID thẻ</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-surface-container">Trạng thái</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-surface-container">Biển số xe</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-surface-container">Khớp BSX</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-surface-container">Thời gian đậu</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-surface-container">Chi phí (VNĐ)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-container">
                {sessions.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-slate-400">
                      <span className="material-symbols-outlined text-3xl mb-2 block">inbox</span>
                      <span className="text-sm">Chưa có dữ liệu. Kết nối Pi để nhận dữ liệu thời gian thực.</span>
                    </td>
                  </tr>
                ) : (
                  sessions.map((session) => (
                    <tr key={session.id} className="hover:bg-slate-50/80 transition-colors group">
                      <td className="px-6 py-5">
                        <div className="flex flex-col">
                          <span className="text-sm font-semibold text-on-surface">
                            {new Date(session.timeIn).toLocaleTimeString('vi-VN')}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {new Date(session.timeIn).toLocaleDateString('vi-VN')}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <code className="text-xs font-mono bg-surface-container px-2 py-1 rounded text-primary">
                          {session.cardUID}
                        </code>
                      </td>
                      <td className="px-6 py-5">
                        {session.timeOut ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-tight bg-error-container text-on-error-container">
                            <span className="w-1 h-1 rounded-full bg-error mr-1.5" /> Ra
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-tight bg-secondary-container text-on-secondary-container">
                            <span className="w-1 h-1 rounded-full bg-secondary mr-1.5" /> Vào
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-3">
                          {session.plateImageIn && (
                            <div className="w-8 h-8 rounded-lg overflow-hidden flex-shrink-0 bg-slate-200">
                              <img className="w-full h-full object-cover" alt="Ảnh biển số" src={session.plateImageIn} />
                            </div>
                          )}
                          <span className="text-sm font-bold text-on-surface">{session.plateIn}</span>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        {session.matched === null ? (
                          <span className="text-xs text-slate-400">--</span>
                        ) : session.matched ? (
                          <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-600">
                            <span className="material-symbols-outlined text-xs">check_circle</span> Khớp
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-bold text-red-600">
                            <span className="material-symbols-outlined text-xs">cancel</span> Lỗi
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-5 font-body text-sm text-on-surface-variant">
                        {session.durationMinutes !== null ? `${session.durationMinutes} phút` : '--'}
                      </td>
                      <td className="px-6 py-5 font-body text-sm font-bold text-on-surface">
                        {session.cost !== null ? session.cost.toLocaleString() : '--'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="p-6 bg-slate-50/50 flex items-center justify-between">
            <span className="text-xs text-slate-500">Hiển thị {Math.min(sessions.length, 50)} của {sessions.length} bản ghi</span>
            <div className="flex gap-2">
              <button className="w-8 h-8 flex items-center justify-center rounded-lg border border-slate-200 text-slate-400 hover:bg-white transition-colors">
                <span className="material-symbols-outlined text-sm">chevron_left</span>
              </button>
              <button className="w-8 h-8 flex items-center justify-center rounded-lg bg-primary text-white text-xs font-bold">1</button>
              <button className="w-8 h-8 flex items-center justify-center rounded-lg border border-slate-200 text-slate-400 hover:bg-white transition-colors">
                <span className="material-symbols-outlined text-sm">chevron_right</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}