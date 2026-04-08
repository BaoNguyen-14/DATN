interface ConnectionStatusProps {
  connected: boolean;
  className?: string;
}

export default function ConnectionStatus({ connected, className = '' }: ConnectionStatusProps) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider border transition-all ${
        connected
          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
          : 'bg-red-50 text-red-600 border-red-200'
      }`}>
        <span className={`w-2 h-2 rounded-full ${
          connected
            ? 'bg-emerald-500 animate-pulse'
            : 'bg-red-500 animate-pulse'
        }`} />
        <span className="material-symbols-outlined text-xs">
          {connected ? 'wifi' : 'wifi_off'}
        </span>
        {connected ? 'PI CONNECTED' : 'DISCONNECTED'}
      </div>
    </div>
  );
}
