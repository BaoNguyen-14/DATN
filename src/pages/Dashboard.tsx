export default function Dashboard() {
  return (
    <main className="p-8 flex flex-col gap-8 max-w-[1600px] mx-auto w-full flex-1">
      {/* Thống kê nhanh (Section 1) */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Tổng xe vào */}
        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm border-l-4 border-primary">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant font-label">Tổng xe vào</span>
            <span className="material-symbols-outlined text-primary">login</span>
          </div>
          <div className="text-4xl font-extrabold font-headline text-primary tracking-tight">1,284</div>
          <div className="mt-2 flex items-center gap-1 text-[10px] text-secondary font-bold">
            <span className="material-symbols-outlined text-xs">trending_up</span>
            +12% so với hôm qua
          </div>
        </div>

        {/* Tổng xe ra */}
        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm border-l-4 border-on-tertiary-fixed-variant">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant font-label">Tổng xe ra</span>
            <span className="material-symbols-outlined text-on-tertiary-fixed-variant">logout</span>
          </div>
          <div className="text-4xl font-extrabold font-headline text-on-tertiary-fixed-variant tracking-tight">1,156</div>
          <div className="mt-2 flex items-center gap-1 text-[10px] text-secondary font-bold">
            <span className="material-symbols-outlined text-xs">trending_up</span>
            +8% so với hôm qua
          </div>
        </div>

        {/* Số chỗ hiện tại */}
        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm border-l-4 border-secondary">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant font-label">Số chỗ hiện tại</span>
            <span className="material-symbols-outlined text-secondary">local_parking</span>
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-4xl font-extrabold font-headline text-secondary tracking-tight">42</div>
            <div className="text-sm font-bold text-on-surface-variant">/ 150</div>
          </div>
          <div className="mt-4 w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full bg-secondary rounded-full" style={{ width: '28%' }}></div>
          </div>
        </div>

        {/* Tổng doanh thu */}
        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm border-l-4 border-tertiary-container">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant font-label">Chi phí xe vừa ra</span>
            <span className="material-symbols-outlined text-tertiary-container">payments</span>
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-4xl font-extrabold font-headline text-tertiary-container tracking-tight">15,000</div>
            <div className="text-sm font-bold text-on-surface-variant uppercase">VNĐ</div>
          </div>
        </div>
      </section>

      {/* Khu vực chính (Section 2 & 3) */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Camera trực tiếp (Left Column - 2/3 width) */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="w-3 h-3 bg-error rounded-full animate-pulse"></span>
              <h2 className="text-lg font-bold font-headline tracking-tight uppercase">Camera trực tiếp - Cổng vào</h2>
            </div>
            <div className="flex gap-2">
              <span className="px-3 py-1 bg-surface-container-high rounded-full text-[10px] font-bold text-on-surface-variant">FULL HD 1080P</span>
              <span className="px-3 py-1 bg-surface-container-high rounded-full text-[10px] font-bold text-on-surface-variant">CAM_01</span>
            </div>
          </div>

          <div className="relative aspect-video bg-slate-900 rounded-xl overflow-hidden shadow-xl">
            <img
              alt="Live parking entrance camera feed"
              className="w-full h-full object-cover opacity-80"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuCtQnLDE4TSc-qDQ9yXeTayfjjXXEySjCzRLQTqS2LuNPQxnrrVFB4IlurBUwZYoWwdCEoPcmWgYeZkJWl10z52CDec0CWfD6BZKm7TE7tou1DWlSPVKkHiApMA90Ydt_KlHEdIyw8Me285unetutkvWmfoImJtCjEIpYNwpP2qnr5ThIx-Smy2MbMfwUbrYvrBQ3NUe09KO6X-o-J3AX97vXxsvYQGEuoyDxODfC86E7FzUdFyvYob0FO--TRYSbykCeqlCTiehf-z"
            />
            {/* Overlay interface for Camera */}
            <div className="absolute inset-0 pointer-events-none p-6 flex flex-col justify-between">
              <div className="flex justify-between items-start">
                <div className="bg-black/40 backdrop-blur-md p-2 rounded-lg border border-white/10">
                  <div className="text-white text-[10px] font-mono tracking-tighter">TIMESTAMP: 2024-05-20 14:32:15</div>
                </div>
                <div className="flex flex-col gap-2">
                  <div className="glass-panel px-4 py-2 rounded-lg border border-white/20 text-blue-900 font-bold text-xs flex items-center gap-2">
                    <span className="material-symbols-outlined text-sm">visibility</span>
                    MONITORING
                  </div>
                </div>
              </div>

              {/* Recognition Box Placeholder */}
              <div className="relative w-48 h-32 border-2 border-secondary/60 rounded-sm self-center">
                <div className="absolute -top-6 left-0 bg-secondary px-2 py-0.5 text-[10px] text-white font-bold">DETECTING VEHICLE...</div>
                <div className="absolute -top-1 -left-1 w-4 h-4 border-t-2 border-l-2 border-secondary"></div>
                <div className="absolute -top-1 -right-1 w-4 h-4 border-t-2 border-r-2 border-secondary"></div>
                <div className="absolute -bottom-1 -left-1 w-4 h-4 border-b-2 border-l-2 border-secondary"></div>
                <div className="absolute -bottom-1 -right-1 w-4 h-4 border-b-2 border-r-2 border-secondary"></div>
              </div>

              <div className="flex justify-between items-end">
                <div className="flex gap-2">
                  <button className="pointer-events-auto p-2 bg-white/20 hover:bg-white/40 backdrop-blur-xl rounded-full text-white transition-all">
                    <span className="material-symbols-outlined">zoom_in</span>
                  </button>
                  <button className="pointer-events-auto p-2 bg-white/20 hover:bg-white/40 backdrop-blur-xl rounded-full text-white transition-all">
                    <span className="material-symbols-outlined">photo_camera</span>
                  </button>
                </div>
                <div className="bg-black/40 backdrop-blur-md px-3 py-1 rounded-full border border-white/10">
                  <span className="text-white text-[10px] font-bold">REC ●</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Kết quả xử lý (Right Column - 1/3 width) */}
        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-lg font-bold font-headline tracking-tight uppercase">Kết quả xử lý</h2>
            <span className="material-symbols-outlined text-secondary">verified</span>
          </div>

          <div className="bg-surface-container-lowest rounded-xl shadow-lg overflow-hidden flex flex-col">
            {/* Plate Capture */}
            <div className="p-6 border-b border-slate-100">
              <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-3 font-label">Ảnh chụp biển số</div>
              <div className="relative aspect-[3/1] bg-slate-200 rounded-lg overflow-hidden border-2 border-primary-fixed-dim">
                <img
                  alt="License plate close-up"
                  className="w-full h-full object-cover"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuDUfkImsrPKyodn20bVHQgNYeq-eBHjr2yQ7urdrzgGEpqCT6R6vOUqhs_3-YA1Z50SD8bgBKUlQycpM3Klk3s3o0LtLFZJXa-UV_aAX0aX9N6hGCYUD8EkTuFA5gNUdKg81nOI7U4m4gw4o_OX8qxmB_fJJ6eMqIuFl4pCIfj1DHFmVb-NxA8eQFo9THc9n8DpmhT35B31i2x9tzY27j8HKqjc9xYYKmjBI_gv6CMeHsMo1HcoHhPxGXyfMa-Uk1q7xB8Scs0bNDvq"
                />
                <div className="absolute inset-0 bg-primary/5"></div>
              </div>
            </div>

            {/* Data & Results */}
            <div className="p-6 space-y-6">
              <div className="space-y-4">
                <div>
                  <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest font-label mb-1">Biển số nhận diện</div>
                  <div className="text-4xl font-black font-headline text-primary tracking-tighter">51G - 888.88</div>
                </div>
                <div className="grid gap-4">
                  <div>
                    <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest font-label mb-1">Thời gian vào</div>
                    <div className="text-base font-bold">14:32:15</div>
                  </div>
                </div>
                <div>
                  <div className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest font-label mb-1">Trạng thái hệ thống</div>
                  <div className="flex items-center gap-2 text-secondary font-bold">
                    <span className="w-2 h-2 bg-secondary rounded-full"></span>
                    Xác thực thành công
                  </div>
                </div>
              </div>

              {/* Primary CTA Button */}
              <button className="w-full py-4 bg-gradient-to-br from-primary to-primary-container text-on-primary rounded-full font-headline font-bold text-lg shadow-lg hover:shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-3">
                <span className="material-symbols-outlined">door_front</span>
                MỞ THANH CHẮN
              </button>
            </div>
          </div>

          {/* Recent Activity Mini-List */}
          <div className="bg-surface-container-low p-5 rounded-xl">
            <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Lượt xe vừa vào</div>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 bg-white rounded-lg shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded bg-slate-100 flex items-center justify-center text-primary">
                    <span className="material-symbols-outlined text-xl">directions_car</span>
                  </div>
                  <div>
                    <div className="text-sm font-bold">29A - 123.45</div>
                    <div className="text-[10px] text-slate-400">14:28:05</div>
                  </div>
                </div>
                <span className="text-[10px] font-bold text-secondary uppercase">Đã vào</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-white rounded-lg shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded bg-slate-100 flex items-center justify-center text-primary">
                    <span className="material-symbols-outlined text-xl">directions_car</span>
                  </div>
                  <div>
                    <div className="text-sm font-bold">51H - 999.01</div>
                    <div className="text-[10px] text-slate-400">14:25:30</div>
                  </div>
                </div>
                <span className="text-[10px] font-bold text-secondary uppercase">Đã vào</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}