import ConnectionStatus from './ConnectionStatus';
import { useParkingContext } from '../hooks/useParkingState';

export default function TopNav({ title = "Đồ án tốt nghiệp - Bãi đậu xe thông minh", subtitle = "" }) {
  const { connected } = useParkingContext();

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
      <ConnectionStatus connected={connected} className="hidden md:flex" />
    </header>
  );
}