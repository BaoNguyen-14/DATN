"""
WebSocket Server chính trên Raspberry Pi.

Kết nối tất cả module:
  - RFID (2×RC522) → quẹt thẻ cổng vào/ra
  - PiCamera2      → chụp ảnh biển số
  - PlateProcessor  → xử lý nhận diện biển số (KNN)
  - Servo (2×)      → điều khiển thanh chắn
  - IR (2×)         → phát hiện xe qua thanh chắn
  - Buzzer          → phản hồi âm thanh
  - LCD (2×20x4)    → hiển thị thông tin
  - Webcam          → quét vùng bãi đậu

Giao tiếp WebSocket với Dashboard (React frontend).
"""

import asyncio
import json
import logging
import time
import os
import base64
from datetime import datetime
from typing import Optional, Dict, Set
import websockets
from websockets.server import WebSocketServerProtocol

# Import plate recognition
from plate_recognition import PlateProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger('ParkingServer')

# ============================================================
# CẤU HÌNH PHẦN CỨNG (GPIO PINS)
# ============================================================
SERVO_ENTRY_PIN = 12       # GPIO 12 (Hardware PWM0)
SERVO_EXIT_PIN = 13        # GPIO 13 (Hardware PWM1)
IR_ENTRY_PIN = 23          # GPIO 23 (LOW = có xe)
IR_EXIT_PIN = 24           # GPIO 24 (LOW = có xe)
BUZZER_PIN = 26            # GPIO 26

# RFID RC522 SPI
RFID_ENTRY_RST = 17        # RST pin cho RC522 cổng vào
RFID_EXIT_RST = 27         # RST pin cho RC522 cổng ra
# RC522 VÀO: SPI0-CE0 (GPIO8)
# RC522 RA:  SPI0-CE1 (GPIO7)

# LCD I2C
LCD_ENTRY_ADDR = 0x27      # I2C address LCD cổng vào
LCD_EXIT_ADDR = 0x20       # I2C address LCD cổng ra

# Thông số
BARRIER_CLOSE_DELAY = 4    # Thời gian chờ đóng thanh chắn (giây)
COST_PER_MINUTE = 1000     # Chi phí gửi xe (VNĐ/phút)

WS_HOST = '0.0.0.0'
WS_PORT = 8765

# ============================================================
# TRẠNG THÁI HỆ THỐNG
# ============================================================
class ParkingState:
    """Trạng thái toàn cục của hệ thống."""

    def __init__(self):
        self.total_in = 0
        self.total_out = 0
        self.available_slots = 8
        self.total_slots = 8
        self.last_cost: Optional[int] = None

        # Sessions: card_uid → session data
        self.active_sessions: Dict[str, dict] = {}

        # Gate states
        self.entry_servo_open = False
        self.exit_servo_open = False
        self.entry_ir_detected = False
        self.exit_ir_detected = False

        # Connected clients
        self.clients: Set[WebSocketServerProtocol] = set()


state = ParkingState()

# ============================================================
# PHẦN CỨNG (GPIO, SPI, I2C)
# ============================================================
HW_AVAILABLE = False
servo_entry = None
servo_exit = None
rfid_entry = None
rfid_exit = None
lcd_entry = None
lcd_exit = None

# Shared camera manager
camera_mgr = None

try:
    import RPi.GPIO as GPIO
    from mfrc522 import MFRC522
    from RPLCD.i2c import CharLCD

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Setup GPIO
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.setup(IR_ENTRY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(IR_EXIT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(SERVO_ENTRY_PIN, GPIO.OUT)
    GPIO.setup(SERVO_EXIT_PIN, GPIO.OUT)

    # PWM cho Servo
    servo_entry = GPIO.PWM(SERVO_ENTRY_PIN, 50)  # 50Hz
    servo_exit = GPIO.PWM(SERVO_EXIT_PIN, 50)
    servo_entry.start(0)
    servo_exit.start(0)

    # RFID - 2 đầu đọc RC522 trên SPI0
    # Cổng VÀO: SPI0-CE0 (GPIO8), RST=GPIO17
    rfid_entry = MFRC522(bus=0, device=0, pin_rst=RFID_ENTRY_RST)
    logger.info("✅ RC522 cổng VÀO (CE0, RST=GPIO17)")

    # Cổng RA: SPI0-CE1 (GPIO7), RST=GPIO27
    rfid_exit = MFRC522(bus=0, device=1, pin_rst=RFID_EXIT_RST)
    logger.info("✅ RC522 cổng RA (CE1, RST=GPIO27)")

    # LCD
    try:
        lcd_entry = CharLCD(i2c_expander='PCF8574', address=LCD_ENTRY_ADDR, port=1,
                            cols=20, rows=4, dotsize=8)
    except OSError:
        logger.warning(f"Không thể kết nối LCD cổng vào (I2C: 0x{LCD_ENTRY_ADDR:02X})")
        lcd_entry = None

    try:
        lcd_exit = CharLCD(i2c_expander='PCF8574', address=LCD_EXIT_ADDR, port=1,
                            cols=20, rows=4, dotsize=8)
    except OSError:
        logger.warning(f"Không thể kết nối LCD cổng ra (I2C: 0x{LCD_EXIT_ADDR:02X})")
        lcd_exit = None

    HW_AVAILABLE = True
    logger.info("Phần cứng GPIO/SPI/I2C khởi tạo thành công")

except Exception as e:
    logger.warning(f"Không khả dụng toàn bộ phần cứng GPIO: {e}")
    logger.warning("Chạy ở chế độ simulation (không có phần cứng)")
    HW_AVAILABLE = False


# ============================================================
# HÀM ĐIỀU KHIỂN PHẦN CỨNG
# ============================================================

def buzzer_beep(times: int, duration: float = 0.15, gap: float = 0.1):
    """Kêu buzzer số lần chỉ định."""
    if not HW_AVAILABLE:
        logger.info(f"[SIM] Buzzer: {times} beeps")
        return
    for i in range(times):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        if i < times - 1:
            time.sleep(gap)


def servo_set_angle(servo_pwm, angle: int):
    """Đặt góc servo (0=đóng, 90=mở)."""
    if servo_pwm is None:
        return
    duty = 2 + (angle / 18)
    servo_pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    servo_pwm.ChangeDutyCycle(0)  # Tắt PWM để tránh rung


def open_barrier(gate_type: str):
    """Mở thanh chắn."""
    if gate_type == 'entry':
        servo_set_angle(servo_entry, 90)
        state.entry_servo_open = True
    else:
        servo_set_angle(servo_exit, 90)
        state.exit_servo_open = True
    logger.info(f"[{gate_type.upper()}] Thanh chắn MỞ")


def close_barrier(gate_type: str):
    """Đóng thanh chắn."""
    if gate_type == 'entry':
        servo_set_angle(servo_entry, 0)
        state.entry_servo_open = False
    else:
        servo_set_angle(servo_exit, 0)
        state.exit_servo_open = False
    logger.info(f"[{gate_type.upper()}] Thanh chắn ĐÓNG")


def read_ir(gate_type: str) -> bool:
    """Đọc cảm biến IR. True = có xe."""
    if not HW_AVAILABLE:
        return False
    pin = IR_ENTRY_PIN if gate_type == 'entry' else IR_EXIT_PIN
    return GPIO.input(pin) == GPIO.LOW  # LOW = có xe


def lcd_display(gate_type: str, lines: list):
    """Hiển thị nội dung lên LCD 20×4."""
    lcd = lcd_entry if gate_type == 'entry' else lcd_exit
    if lcd is None:
        logger.info(f"[SIM] LCD {gate_type}: {lines}")
        return
    try:
        lcd.clear()
        for i, line in enumerate(lines[:4]):
            lcd.cursor_pos = (i, 0)
            lcd.write_string(line[:20].ljust(20))
    except Exception as e:
        logger.error(f"LCD error: {e}")


def rfid_read_card(gate_type: str) -> Optional[str]:
    """
    Đọc UID thẻ RFID.

    Returns:
        UID string (hex) hoặc None nếu không có thẻ
    """
    reader = rfid_entry if gate_type == 'entry' else rfid_exit
    if reader is None:
        return None

    try:
        (status, _) = reader.MFRC522_Request(reader.PICC_REQIDL)
        if status != reader.MI_OK:
            return None

        (status, uid) = reader.MFRC522_Anticoll()
        if status != reader.MI_OK:
            return None

        uid_str = ':'.join([f'{x:02X}' for x in uid[:4]])
        return uid_str

    except Exception as e:
        logger.error(f"[{gate_type.upper()}] RFID read error: {e}")
        return None


def rfid_write_plate(gate_type: str, plate_text: str) -> bool:
    """
    Ghi nội dung biển số vào thẻ RFID.

    Dùng ở cổng VÀO: lưu biển số vào thẻ.
    """
    reader = rfid_entry if gate_type == 'entry' else rfid_exit
    if reader is None:
        logger.info(f"[SIM] RFID write: {plate_text}")
        return True

    try:
        # Authenticate block 8 (sector 2, block 0)
        key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
        (status, _) = reader.MFRC522_Anticoll()
        reader.MFRC522_SelectTag(_)

        status = reader.MFRC522_Auth(reader.PICC_AUTHENT1A, 8, key, _)
        if status != reader.MI_OK:
            logger.error("RFID auth failed")
            return False

        # Encode biển số thành 16 bytes
        data = list(plate_text.encode('ascii')[:16].ljust(16, b'\x00'))
        reader.MFRC522_Write(8, data)
        reader.MFRC522_StopCrypto1()

        logger.info(f"RFID write thành công: {plate_text}")
        return True

    except Exception as e:
        logger.error(f"RFID write error: {e}")
        return False


def rfid_read_plate(gate_type: str) -> Optional[str]:
    """
    Đọc nội dung biển số từ thẻ RFID.

    Dùng ở cổng RA: đọc biển số từ thẻ để so sánh.
    """
    reader = rfid_entry if gate_type == 'entry' else rfid_exit
    if reader is None:
        return None

    try:
        key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
        (status, uid) = reader.MFRC522_Anticoll()
        reader.MFRC522_SelectTag(uid)

        status = reader.MFRC522_Auth(reader.PICC_AUTHENT1A, 8, key, uid)
        if status != reader.MI_OK:
            return None

        data = reader.MFRC522_Read(8)
        reader.MFRC522_StopCrypto1()

        if data:
            plate = bytes(data).decode('ascii').strip('\x00')
            return plate

        return None

    except Exception as e:
        logger.error(f"RFID read plate error: {e}")
        return None


# ============================================================
# WEBSOCKET BROADCAST
# ============================================================

async def broadcast(message: dict):
    """Gửi message đến tất cả clients."""
    if not state.clients:
        return
    msg = json.dumps(message)
    disconnected = set()
    for client in state.clients:
        try:
            await client.send(msg)
        except websockets.exceptions.ConnectionClosed:
            disconnected.add(client)
    state.clients -= disconnected


async def send_gate_status(gate_type: str):
    """Gửi trạng thái cổng."""
    is_entry = gate_type == 'entry'
    await broadcast({
        'type': 'gate_status',
        'payload': {
            'gateType': gate_type,
            'servo': 'open' if (state.entry_servo_open if is_entry else state.exit_servo_open) else 'closed',
            'ir': 'detected' if (state.entry_ir_detected if is_entry else state.exit_ir_detected) else 'clear',
            'rfidReady': True,
            'lastCardUID': None,
            'barrierCountdown': None,
        },
        'timestamp': datetime.now().isoformat(),
    })


async def send_lcd_update(gate_type: str, lines: list):
    """Gửi nội dung LCD lên dashboard."""
    await broadcast({
        'type': 'lcd_update',
        'payload': {
            'gateType': gate_type,
            'content': {
                'line1': lines[0] if len(lines) > 0 else '',
                'line2': lines[1] if len(lines) > 1 else '',
                'line3': lines[2] if len(lines) > 2 else '',
                'line4': lines[3] if len(lines) > 3 else '',
            },
        },
        'timestamp': datetime.now().isoformat(),
    })


async def send_stats():
    """Gửi thống kê tổng quan."""
    await broadcast({
        'type': 'stats_update',
        'payload': {
            'totalIn': state.total_in,
            'totalOut': state.total_out,
            'availableSlots': state.available_slots,
            'totalSlots': state.total_slots,
            'lastCost': state.last_cost,
        },
        'timestamp': datetime.now().isoformat(),
    })


async def send_plate_result(gate_type: str, result, plate_image_url: str):
    """Gửi kết quả nhận diện biển số."""
    await broadcast({
        'type': 'plate_recognized',
        'payload': {
            'plateText': result.plate_text,
            'imageUrl': plate_image_url,
            'timestamp': result.timestamp,
            'confidence': result.confidence,
            'gateType': gate_type,
        },
        'timestamp': datetime.now().isoformat(),
    })


async def send_buzzer(gate_type: str, buzzer_type: str):
    """Gửi trạng thái buzzer."""
    await broadcast({
        'type': 'buzzer_feedback',
        'payload': {
            'type': buzzer_type,
            'gateType': gate_type,
            'timestamp': datetime.now().isoformat(),
        },
        'timestamp': datetime.now().isoformat(),
    })


async def send_session_update(session: dict):
    """Gửi cập nhật phiên đậu xe."""
    await broadcast({
        'type': 'session_update',
        'payload': session,
        'timestamp': datetime.now().isoformat(),
    })


# ============================================================
# LUỒNG XỬ LÝ CHÍNH
# ============================================================

plate_processor: Optional[PlateProcessor] = None


async def handle_entry_rfid(card_uid: str):
    """
    Xử lý khi quẹt thẻ RFID ở CỔNG VÀO.

    Flow:
    1. Quẹt thẻ → nhận UID
    2. Chụp ảnh PiCamera → xử lý biển số KNN
    3. Nếu nhận diện thành công:
       - Buzzer 2 tít
       - Ghi biển số vào thẻ
       - LCD: "MOI XE VAO", biển số, thời gian
       - Gửi kết quả lên Dashboard
       - Chờ người dùng bấm nút mở thanh chắn trên web
    4. Nếu thất bại:
       - Buzzer 3 tít
       - LCD: "LOI NHAN DIEN"
    """
    now = datetime.now()
    time_str = now.strftime('%H:%M:%S')

    logger.info(f"[ENTRY] Thẻ quẹt: {card_uid}")

    # Gửi sự kiện quẹt thẻ
    await broadcast({
        'type': 'rfid_scanned',
        'payload': {'gateType': 'entry', 'cardUID': card_uid},
        'timestamp': now.isoformat(),
    })

    # LCD: Đang xử lý
    lcd_lines = ['     CONG VAO       ', f'Thoi gian: {time_str}', 'Bien so xe: ...     ', 'Trang thai: XU LY  ']
    lcd_display('entry', lcd_lines)
    await send_lcd_update('entry', lcd_lines)

    # Chụp và xử lý biển số
    if plate_processor:
        result = plate_processor.capture_and_process(gate_type='entry')
    else:
        # Simulation
        result = type('R', (), {
            'success': True, 'plate_text': '51G-888.88',
            'confidence': 92.5, 'plate_image_path': '',
            'timestamp': now.isoformat()
        })()

    if result.success:
        # === THÀNH CÔNG ===
        plate_text = result.plate_text

        # Buzzer 2 tít
        buzzer_beep(2)
        await send_buzzer('entry', 'success')

        # Ghi biển số vào thẻ RFID
        rfid_write_plate('entry', plate_text)

        # Cập nhật LCD
        lcd_lines = [
            '     CONG VAO       ',
            f'Thoi gian: {time_str}',
            f'Bien so: {plate_text[:11].ljust(11)}',
            'Trang thai: MOI VAO '
        ]
        lcd_display('entry', lcd_lines)
        await send_lcd_update('entry', lcd_lines)

        # Gửi kết quả lên Dashboard
        plate_image_url = f'/captures/{os.path.basename(result.plate_image_path)}' if result.plate_image_path else ''
        await send_plate_result('entry', result, plate_image_url)

        # Tạo session
        session_id = f"S{now.strftime('%Y%m%d%H%M%S')}_{card_uid.replace(':', '')}"
        session = {
            'id': session_id,
            'cardUID': card_uid,
            'plateIn': plate_text,
            'plateOut': None,
            'plateImageIn': plate_image_url,
            'plateImageOut': None,
            'timeIn': now.isoformat(),
            'timeOut': None,
            'durationMinutes': None,
            'cost': None,
            'matched': None,
        }
        state.active_sessions[card_uid] = session
        state.total_in += 1
        state.available_slots = max(0, state.available_slots - 1)

        await send_session_update(session)
        await send_stats()

        logger.info(f"[ENTRY] Thành công: {plate_text} ({result.confidence}%)")

    else:
        # === THẤT BẠI ===
        buzzer_beep(3)
        await send_buzzer('entry', 'error')

        lcd_lines = [
            '     CONG VAO       ',
            f'Thoi gian: {time_str}',
            'Bien so: LOI        ',
            'Trang thai: THU LAI '
        ]
        lcd_display('entry', lcd_lines)
        await send_lcd_update('entry', lcd_lines)

        logger.warning(f"[ENTRY] Thất bại: {result.error}")


async def handle_exit_rfid(card_uid: str):
    """
    Xử lý khi quẹt thẻ RFID ở CỔNG RA.

    Flow:
    1. Quẹt thẻ → nhận UID
    2. Đọc biển số từ thẻ (đã lưu lúc vào)
    3. Chụp ảnh PiCamera → xử lý biển số KNN
    4. So sánh biển số trong thẻ vs biển số vừa chụp:
       - Khớp: Buzzer 2 tít, LCD hiển thị chi phí
       - Không khớp: Buzzer 3 tít, LCD hiển thị "LOI"
    5. Chờ người dùng bấm nút mở thanh chắn trên web
    """
    now = datetime.now()
    time_str = now.strftime('%H:%M:%S')

    logger.info(f"[EXIT] Thẻ quẹt: {card_uid}")

    # Gửi sự kiện quẹt thẻ
    await broadcast({
        'type': 'rfid_scanned',
        'payload': {'gateType': 'exit', 'cardUID': card_uid},
        'timestamp': now.isoformat(),
    })

    # LCD: Đang xử lý
    lcd_lines = ['      CONG RA       ', f'Thoi gian: {time_str}', 'Bien so xe: ...     ', 'Trang thai: XU LY  ']
    lcd_display('exit', lcd_lines)
    await send_lcd_update('exit', lcd_lines)

    # Đọc biển số từ thẻ (đã ghi lúc vào)
    plate_from_card = rfid_read_plate('exit')
    if plate_from_card is None and card_uid in state.active_sessions:
        plate_from_card = state.active_sessions[card_uid].get('plateIn', '')

    # Chụp và xử lý biển số hiện tại
    if plate_processor:
        result = plate_processor.capture_and_process(gate_type='exit')
    else:
        result = type('R', (), {
            'success': True, 'plate_text': plate_from_card or '51G-888.88',
            'confidence': 90.0, 'plate_image_path': '',
            'timestamp': now.isoformat()
        })()

    if not result.success:
        buzzer_beep(3)
        await send_buzzer('exit', 'error')

        lcd_lines = [
            '      CONG RA       ',
            f'Thoi gian: {time_str}',
            'Bien so: LOI        ',
            'Trang thai: THU LAI '
        ]
        lcd_display('exit', lcd_lines)
        await send_lcd_update('exit', lcd_lines)
        return

    plate_current = result.plate_text

    # Gửi kết quả nhận diện lên Dashboard
    plate_image_url = f'/captures/{os.path.basename(result.plate_image_path)}' if result.plate_image_path else ''
    await send_plate_result('exit', result, plate_image_url)

    # === SO SÁNH BIỂN SỐ ===
    is_matched = plate_from_card and plate_current and plate_from_card.replace(' ', '') == plate_current.replace(' ', '')

    if is_matched:
        # === KHỚP ===
        buzzer_beep(2)
        await send_buzzer('exit', 'success')

        # Tính chi phí
        session = state.active_sessions.get(card_uid)
        duration_minutes = 0
        cost = 0

        if session:
            time_in = datetime.fromisoformat(session['timeIn'])
            duration = now - time_in
            duration_minutes = int(duration.total_seconds() / 60)
            cost = max(COST_PER_MINUTE, duration_minutes * COST_PER_MINUTE)

        # LCD hiển thị chi phí
        cost_str = f'{cost:,}'.replace(',', '.')
        lcd_lines = [
            '      CONG RA       ',
            f'Thoi gian: {time_str}',
            f'Bien so: {plate_current[:11].ljust(11)}',
            f'Phi: {cost_str} VND    '[:20]
        ]
        lcd_display('exit', lcd_lines)
        await send_lcd_update('exit', lcd_lines)

        # Cập nhật session
        if session:
            session['plateOut'] = plate_current
            session['plateImageOut'] = plate_image_url
            session['timeOut'] = now.isoformat()
            session['durationMinutes'] = duration_minutes
            session['cost'] = cost
            session['matched'] = True
            await send_session_update(session)

        state.total_out += 1
        state.available_slots = min(state.total_slots, state.available_slots + 1)
        state.last_cost = cost
        await send_stats()

        logger.info(f"[EXIT] Khớp! {plate_current} = {plate_from_card}, Chi phí: {cost} VNĐ ({duration_minutes} phút)")

    else:
        # === KHÔNG KHỚP ===
        buzzer_beep(3)
        await send_buzzer('exit', 'error')

        lcd_lines = [
            '      CONG RA       ',
            f'Thoi gian: {time_str}',
            f'Bien so: {plate_current[:11].ljust(11)}',
            'Trang thai: LOI     '
        ]
        lcd_display('exit', lcd_lines)
        await send_lcd_update('exit', lcd_lines)

        # Cập nhật session
        session = state.active_sessions.get(card_uid)
        if session:
            session['plateOut'] = plate_current
            session['matched'] = False
            await send_session_update(session)

        logger.warning(f"[EXIT] Không khớp! Thẻ: {plate_from_card}, Camera: {plate_current}")


async def handle_barrier_auto_close(gate_type: str):
    """
    Theo dõi IR sensor và tự đóng thanh chắn sau 4 giây
    khi xe đã đi qua.
    """
    logger.info(f"[{gate_type.upper()}] Bắt đầu theo dõi IR...")

    # Gửi countdown
    for remaining in range(BARRIER_CLOSE_DELAY, 0, -1):
        # Kiểm tra IR mỗi giây
        ir_detected = read_ir(gate_type)
        if gate_type == 'entry':
            state.entry_ir_detected = ir_detected
        else:
            state.exit_ir_detected = ir_detected

        if ir_detected:
            # Xe vẫn đang ở thanh chắn → reset countdown
            logger.info(f"[{gate_type.upper()}] IR detected, chờ xe qua...")
            await send_gate_status(gate_type)
            await asyncio.sleep(1)
            return await handle_barrier_auto_close(gate_type)  # Restart countdown

        # Broadcast countdown
        await broadcast({
            'type': 'gate_status',
            'payload': {
                'gateType': gate_type,
                'servo': 'open',
                'ir': 'clear',
                'rfidReady': True,
                'lastCardUID': None,
                'barrierCountdown': remaining,
            },
            'timestamp': datetime.now().isoformat(),
        })
        await asyncio.sleep(1)

    # Đóng thanh chắn
    close_barrier(gate_type)
    await send_gate_status(gate_type)

    # Reset LCD
    if gate_type == 'entry':
        lcd_lines = ['     CONG VAO       ', 'Thoi gian:          ', 'Bien so xe:         ', 'Trang thai: SAN SANG']
    else:
        lcd_lines = ['      CONG RA       ', 'Thoi gian:          ', 'Bien so xe:         ', 'Trang thai: SAN SANG']
    lcd_display(gate_type, lcd_lines)
    await send_lcd_update(gate_type, lcd_lines)

    logger.info(f"[{gate_type.upper()}] Thanh chắn đã đóng")


# ============================================================
# WEBSOCKET HANDLER
# ============================================================

async def ws_handler(websocket: WebSocketServerProtocol):
    """Xử lý kết nối WebSocket từ Dashboard."""
    state.clients.add(websocket)
    client_addr = websocket.remote_address
    logger.info(f"Client kết nối: {client_addr}")

    # Gửi ACK
    await websocket.send(json.dumps({
        'type': 'connection_ack',
        'payload': {'message': 'Connected to Smart Parking Pi'},
        'timestamp': datetime.now().isoformat(),
    }))

    # Gửi trạng thái hiện tại
    await send_stats()
    await send_gate_status('entry')
    await send_gate_status('exit')

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                cmd_type = data.get('type')
                payload = data.get('payload', {})

                if cmd_type == 'open_gate':
                    gate_type = payload.get('gateType', 'entry')
                    open_barrier(gate_type)
                    await send_gate_status(gate_type)
                    # Bắt đầu theo dõi auto-close
                    asyncio.create_task(handle_barrier_auto_close(gate_type))

                elif cmd_type == 'update_settings':
                    global COST_PER_MINUTE
                    if 'costPerMinute' in payload:
                        COST_PER_MINUTE = payload['costPerMinute']
                        logger.info(f"Cập nhật phí: {COST_PER_MINUTE} VNĐ/phút")

                else:
                    logger.warning(f"Unknown command: {cmd_type}")

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON: {message}")

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        state.clients.discard(websocket)
        logger.info(f"Client ngắt kết nối: {client_addr}")


# ============================================================
# RFID POLLING LOOP
# ============================================================

async def rfid_polling_loop():
    """Liên tục poll RFID readers để phát hiện thẻ quẹt."""
    logger.info("RFID polling started")

    while True:
        # Poll cổng VÀO (RC522 #1 trên SPI0-CE0)
        card_uid = rfid_read_card('entry')
        if card_uid:
            await handle_entry_rfid(card_uid)
            await asyncio.sleep(2)  # Debounce

        # Poll cổng RA (RC522 #2 trên SPI0-CE1)
        card_uid_exit = rfid_read_card('exit')
        if card_uid_exit:
            await handle_exit_rfid(card_uid_exit)
            await asyncio.sleep(2)  # Debounce

        await asyncio.sleep(0.2)  # 5 lần/giây


# ============================================================
# IR POLLING LOOP
# ============================================================

async def ir_polling_loop():
    """Liên tục đọc cảm biến IR."""
    while True:
        entry_ir = read_ir('entry')
        exit_ir = read_ir('exit')

        if entry_ir != state.entry_ir_detected:
            state.entry_ir_detected = entry_ir
            await send_gate_status('entry')

        if exit_ir != state.exit_ir_detected:
            state.exit_ir_detected = exit_ir
            await send_gate_status('exit')

        await asyncio.sleep(0.1)


from zone_scanner import ZoneScanner

async def on_slot_change(all_statuses):
    await broadcast({
        'type': 'slot_update',
        'payload': {'slots': all_statuses},
        'timestamp': datetime.now().isoformat(),
    })

# ============================================================
# MAIN
# ============================================================

async def main():
    global plate_processor, camera_mgr

    logger.info("=" * 60)
    logger.info("  HỆ THỐNG BÃI ĐẬU XE THÔNG MINH")
    logger.info("  Raspberry Pi 4 (4GB)")
    logger.info("=" * 60)

    # ── Khởi tạo shared PiCamera2 ──────────────────────────────
    if HW_AVAILABLE:
        try:
            from camera_manager import init_camera
            camera_mgr = init_camera()
            logger.info("✅ Shared CameraManager khởi tạo thành công")
        except Exception as e:
            logger.warning(f"Không thể khởi tạo CameraManager: {e}")
            camera_mgr = None
    else:
        camera_mgr = None

    # ── Khởi tạo PlateProcessor (dùng shared camera) ──────────
    plate_processor = PlateProcessor(
        model_path='knn_plate_model.pkl',
        output_dir='captures',
        camera_manager=camera_mgr,
        debug=False,
    )

    if plate_processor.init():
        logger.info("✅ PlateProcessor khởi tạo thành công")
    else:
        logger.warning("PlateProcessor khởi tạo thất bại, chạy ở chế độ simulation")
        plate_processor = None

    # Reset LCD
    lcd_display('entry', ['     CONG VAO       ', 'Thoi gian:          ', 'Bien so xe:         ', 'Trang thai: SAN SANG'])
    lcd_display('exit',  ['      CONG RA       ', 'Thoi gian:          ', 'Bien so xe:         ', 'Trang thai: SAN SANG'])

    # ── Start MJPEG streaming server (dùng shared camera) ─────
    try:
        from mjpeg_server import start_mjpeg_thread
        from webcam_manager import init_webcam
        
        # Khởi tạo webcam ở đây
        init_webcam(0)
        
        start_mjpeg_thread(host='0.0.0.0', port=8080, camera_manager=camera_mgr)
        logger.info("✅ MJPEG streaming server đã khởi động trên port 8080")
    except Exception as e:
        logger.warning(f"Không thể khởi động MJPEG server: {e}")

    # ── Start WebSocket server ────────────────────────────────
    logger.info(f"WebSocket server starting on ws://{WS_HOST}:{WS_PORT}")

    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        # Chạy song song: WebSocket server + RFID polling + IR polling
        # Khởi động ZoneScanner với kiến trúc 2 thread (Camera + Detector)
        # Warm-up tự động 45 frames — không cần calibrate() thủ công
        loop = asyncio.get_running_loop()
        scanner = ZoneScanner(on_status_change=on_slot_change)
        scanner.start(loop=loop)

        tasks = [
            asyncio.create_task(rfid_polling_loop()),
            asyncio.create_task(ir_polling_loop()),
        ]

        logger.info("🚀 Hệ thống sẵn sàng!")
        await asyncio.gather(*tasks)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        if HW_AVAILABLE:
            GPIO.cleanup()
        if plate_processor:
            plate_processor.cleanup()
        if camera_mgr:
            camera_mgr.cleanup()
