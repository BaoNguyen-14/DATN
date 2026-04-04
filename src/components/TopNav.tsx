export default function TopNav({ title = "Đồ án tốt nghiệp - Bãi đậu xe thông minh", subtitle = "" }) {
  return (
    <header className="w-full top-0 sticky z-40 bg-white shadow-sm flex justify-between items-center px-6 py-4 border-b border-slate-100">
      <div className="flex flex-col">
        <h1 className="text-xl font-bold tracking-tighter text-blue-950 font-headline uppercase leading-none">
          {title}
        </h1>
        {subtitle && (
          <span className="text-[10px] font-headline font-semibold tracking-tight text-slate-500 uppercase mt-1">
            {subtitle}
          </span>
        )}
      </div>
      <div className="flex items-center gap-6">
        <div className="relative hidden md:flex items-center bg-surface-container-highest px-4 py-2 rounded-full">
          <span className="material-symbols-outlined absolute left-3 text-slate-400 text-sm">search</span>
          <input
            className="pl-8 pr-4 py-1 bg-transparent border-none rounded-full text-sm focus:ring-2 focus:ring-primary focus:bg-surface-container-lowest transition-all w-64 outline-none"
            placeholder="Tìm kiếm..."
            type="text"
          />
        </div>
        <div className="flex items-center gap-3">
          <button className="p-2 rounded-full hover:bg-slate-50 transition-colors active:scale-95 duration-150 text-slate-600">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button className="flex items-center gap-2 p-1 pr-3 rounded-full hover:bg-slate-50 transition-colors active:scale-95 duration-150">
            <span className="material-symbols-outlined text-blue-900 text-3xl">account_circle</span>
            <span className="font-headline text-sm font-semibold tracking-tight text-blue-900 hidden sm:inline">Admin</span>
          </button>
        </div>
      </div>
    </header>
  );
}