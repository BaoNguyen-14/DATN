export default function Settings() {
  return (
    <section className="p-8 max-w-5xl mx-auto w-full flex-1">
      <div className="mb-10">
        <h2 className="text-4xl font-extrabold text-primary tracking-tight mb-2">Cài đặt hệ thống</h2>
        <p className="text-on-surface-variant font-body">Cấu hình các tham số vận hành và thông tin bãi đỗ xe của bạn.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
        {/* Pricing Configuration (Priority Item) */}
        <div className="md:col-span-12 lg:col-span-5">
          <div className="bg-primary-container p-8 rounded-lg shadow-sm relative overflow-hidden">
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
                      defaultValue="1000"
                    />
                    <div className="absolute right-5 top-1/2 -translate-y-1/2 text-white/50 font-bold">VNĐ</div>
                  </div>
                </label>
                <p className="text-blue-200 text-xs italic">Lưu ý: Mức phí này sẽ được áp dụng ngay lập tức cho tất cả lượt gửi mới.</p>
              </div>
            </div>

            {/* Abstract Background Decoration */}
            <div className="absolute -right-10 -bottom-10 w-48 h-48 bg-white/5 rounded-full blur-3xl"></div>
          </div>
        </div>

        {/* General & Technical Settings */}
        <div className="md:col-span-12 lg:col-span-7 space-y-6">
          {/* General Information */}
          <div className="bg-surface-container-lowest p-8 rounded-lg shadow-sm">
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
                  defaultValue="Smart Parking Central"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-2">Địa chỉ bãi xe</label>
                <textarea
                  className="w-full bg-surface-container-low border-none rounded-lg py-3 px-4 focus:ring-2 focus:ring-primary focus:bg-surface-container-lowest transition-all"
                  rows={2}
                  defaultValue="Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội"
                ></textarea>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Fixed Floating Footer for Actions */}
      <div className="mt-12 flex justify-end">
        <button className="bg-gradient-to-br from-primary to-primary-container text-on-primary px-10 py-4 rounded-full font-headline font-bold text-lg shadow-xl hover:shadow-primary/20 active:scale-95 transition-all flex items-center gap-3">
          <span className="material-symbols-outlined">save</span>
          Lưu cài đặt
        </button>
      </div>
    </section>
  );
}