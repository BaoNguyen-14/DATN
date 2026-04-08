import React, { createContext, useContext, useReducer, useCallback, useMemo, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import type {
  ParkingAppState,
  WSMessage,
  WSCommand,
  GateState,
  LCDContent,
  RFIDScannedPayload,
  PlateRecognizedPayload,
  SlotUpdatePayload,
  GateStatusPayload,
  LCDUpdatePayload,
  BuzzerFeedbackPayload,
  SessionUpdatePayload,
  StatsPayload,
  ParkingSession,
} from '../types/parking';

// ===== Initial State =====
const defaultGate = (gateType: 'entry' | 'exit'): GateState => ({
  gateType,
  servo: 'closed',
  ir: 'clear',
  rfidReady: true,
  lastCardUID: null,
  barrierCountdown: null,
});

const defaultLCD = (title: string): LCDContent => ({
  line1: title,
  line2: 'Thoi gian:          ',
  line3: 'Bien so xe:         ',
  line4: 'Trang thai: SAN SANG',
});

const initialState: ParkingAppState = {
  connected: false,
  entryGate: defaultGate('entry'),
  exitGate: defaultGate('exit'),
  entryLCD: defaultLCD('     CONG VAO       '),
  exitLCD: defaultLCD('      CONG RA       '),
  entryPlate: null,
  exitPlate: null,
  slots: Array.from({ length: 8 }, (_, i) => ({
    id: i + 1,
    status: 'free' as const,
    lastUpdated: new Date().toISOString(),
  })),
  sessions: [],
  stats: {
    totalIn: 0,
    totalOut: 0,
    availableSlots: 8,
    totalSlots: 8,
    lastCost: null,
  },
  lastBuzzer: null,
};

// ===== Actions =====
type Action =
  | { type: 'SET_CONNECTED'; payload: boolean }
  | { type: 'RFID_SCANNED'; payload: RFIDScannedPayload }
  | { type: 'PLATE_RECOGNIZED'; payload: PlateRecognizedPayload }
  | { type: 'SLOT_UPDATE'; payload: SlotUpdatePayload }
  | { type: 'GATE_STATUS'; payload: GateStatusPayload }
  | { type: 'LCD_UPDATE'; payload: LCDUpdatePayload }
  | { type: 'BUZZER_FEEDBACK'; payload: BuzzerFeedbackPayload }
  | { type: 'SESSION_UPDATE'; payload: SessionUpdatePayload }
  | { type: 'STATS_UPDATE'; payload: StatsPayload }
  | { type: 'ADD_SESSION'; payload: ParkingSession };

// ===== Reducer =====
function parkingReducer(state: ParkingAppState, action: Action): ParkingAppState {
  switch (action.type) {
    case 'SET_CONNECTED':
      return { ...state, connected: action.payload };

    case 'RFID_SCANNED': {
      const { gateType, cardUID } = action.payload;
      if (gateType === 'entry') {
        return {
          ...state,
          entryGate: { ...state.entryGate, lastCardUID: cardUID },
        };
      }
      return {
        ...state,
        exitGate: { ...state.exitGate, lastCardUID: cardUID },
      };
    }

    case 'PLATE_RECOGNIZED': {
      const plate = action.payload;
      if (plate.gateType === 'entry') {
        return { ...state, entryPlate: plate };
      }
      return { ...state, exitPlate: plate };
    }

    case 'SLOT_UPDATE':
      return { ...state, slots: action.payload.slots };

    case 'GATE_STATUS': {
      const gate = action.payload;
      if (gate.gateType === 'entry') {
        return { ...state, entryGate: gate };
      }
      return { ...state, exitGate: gate };
    }

    case 'LCD_UPDATE': {
      const { gateType, content } = action.payload;
      if (gateType === 'entry') {
        return { ...state, entryLCD: content };
      }
      return { ...state, exitLCD: content };
    }

    case 'BUZZER_FEEDBACK':
      return { ...state, lastBuzzer: action.payload };

    case 'SESSION_UPDATE': {
      const session = action.payload;
      const existingIdx = state.sessions.findIndex((s) => s.id === session.id);
      const newSessions =
        existingIdx >= 0
          ? state.sessions.map((s, i) => (i === existingIdx ? session : s))
          : [session, ...state.sessions];
      return { ...state, sessions: newSessions.slice(0, 100) };
    }

    case 'STATS_UPDATE':
      return { ...state, stats: action.payload };

    case 'ADD_SESSION':
      return {
        ...state,
        sessions: [action.payload, ...state.sessions].slice(0, 100),
      };

    default:
      return state;
  }
}

// ===== Context =====
interface ParkingContextType {
  state: ParkingAppState;
  dispatch: React.Dispatch<Action>;
  sendCommand: (command: WSCommand) => void;
  connected: boolean;
  wsUrl: string;
  setWsUrl: (url: string) => void;
}

const ParkingContext = createContext<ParkingContextType | null>(null);

// ===== Provider =====
export function ParkingProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(parkingReducer, initialState);
  const [wsUrl, setWsUrl] = useState(() => {
    return localStorage.getItem('parking_ws_url') || 'ws://192.168.1.9:8765';
  });

  const handleSetWsUrl = useCallback((url: string) => {
    localStorage.setItem('parking_ws_url', url);
    setWsUrl(url);
  }, []);

  const handleMessage = useCallback((message: WSMessage) => {
    switch (message.type) {
      case 'rfid_scanned':
        dispatch({ type: 'RFID_SCANNED', payload: message.payload as RFIDScannedPayload });
        break;
      case 'plate_recognized':
        dispatch({ type: 'PLATE_RECOGNIZED', payload: message.payload as PlateRecognizedPayload });
        break;
      case 'slot_update':
        dispatch({ type: 'SLOT_UPDATE', payload: message.payload as SlotUpdatePayload });
        break;
      case 'gate_status':
        dispatch({ type: 'GATE_STATUS', payload: message.payload as GateStatusPayload });
        break;
      case 'lcd_update':
        dispatch({ type: 'LCD_UPDATE', payload: message.payload as LCDUpdatePayload });
        break;
      case 'buzzer_feedback':
        dispatch({ type: 'BUZZER_FEEDBACK', payload: message.payload as BuzzerFeedbackPayload });
        break;
      case 'session_update':
        dispatch({ type: 'SESSION_UPDATE', payload: message.payload as SessionUpdatePayload });
        break;
      case 'stats_update':
        dispatch({ type: 'STATS_UPDATE', payload: message.payload as StatsPayload });
        break;
      case 'connection_ack':
        console.log('[Parking] Connection acknowledged by Pi');
        break;
    }
  }, []);

  const handleStatusChange = useCallback((connected: boolean) => {
    dispatch({ type: 'SET_CONNECTED', payload: connected });
  }, []);

  const { sendCommand, connected } = useWebSocket({
    url: wsUrl,
    onMessage: handleMessage,
    onStatusChange: handleStatusChange,
  });

  const value = useMemo(
    () => ({ state, dispatch, sendCommand, connected, wsUrl, setWsUrl: handleSetWsUrl }),
    [state, dispatch, sendCommand, connected, wsUrl, handleSetWsUrl]
  );

  return React.createElement(ParkingContext.Provider, { value }, children);
}

// ===== Hook =====
export function useParkingContext() {
  const context = useContext(ParkingContext);
  if (!context) {
    throw new Error('useParkingContext must be used within a ParkingProvider');
  }
  return context;
}
