export default function History() {
  return (
    <main className="flex-1 p-6 md:p-10">
      <div className="max-w-7xl mx-auto">
        {/* Page Header & Stats Bento Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
          <div className="lg:col-span-2 flex flex-col justify-end">
            <h2 className="text-4xl font-extrabold tracking-tight text-primary mb-2">Truy xuất dữ liệu</h2>
            <p className="text-on-surface-variant font-body">Danh sách chi tiết các lượt xe ra vào được ghi nhận bởi hệ thống cảm biến và RFID.</p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border-l-4 border-secondary flex flex-col justify-between">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Hôm nay</span>
            <div className="flex items-end justify-between">
              <span className="text-3xl font-headline font-extrabold text-on-surface">1,248</span>
              <span className="text-secondary text-xs font-bold flex items-center mb-1">
                <span className="material-symbols-outlined text-sm">trending_up</span> 12%
              </span>
            </div>
            <span className="text-xs text-slate-500 font-medium mt-1">Lượt xe ra vào</span>
          </div>

          <div className="bg-primary p-6 rounded-xl shadow-sm flex flex-col justify-between text-white">
            <span className="text-[10px] font-bold uppercase tracking-widest text-blue-300/60">Doanh thu ngày</span>
            <div className="flex items-end justify-between">
              <span className="text-2xl font-headline font-extrabold">4,520,000</span>
              <span className="text-blue-300 text-xs font-bold mb-1">VNĐ</span>
            </div>
            <div className="h-1 w-full bg-blue-900 rounded-full mt-2 overflow-hidden">
              <div className="h-full bg-blue-400 w-3/4"></div>
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
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-secondary"></span> Xe vào</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-error"></span> Xe ra</span>
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
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-surface-container">Thời gian đậu</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-surface-container">Chi phí (VNĐ)</th>
                  <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-surface-container"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-container">
                {/* Row 1 */}
                <tr className="hover:bg-slate-50/80 transition-colors group">
                  <td className="px-6 py-5">
                    <div className="flex flex-col">
                      <span className="text-sm font-semibold text-on-surface">14:25:30</span>
                      <span className="text-[10px] text-slate-400">22/05/2024</span>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <code className="text-xs font-mono bg-surface-container px-2 py-1 rounded text-primary">A4:B2:99:1C</code>
                  </td>
                  <td className="px-6 py-5">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-tight bg-secondary-container text-on-secondary-container">
                      <span className="w-1 h-1 rounded-full bg-secondary mr-1.5"></span> Vào
                    </span>
                  </td>
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg overflow-hidden flex-shrink-0 bg-slate-200">
                        <img className="w-full h-full object-cover" alt="Close up of a modern blue car front grill" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDJ_P8eYgpJ3yWi7r-Aw7hFHf6eIfNkApsl_diYVB9arAuEiE_lWbu8Im-u-NPZwZmo6WCbweJd-sl6CjIJAMCHfEzQ7yt1Sum0_wpj0K3HINeo0y1VrFiQvCBFgdQlPJxOjmhBzbSU-6cNPqypFqy_NP2vZ7oFRtCrLISGeSDipQja_qmgh2Fh2ub_2iE78stJYk7tfCZ-ErjkMNwXjHopx17CUh-3Kr8VnDmJPGrvDwdS-4qKRE0Tj-YZiz0EkJ9FeFlx2ZhPy_pC" />
                      </div>
                      <span className="text-sm font-bold text-on-surface">51G-123.45</span>
                    </div>
                  </td>
                  <td className="px-6 py-5 font-body text-sm text-on-surface-variant">--</td>
                  <td className="px-6 py-5 font-body text-sm font-bold text-on-surface">--</td>
                  <td className="px-6 py-5 text-right">
                    <button className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-primary">
                      <span className="material-symbols-outlined">visibility</span>
                    </button>
                  </td>
                </tr>

                {/* Row 2 */}
                <tr className="hover:bg-slate-50/80 transition-colors group">
                  <td className="px-6 py-5">
                    <div className="flex flex-col">
                      <span className="text-sm font-semibold text-on-surface">13:10:12</span>
                      <span className="text-[10px] text-slate-400">22/05/2024</span>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <code className="text-xs font-mono bg-surface-container px-2 py-1 rounded text-primary">FF:D3:21:0A</code>
                  </td>
                  <td className="px-6 py-5">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-tight bg-error-container text-on-error-container">
                      <span className="w-1 h-1 rounded-full bg-error mr-1.5"></span> Ra
                    </span>
                  </td>
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg overflow-hidden flex-shrink-0 bg-slate-200">
                        <img className="w-full h-full object-cover" alt="Rear view of a black luxury car" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCOd_k353bVNXK-dhVbfMrkaMEgTBCtHfqJo9vFlXtQGIBFDA38WEJYSPs7fFOCrvNWfQEhPqjAXWjTL37lHfZmHoCgn8Tsu7m3RUF78xfYJQEMPI5_rYSp8FdMy_9Re_hlNb2INsoNOEPE1YfLhWYuw1CCREZD_8wVUfSxGOpHfz56yAlwIFXTnjJrMHmsxc2DzTp13J0gro5jIY_c9M6k5x3zbgu4zqFHWaYNtA0YMgF7cvNFDnRJTtmYVtHLYp0tbM8VQuHbphxG" />
                      </div>
                      <span className="text-sm font-bold text-on-surface">59A-999.99</span>
                    </div>
                  </td>
                  <td className="px-6 py-5 font-body text-sm text-on-surface-variant">125 phút</td>
                  <td className="px-6 py-5 font-body text-sm font-bold text-on-surface">35,000</td>
                  <td className="px-6 py-5 text-right">
                    <button className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-primary">
                      <span className="material-symbols-outlined">visibility</span>
                    </button>
                  </td>
                </tr>

                {/* Row 3 */}
                <tr className="hover:bg-slate-50/80 transition-colors group">
                  <td className="px-6 py-5">
                    <div className="flex flex-col">
                      <span className="text-sm font-semibold text-on-surface">12:45:00</span>
                      <span className="text-[10px] text-slate-400">22/05/2024</span>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <code className="text-xs font-mono bg-surface-container px-2 py-1 rounded text-primary">C1:55:E2:BB</code>
                  </td>
                  <td className="px-6 py-5">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-tight bg-error-container text-on-error-container">
                      <span className="w-1 h-1 rounded-full bg-error mr-1.5"></span> Ra
                    </span>
                  </td>
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg overflow-hidden flex-shrink-0 bg-slate-200">
                        <img className="w-full h-full object-cover" alt="Sleek white electric car" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDleRe-IUMRaQNnxctvqk5yL3Y6yEY6RcIe7cYrSJQmn6NZRkhvhNhKFQaty_vNef_2QYIYXeSpGhfxb-QX-AjhIJ35kbrHZe1Qg3cEvw8sxp1vZIwhmu8RoT61v3wMEPkUbpcY0VRqxqID1BpvW8SSjpdbfs6CnFJRVR1BHhahnlagJ9kgjJD4nQaDZiwUkfQP70kl02feO8ygSyLeyDiPcV3r5fE3eYEOMM0iY4wFV1gM2wKd0fSXRZnJihDFgNizZu9qA0103tbj" />
                      </div>
                      <span className="text-sm font-bold text-on-surface">30H-888.88</span>
                    </div>
                  </td>
                  <td className="px-6 py-5 font-body text-sm text-on-surface-variant">45 phút</td>
                  <td className="px-6 py-5 font-body text-sm font-bold text-on-surface">15,000</td>
                  <td className="px-6 py-5 text-right">
                    <button className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-primary">
                      <span className="material-symbols-outlined">visibility</span>
                    </button>
                  </td>
                </tr>

                {/* Row 4 */}
                <tr className="hover:bg-slate-50/80 transition-colors group">
                  <td className="px-6 py-5">
                    <div className="flex flex-col">
                      <span className="text-sm font-semibold text-on-surface">11:30:55</span>
                      <span className="text-[10px] text-slate-400">22/05/2024</span>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <code className="text-xs font-mono bg-surface-container px-2 py-1 rounded text-primary">88:7A:B2:34</code>
                  </td>
                  <td className="px-6 py-5">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-tight bg-secondary-container text-on-secondary-container">
                      <span className="w-1 h-1 rounded-full bg-secondary mr-1.5"></span> Vào
                    </span>
                  </td>
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg overflow-hidden flex-shrink-0 bg-slate-200">
                        <img className="w-full h-full object-cover" alt="High-end red sports car" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBTtpeHqSmDv2dMhSB28ZQTscdQMd5KKEqUVcEM6CT9le8paSXXCOwCpPFMB4WYckbywUotB3ftNvHpYNhxJXcy_ZxAencBCcZySkFUanSyMOGbWP8lugQXJnWcFsO1WDCXwlsCoYKu6UrKk_rUnH_ds3CD51SWI2DktnDkY18wmX9ZrGw57iA6P9piza3-BUyv7aaqvOqPN9yDfjBJDkUVs5Y0CM71Dw9pIo0FtqDFEsD5eQjgQBf3O7UpSsGkeEtsRWL76jdfEEyp" />
                      </div>
                      <span className="text-sm font-bold text-on-surface">51A-002.11</span>
                    </div>
                  </td>
                  <td className="px-6 py-5 font-body text-sm text-on-surface-variant">--</td>
                  <td className="px-6 py-5 font-body text-sm font-bold text-on-surface">--</td>
                  <td className="px-6 py-5 text-right">
                    <button className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-primary">
                      <span className="material-symbols-outlined">visibility</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="p-6 bg-slate-50/50 flex items-center justify-between">
            <span className="text-xs text-slate-500">Hiển thị 1 - 4 của 1,248 bản ghi</span>
            <div className="flex gap-2">
              <button className="w-8 h-8 flex items-center justify-center rounded-lg border border-slate-200 text-slate-400 hover:bg-white transition-colors">
                <span className="material-symbols-outlined text-sm">chevron_left</span>
              </button>
              <button className="w-8 h-8 flex items-center justify-center rounded-lg bg-primary text-white text-xs font-bold">1</button>
              <button className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white border border-transparent hover:border-slate-200 text-slate-600 text-xs font-bold">2</button>
              <button className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white border border-transparent hover:border-slate-200 text-slate-600 text-xs font-bold">3</button>
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