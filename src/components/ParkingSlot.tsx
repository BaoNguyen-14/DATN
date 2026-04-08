import type { ParkingSlot as ParkingSlotType } from '../types/parking';

interface ParkingSlotProps {
  slot: ParkingSlotType;
  className?: string;
}

export default function ParkingSlot({ slot, className = '' }: ParkingSlotProps) {
  const isOccupied = slot.status === 'occupied';
  const timeAgo = getTimeAgo(slot.lastUpdated);

  return (
    <div
      className={`relative group cursor-default rounded-xl border-2 transition-all duration-500 ${
        isOccupied
          ? 'bg-red-50 border-red-200 hover:border-red-300 shadow-sm hover:shadow-red-100'
          : 'bg-emerald-50 border-emerald-200 hover:border-emerald-300 shadow-sm hover:shadow-emerald-100'
      } ${className}`}
    >
      {/* Slot Header */}
      <div className="p-4 flex flex-col items-center gap-2">
        {/* Slot Number */}
        <div className={`text-[10px] font-bold uppercase tracking-widest ${
          isOccupied ? 'text-red-400' : 'text-emerald-400'
        }`}>
          Slot
        </div>
        <div className={`text-3xl font-headline font-extrabold ${
          isOccupied ? 'text-red-600' : 'text-emerald-600'
        }`}>
          {String(slot.id).padStart(2, '0')}
        </div>

        {/* Status Icon */}
        <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500 ${
          isOccupied
            ? 'bg-red-100 text-red-600'
            : 'bg-emerald-100 text-emerald-600'
        }`}>
          <span className="material-symbols-outlined text-xl"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            {isOccupied ? 'directions_car' : 'check_circle'}
          </span>
        </div>

        {/* Status Text */}
        <div className={`text-[10px] font-bold uppercase tracking-widest ${
          isOccupied ? 'text-red-500' : 'text-emerald-500'
        }`}>
          {isOccupied ? 'ĐÃ ĐẬU' : 'TRỐNG'}
        </div>
      </div>

      {/* Tooltip on hover */}
      <div className="absolute -top-10 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
        <div className="bg-slate-900 text-white text-[10px] font-medium px-3 py-1.5 rounded-lg whitespace-nowrap shadow-lg">
          Cập nhật: {timeAgo}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900" />
        </div>
      </div>

      {/* Pulse effect for occupied */}
      {isOccupied && (
        <div className="absolute inset-0 rounded-xl border-2 border-red-300 animate-ping opacity-20 pointer-events-none" />
      )}
    </div>
  );
}

function getTimeAgo(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s trước`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m trước`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h trước`;
}
