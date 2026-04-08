import { useState, useEffect, useCallback } from 'react';
import type { GateState, GateType } from '../types/parking';
import { useParkingContext } from '../hooks/useParkingState';

interface GateControlProps {
  gate: GateState;
  gateType: GateType;
  plateRecognized: boolean;
  className?: string;
}

export default function GateControl({ gate, gateType, plateRecognized, className = '' }: GateControlProps) {
  const { sendCommand } = useParkingContext();
  const [countdown, setCountdown] = useState<number | null>(null);
  const isEntry = gateType === 'entry';
  const canOpen = plateRecognized && gate.servo === 'closed';

  const handleOpenGate = useCallback(() => {
    if (!canOpen) return;
    sendCommand({
      type: 'open_gate',
      payload: { gateType },
    });
  }, [canOpen, gateType, sendCommand]);

  // Countdown effect when barrier is closing
  useEffect(() => {
    if (gate.barrierCountdown !== null && gate.barrierCountdown > 0) {
      setCountdown(gate.barrierCountdown);
    } else {
      setCountdown(null);
    }
  }, [gate.barrierCountdown]);

  useEffect(() => {
    if (countdown === null || countdown <= 0) return;
    const timer = setTimeout(() => setCountdown((c) => (c !== null ? c - 1 : null)), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Status Indicators Row */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* IR Sensor */}
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
          gate.ir === 'detected'
            ? 'bg-amber-50 text-amber-700 border-amber-200'
            : 'bg-emerald-50 text-emerald-700 border-emerald-200'
        }`}>
          <span className={`w-2 h-2 rounded-full ${
            gate.ir === 'detected' ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'
          }`} />
          <span className="material-symbols-outlined text-xs">sensors</span>
          IR: {gate.ir === 'detected' ? 'CÓ XE' : 'TRỐNG'}
        </div>

        {/* Servo State */}
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
          gate.servo === 'open'
            ? 'bg-blue-50 text-blue-700 border-blue-200'
            : 'bg-slate-100 text-slate-600 border-slate-200'
        }`}>
          <span className="material-symbols-outlined text-xs">
            {gate.servo === 'open' ? 'lock_open' : 'lock'}
          </span>
          {gate.servo === 'open' ? 'ĐÃ MỞ' : 'ĐÃ ĐÓNG'}
          {countdown !== null && countdown > 0 && (
            <span className="ml-1 text-blue-500">({countdown}s)</span>
          )}
        </div>

        {/* RFID Ready */}
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
          gate.rfidReady
            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
            : 'bg-red-50 text-red-700 border-red-200'
        }`}>
          <span className="material-symbols-outlined text-xs">contactless</span>
          RFID: {gate.rfidReady ? 'SẴN SÀNG' : 'BẬN'}
        </div>
      </div>

      {/* Barrier Animation */}
      <div className="relative h-8 bg-slate-100 rounded-lg overflow-hidden flex items-center">
        <div className="absolute left-3 w-4 h-full flex items-center">
          <div className="w-3 h-3 rounded-sm bg-slate-400" />
        </div>
        <div
          className={`absolute left-6 h-1.5 rounded-r-full transition-all duration-700 ease-in-out ${
            gate.servo === 'open'
              ? 'bg-emerald-400 w-[15%]'
              : 'bg-red-400 w-[85%]'
          }`}
          style={{
            transformOrigin: 'left center',
          }}
        />
        <div className={`absolute right-3 text-[10px] font-bold uppercase tracking-wider ${
          gate.servo === 'open' ? 'text-emerald-600' : 'text-slate-500'
        }`}>
          {gate.servo === 'open' ? '↑ THANH CHẮN MỞ' : '── THANH CHẮN ĐÓNG'}
        </div>
      </div>

      {/* Open Gate Button */}
      <button
        onClick={handleOpenGate}
        disabled={!canOpen}
        className={`w-full py-4 rounded-2xl font-headline font-bold text-base shadow-lg transition-all flex items-center justify-center gap-3 ${
          canOpen
            ? isEntry
              ? 'bg-gradient-to-br from-primary to-primary-container text-on-primary hover:shadow-primary/30 hover:scale-[1.02] active:scale-95'
              : 'bg-gradient-to-br from-secondary to-emerald-800 text-white hover:shadow-secondary/30 hover:scale-[1.02] active:scale-95'
            : 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
        }`}
      >
        <span className="material-symbols-outlined">
          {gate.servo === 'open' ? 'door_front' : canOpen ? 'lock_open' : 'lock'}
        </span>
        {gate.servo === 'open'
          ? (countdown ? `ĐANG ĐÓNG (${countdown}s)` : 'THANH CHẮN ĐANG MỞ')
          : canOpen
            ? `MỞ THANH CHẮN - ${isEntry ? 'CỔNG VÀO' : 'CỔNG RA'}`
            : 'CHỜ QUẸT THẺ & NHẬN DIỆN BSX'}
      </button>
    </div>
  );
}
