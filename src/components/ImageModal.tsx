import React from 'react';

interface ImageModalProps {
  url: string;
  title: string;
  onClose: () => void;
}

export default function ImageModal({ url, title, onClose }: ImageModalProps) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200" onClick={onClose}>
      <div className="relative max-w-5xl w-full bg-white rounded-2xl overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">image</span>
            <h3 className="font-bold text-on-surface">{title}</h3>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-100 transition-colors">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>
        
        {/* Image Content */}
        <div className="bg-slate-900 aspect-video flex items-center justify-center overflow-hidden">
          <img src={url} alt={title} className="max-w-full max-h-full object-contain shadow-inner" />
        </div>
        
        {/* Footer */}
        <div className="p-4 bg-slate-50 flex justify-between items-center">
          <div className="flex flex-col">
            <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest leading-none mb-1">Chi tiết hình ảnh</div>
            <div className="text-xs text-slate-400 font-medium italic">Ảnh gốc không qua cắt gọt từ hệ thống camera</div>
          </div>
          <button onClick={onClose} className="px-8 py-2.5 bg-primary text-white text-xs font-bold rounded-full hover:shadow-lg active:scale-95 transition-all">
            Đóng cửa sổ
          </button>
        </div>
      </div>
    </div>
  );
}
