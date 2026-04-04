export default function Footer() {
  return (
    <footer className="w-full py-6 px-8 mt-auto flex flex-col md:flex-row justify-between items-center gap-4 border-t border-slate-100 bg-white">
      <div className="flex items-center gap-2 mb-2 md:mb-0">
        <span className="w-2 h-2 bg-secondary rounded-full animate-pulse"></span>
        <span className="font-body text-[10px] sm:text-xs text-slate-500 uppercase tracking-widest font-medium">
          © 2024 HỆ THỐNG BÃI ĐẬU XE THÔNG MINH - TRẠNG THÁI: HOẠT ĐỘNG
        </span>
      </div>
      <div className="flex gap-6 mt-2 md:mt-0">
        <a className="font-body text-[10px] sm:text-xs text-slate-500 uppercase tracking-widest font-bold hover:text-primary transition-colors" href="#">LIÊN HỆ</a>
        <a className="font-body text-[10px] sm:text-xs text-slate-500 uppercase tracking-widest font-bold hover:text-primary transition-colors" href="#">ĐIỀU KHOẢN</a>
        <a className="font-body text-[10px] sm:text-xs text-slate-500 uppercase tracking-widest font-bold hover:text-primary transition-colors" href="#">BÁO CÁO LỖI</a>
      </div>
    </footer>
  );
}