// ===== Parking Slot =====
export type SlotStatus = 'free' | 'occupied';

export interface ParkingSlot {
  id: number;           // 1-8
  status: SlotStatus;
  lastUpdated: string;  // ISO timestamp
}

// ===== Gate =====
export type GateType = 'entry' | 'exit';
export type ServoState = 'open' | 'closed';
export type IRState = 'detected' | 'clear';

export interface GateState {
  gateType: GateType;
  servo: ServoState;
  ir: IRState;
  rfidReady: boolean;
  lastCardUID: string | null;
  barrierCountdown: number | null;  // seconds remaining before auto-close
}

// ===== License Plate =====
export interface PlateResult {
  plateText: string;
  imageUrl: string;       // URL to captured plate image
  timestamp: string;      // ISO timestamp
  confidence: number;     // 0-100
  gateType: GateType;
}

// ===== LCD 20x4 =====
export interface LCDContent {
  line1: string;  // max 20 chars
  line2: string;
  line3: string;
  line4: string;
}

// ===== Parking Session =====
export interface ParkingSession {
  id: string;
  cardUID: string;
  plateIn: string;
  plateOut: string | null;
  plateImageIn: string;
  plateImageOut: string | null;
  timeIn: string;         // ISO timestamp
  timeOut: string | null;  // ISO timestamp
  durationMinutes: number | null;
  cost: number | null;     // VND
  matched: boolean | null; // null = chưa ra, true = khớp, false = lỗi
}

// ===== Buzzer Feedback =====
export type BuzzerType = 'success' | 'error';

export interface BuzzerFeedback {
  type: BuzzerType;
  gateType: GateType;
  timestamp: string;
}

// ===== WebSocket Messages =====
export type WSMessageType =
  | 'rfid_scanned'
  | 'plate_recognized'
  | 'slot_update'
  | 'gate_status'
  | 'lcd_update'
  | 'buzzer_feedback'
  | 'session_update'
  | 'stats_update'
  | 'connection_ack';

export interface WSMessage {
  type: WSMessageType;
  payload: unknown;
  timestamp: string;
}

// Specific payloads
export interface RFIDScannedPayload {
  gateType: GateType;
  cardUID: string;
}

export interface PlateRecognizedPayload extends PlateResult {}

export interface SlotUpdatePayload {
  slots: ParkingSlot[];
}

export interface GateStatusPayload extends GateState {}

export interface LCDUpdatePayload {
  gateType: GateType;
  content: LCDContent;
}

export interface BuzzerFeedbackPayload extends BuzzerFeedback {}

export interface SessionUpdatePayload extends ParkingSession {}

export interface StatsPayload {
  totalIn: number;
  totalOut: number;
  availableSlots: number;
  totalSlots: number;
  lastCost: number | null;
}

// ===== Commands (Dashboard -> Pi) =====
export type WSCommandType = 'open_gate' | 'close_gate' | 'update_settings';

export interface WSCommand {
  type: WSCommandType;
  payload: unknown;
}

export interface OpenGatePayload {
  gateType: GateType;
}

export interface UpdateSettingsPayload {
  costPerMinute?: number;
  parkingName?: string;
  wsUrl?: string;
}

// ===== App State =====
export interface ParkingAppState {
  connected: boolean;
  entryGate: GateState;
  exitGate: GateState;
  entryLCD: LCDContent;
  exitLCD: LCDContent;
  entryPlate: PlateResult | null;
  exitPlate: PlateResult | null;
  slots: ParkingSlot[];
  sessions: ParkingSession[];
  stats: StatsPayload;
  lastBuzzer: BuzzerFeedback | null;
}
