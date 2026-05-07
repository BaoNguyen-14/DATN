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
import csv
from datetime import datetime
from typing import Optional, Dict, Set
import pigpio
import websockets
from websockets.server import WebSocketServerProtocol

# Import plate recognition
from plate_recognition import PlateProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger('ParkingServer')

# ============================================================
# CẤU HÌNH PHẦN CỨNG (GPIO PINS)
# ============================================================
SERVO_ENTRY_PIN = 23
SERVO_EXIT_PIN = 24
IR_ENTRY_PIN = 14
IR_EXIT_PIN = 15
BUZZER_PIN = 26

# RFID RC522 SPI
RFID_ENTRY_RST = 17
RFID_EXIT_RST = 27
# RC522 VÀO: SPI0-CE0 (GPIO8)
# RC522 RA:  SPI0-CE1 (GPIO7)

# LCD I2C
LCD_ENTRY_ADDR = 0x27
LCD_EXIT_ADDR = 0x20
LCD_INFO_ADDR = 0x25  # LCD 16x2 hiển thị số chỗ trống

# ============================================================
# HIỆU CHỈNH SERVO (CALIBRATION)
# ============================================================
SERVO_ENTRY_OFFSET = -15   # độ bù góc cổng VÀO
SERVO_EXIT_OFFSET  = 0     # độ bù góc cổng RA

SERVO_CLOSE_ANGLE = 0
SERVO_OPEN_ANGLE  = 90

SERVO_MOVE_TIME     = 1.1   # giây chờ servo di chuyển đến đích
SERVO_HOLD_TIME     = 0.35  # giây giữ để servo settle trước khi tắt PWM
SERVO_DEBOUNCE_TIME = 1.8   # giây tối thiểu giữa 2 lệnh servo (chống double-trigger)

BARRIER_CLOSE_DELAY = 4
COST_PER_MINUTE = 1000

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
        
        # History
        self.history_sessions = []

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
# pigpio instance – DMA hardware PWM, không bị preempt bởi OS scheduler
pi_gpio = None
rfid_entry = None
rfid_exit = None
lcd_entry = None
lcd_exit = None
lcd_info = None

# Lock bảo vệ servo – tránh 2 lệnh pigpio chồng nhau
servo_entry_lock = asyncio.Lock()
servo_exit_lock  = asyncio.Lock()

# Debounce: timestamp lần gửi lệnh servo gần nhất, key = GPIO pin number
_servo_last_cmd_time: dict = {}   # pin → float (monotonic timestamp)

# Shared camera manager
camera_mgr = None

try:
    import RPi.GPIO as GPIO
    from mfrc522 import MFRC522
    from RPLCD.i2c import CharLCD

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Setup GPIO (Buzzer + IR – vẫn dùng RPi.GPIO)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.setup(IR_ENTRY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(IR_EXIT_PIN,  GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # ── pigpio: DMA hardware PWM cho Servo ────────────────────
    try:
        pi_gpio = pigpio.pi()
        if not pi_gpio.connected:
            raise RuntimeError("pigpio daemon chưa chạy – hãy chạy: sudo pigpiod")

        def _boot_pulse(angle_deg, offset):
            a = max(0.0, min(180.0, float(angle_deg + offset)))
            return max(500, min(2500, int(500 + (a / 180.0) * 2000)))

        pi_gpio.set_servo_pulsewidth(SERVO_ENTRY_PIN, _boot_pulse(SERVO_CLOSE_ANGLE, SERVO_ENTRY_OFFSET))
        pi_gpio.set_servo_pulsewidth(SERVO_EXIT_PIN,  _boot_pulse(SERVO_CLOSE_ANGLE, SERVO_EXIT_OFFSET))
        time.sleep(SERVO_MOVE_TIME + SERVO_HOLD_TIME)
        pi_gpio.set_servo_pulsewidth(SERVO_ENTRY_PIN, 0)
        pi_gpio.set_servo_pulsewidth(SERVO_EXIT_PIN,  0)
        logger.info("✅ Servo (pigpio DMA) đã về vị trí đóng")
    except Exception as _servo_err:
        logger.warning(f"⚠️  pigpio/Servo không khả dụng: {_servo_err}")
        pi_gpio = None

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

    try:
        lcd_info = CharLCD(i2c_expander='PCF8574', address=LCD_INFO_ADDR, port=1,
                            cols=16, rows=2, dotsize=8)
    except OSError:
        logger.warning(f"Không thể kết nối LCD thông tin (I2C: 0x{LCD_INFO_ADDR:02X})")
        lcd_info = None

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
    """Kêu buzzer số lần chỉ định (blocking – gọi từ thread riêng)."""
    if not HW_AVAILABLE:
        logger.info(f"[SIM] Buzzer: {times} beeps")
        return
    for i in range(times):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        if i < times - 1:
            time.sleep(gap)


async def buzzer_beep_async(times: int, duration: float = 0.15, gap: float = 0.1):
    """Kêu buzzer bất đồng bộ – không block event loop."""
    await asyncio.to_thread(buzzer_beep, times, duration, gap)


async def lcd_display_async(gate_type: str, lines: list):
    """Ghi LCD bất đồng bộ – không block event loop."""
    await asyncio.to_thread(lcd_display, gate_type, lines)


def set_servo_angle(pin: int, angle: int, offset: int = 0):
    """
    Điều khiển servo bằng pigpio DMA hardware PWM (blocking).

    - Tính pulsewidth từ góc + offset hiệu chỉnh.
    - Debounce per-pin: bỏ qua nếu lệnh đến quá sát lệnh trước.
    - Gửi xung → chờ servo đến vị trí → settle → tắt xung.

    Pulse SG90: 0° = 500µs, 90° = 1500µs, 180° = 2500µs
    """
    if pi_gpio is None or not pi_gpio.connected:
        logger.info(f"[SIM] Servo GPIO{pin} → {angle}° (offset {offset:+d})")
        return

    now = time.monotonic()
    if now - _servo_last_cmd_time.get(pin, 0.0) < SERVO_DEBOUNCE_TIME:
        logger.debug(f"[SERVO] Debounce bỏ qua lệnh GPIO{pin}")
        return
    _servo_last_cmd_time[pin] = now

    clamped = max(0.0, min(180.0, float(angle + offset)))
    pulse = max(500, min(2500, int(500 + (clamped / 180.0) * 2000)))

    try:
        pi_gpio.set_servo_pulsewidth(pin, pulse)
        time.sleep(SERVO_MOVE_TIME)
        time.sleep(SERVO_HOLD_TIME)
        pi_gpio.set_servo_pulsewidth(pin, 0)   # tắt PWM sau khi servo ổn định
        logger.debug(f"Servo GPIO{pin} → {angle}° (offset {offset:+d}) | {pulse}µs")
    except Exception as e:
        logger.error(f"Servo GPIO{pin} error: {e}")


async def open_barrier_async(gate_type: str):
    """Mở thanh chắn bất đồng bộ, có lock + guard chống double-open."""
    lock = servo_entry_lock if gate_type == 'entry' else servo_exit_lock
    async with lock:
        already_open = state.entry_servo_open if gate_type == 'entry' else state.exit_servo_open
        if already_open:
            logger.debug(f"[{gate_type.upper()}] open_barrier_async bỏ qua – đã mở")
            return
        pin    = SERVO_ENTRY_PIN    if gate_type == 'entry' else SERVO_EXIT_PIN
        offset = SERVO_ENTRY_OFFSET if gate_type == 'entry' else SERVO_EXIT_OFFSET
        await asyncio.to_thread(set_servo_angle, pin, SERVO_OPEN_ANGLE, offset)
        if gate_type == 'entry':
            state.entry_servo_open = True
        else:
            state.exit_servo_open = True
        logger.info(f"[{gate_type.upper()}] Thanh chắn MỞ")


async def close_barrier_async(gate_type: str):
    """Đóng thanh chắn bất đồng bộ, có lock + guard chống double-close."""
    lock = servo_entry_lock if gate_type == 'entry' else servo_exit_lock
    async with lock:
        already_closed = not (state.entry_servo_open if gate_type == 'entry' else state.exit_servo_open)
        if already_closed:
            logger.debug(f"[{gate_type.upper()}] close_barrier_async bỏ qua – đã đóng")
            return
        pin    = SERVO_ENTRY_PIN    if gate_type == 'entry' else SERVO_EXIT_PIN
        offset = SERVO_ENTRY_OFFSET if gate_type == 'entry' else SERVO_EXIT_OFFSET
        await asyncio.to_thread(set_servo_angle, pin, SERVO_CLOSE_ANGLE, offset)
        if gate_type == 'entry':
            state.entry_servo_open = False
        else:
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


def update_lcd_info(available, total):
    """Hiển thị số chỗ trống lên LCD 16x2."""
    if lcd_info is None:
        logger.info(f"[SIM] LCD INFO: Cho trong: {available}/{total}")
        return
    try:
        lcd_info.clear()
        lcd_info.cursor_pos = (0, 0)
        lcd_info.write_string("BAI DAU XE DATN ")
        lcd_info.cursor_pos = (1, 0)
        lcd_info.write_string(f"Cho trong: {available}/{total}".ljust(16))
    except Exception as e:
        logger.error(f"LCD INFO error: {e}")

async def update_lcd_info_async(available, total):
    await asyncio.to_thread(update_lcd_info, available, total)


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


async def send_plate_result(gate_type: str, result, plate_image_url: str, full_image_url: str):
    """Gửi kết quả nhận diện biển số."""
    await broadcast({
        'type': 'plate_recognized',
        'payload': {
            'plateText': result.plate_text,
            'imageUrl': plate_image_url,
            'fullImageUrl': full_image_url,
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

    # Gửi sự kiện quẹt thẻ ngay lập tức
    await broadcast({
        'type': 'rfid_scanned',
        'payload': {'gateType': 'entry', 'cardUID': card_uid},
        'timestamp': now.isoformat(),
    })

    # LCD "XU LY" + broadcast song song (không đợi LCD xong)
    lcd_processing = ['     CONG VAO       ', f'Thoi gian: {time_str}', 'Bien so xe: ...     ', 'Trang thai: XU LY  ']
    asyncio.create_task(lcd_display_async('entry', lcd_processing))
    await send_lcd_update('entry', lcd_processing)

    # Chụp và xử lý biển số trong thread riêng (không block event loop)
    if plate_processor:
        result = await asyncio.to_thread(plate_processor.capture_and_process, 'entry')
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

        # Cập nhật LCD kết quả
        lcd_lines = [
            '     CONG VAO       ',
            f'Thoi gian: {time_str}',
            f'Bien so: {plate_text[:11].ljust(11)}',
            'Trang thai: MOI VAO '
        ]

        # Broadcast lên web TRƯỚC (không đợi buzzer/LCD)
        await send_buzzer('entry', 'success')
        await send_lcd_update('entry', lcd_lines)

        # Chạy buzzer + LCD song song trong background (không block web)
        asyncio.create_task(buzzer_beep_async(2))
        asyncio.create_task(lcd_display_async('entry', lcd_lines))

        # Ghi biển số vào thẻ RFID trong thread riêng
        asyncio.create_task(asyncio.to_thread(rfid_write_plate, 'entry', plate_text))

        # Gửi kết quả lên Dashboard
        plate_image_url = f'/captures/{os.path.basename(result.plate_image_path)}' if result.plate_image_path else ''
        full_image_url = f'/captures/{os.path.basename(result.full_image_path)}' if result.full_image_path else ''
        await send_plate_result('entry', result, plate_image_url, full_image_url)

        # Tạo session
        session_id = f"S{now.strftime('%Y%m%d%H%M%S')}_{card_uid.replace(':', '')}"
        session = {
            'id': session_id,
            'cardUID': card_uid,
            'plateIn': plate_text,
            'plateOut': None,
            'plateImageIn': plate_image_url,
            'fullImageIn': full_image_url,
            'plateImageOut': None,
            'fullImageOut': None,
            'timeIn': now.isoformat(),
            'timeOut': None,
            'durationMinutes': None,
            'cost': None,
            'matched': None,
        }
        state.active_sessions[card_uid] = session
        state.history_sessions.append(session)
        state.total_in += 1
        state.available_slots = max(0, state.available_slots - 1)

        await send_session_update(session)
        await send_stats()

        logger.info(f"[ENTRY] Thành công: {plate_text} ({result.confidence}%)")

    else:
        # === THẤT BẠI ===
        # Broadcast web TRƯỚC, buzzer/LCD chạy background
        await send_buzzer('entry', 'error')
        lcd_lines = [
            '     CONG VAO       ',
            f'Thoi gian: {time_str}',
            'Bien so: LOI        ',
            'Trang thai: THU LAI '
        ]
        await send_lcd_update('entry', lcd_lines)
        asyncio.create_task(buzzer_beep_async(3))
        asyncio.create_task(lcd_display_async('entry', lcd_lines))

        logger.warning(f"[ENTRY] Thất bại: {getattr(result, 'error', 'unknown')}")


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

    # Gửi sự kiện quẹt thẻ ngay lập tức
    await broadcast({
        'type': 'rfid_scanned',
        'payload': {'gateType': 'exit', 'cardUID': card_uid},
        'timestamp': now.isoformat(),
    })

    # LCD "XU LY" chạy background, broadcast web ngay
    lcd_processing = ['      CONG RA       ', f'Thoi gian: {time_str}', 'Bien so xe: ...     ', 'Trang thai: XU LY  ']
    asyncio.create_task(lcd_display_async('exit', lcd_processing))
    await send_lcd_update('exit', lcd_processing)

    # Đọc biển số từ thẻ và chụp ảnh song song
    plate_from_card = await asyncio.to_thread(rfid_read_plate, 'exit')
    if plate_from_card is None and card_uid in state.active_sessions:
        plate_from_card = state.active_sessions[card_uid].get('plateIn', '')

    # Chụp và xử lý biển số trong thread riêng
    if plate_processor:
        result = await asyncio.to_thread(plate_processor.capture_and_process, 'exit')
    else:
        result = type('R', (), {
            'success': True, 'plate_text': plate_from_card or '51G-888.88',
            'confidence': 90.0, 'plate_image_path': '',
            'timestamp': now.isoformat()
        })()

    if not result.success:
        # Broadcast web TRƯỚC, buzzer/LCD background
        await send_buzzer('exit', 'error')
        lcd_lines = [
            '      CONG RA       ',
            f'Thoi gian: {time_str}',
            'Bien so: LOI        ',
            'Trang thai: THU LAI '
        ]
        await send_lcd_update('exit', lcd_lines)
        asyncio.create_task(buzzer_beep_async(3))
        asyncio.create_task(lcd_display_async('exit', lcd_lines))
        return

    plate_current = result.plate_text

    # Gửi kết quả nhận diện lên Dashboard
    plate_image_url = f'/captures/{os.path.basename(result.plate_image_path)}' if result.plate_image_path else ''
    full_image_url = f'/captures/{os.path.basename(result.full_image_path)}' if result.full_image_path else ''
    await send_plate_result('exit', result, plate_image_url, full_image_url)

    # === SO SÁNH BIỂN SỐ ===
    is_matched = plate_from_card and plate_current and plate_from_card.replace(' ', '') == plate_current.replace(' ', '')

    if is_matched:
        # === KHỚP ===
        session = state.active_sessions.get(card_uid)
        duration_minutes = 0
        cost = 0

        if session:
            time_in = datetime.fromisoformat(session['timeIn'])
            duration = now - time_in
            duration_minutes = int(duration.total_seconds() / 60)
            cost = max(COST_PER_MINUTE, duration_minutes * COST_PER_MINUTE)

        cost_str = f'{cost:,}'.replace(',', '.')
        lcd_lines = [
            '      CONG RA       ',
            f'Thoi gian: {time_str}',
            f'Bien so: {plate_current[:11].ljust(11)}',
            f'Phi: {cost_str} VND    '[:20]
        ]

        # Broadcast web TRƯỚC, buzzer/LCD chạy background
        await send_buzzer('exit', 'success')
        await send_lcd_update('exit', lcd_lines)
        asyncio.create_task(buzzer_beep_async(2))
        asyncio.create_task(lcd_display_async('exit', lcd_lines))

        # Cập nhật session
        if session:
            session['plateOut'] = plate_current
            session['plateImageOut'] = plate_image_url
            session['fullImageOut'] = full_image_url
            session['timeOut'] = now.isoformat()
            session['durationMinutes'] = duration_minutes
            session['cost'] = cost
            session['matched'] = True
            await send_session_update(session)
            
            # Xóa session khỏi bộ nhớ hệ thống (chỉ lưu trên web history)
            del state.active_sessions[card_uid]

        state.total_out += 1
        state.available_slots = min(state.total_slots, state.available_slots + 1)
        state.last_cost = cost
        await send_stats()

        # Xóa nội dung biển số lưu trong thẻ RFID
        asyncio.create_task(asyncio.to_thread(rfid_write_plate, 'exit', ''))

        logger.info(f"[EXIT] Khớp! {plate_current} = {plate_from_card}, Chi phí: {cost} VNĐ ({duration_minutes} phút)")

    else:
        # === KHÔNG KHỚP ===
        lcd_lines = [
            '      CONG RA       ',
            f'Thoi gian: {time_str}',
            f'Bien so: {plate_current[:11].ljust(11)}',
            'Trang thai: LOI     '
        ]

        # Broadcast web TRƯỚC, buzzer/LCD chạy background
        await send_buzzer('exit', 'error')
        await send_lcd_update('exit', lcd_lines)
        asyncio.create_task(buzzer_beep_async(3))
        asyncio.create_task(lcd_display_async('exit', lcd_lines))

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

    # Đóng thanh chắn qua lock (tránh chồng lệnh PWM)
    await close_barrier_async(gate_type)
    await send_gate_status(gate_type)

    # Reset LCD background
    if gate_type == 'entry':
        lcd_lines = ['     CONG VAO       ', 'Thoi gian:          ', 'Bien so xe:         ', 'Trang thai: SAN SANG']
    else:
        lcd_lines = ['      CONG RA       ', 'Thoi gian:          ', 'Bien so xe:         ', 'Trang thai: SAN SANG']
    await send_lcd_update(gate_type, lcd_lines)
    asyncio.create_task(lcd_display_async(gate_type, lcd_lines))

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
                    # Mở barrier qua lock rồi chạy auto-close — không block WS handler
                    async def _open_then_autoclose(gt: str):
                        await open_barrier_async(gt)
                        await handle_barrier_auto_close(gt)
                    asyncio.create_task(_open_then_autoclose(gate_type))
                    await send_gate_status(gate_type)

                elif cmd_type == 'update_settings':
                    global COST_PER_MINUTE
                    if 'costPerMinute' in payload:
                        COST_PER_MINUTE = payload['costPerMinute']
                        logger.info(f"Cập nhật phí: {COST_PER_MINUTE} VNĐ/phút")
                
                elif cmd_type == 'export_and_reset':
                    if not os.path.exists('exports'):
                        os.makedirs('exports')
                    
                    filename = f"exports/History_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    try:
                        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                            writer = csv.writer(f)
                            writer.writerow(['Session ID', 'UID The', 'Bien so vao', 'Gio vao', 'Bien so ra', 'Gio ra', 'Thoi gian (phut)', 'Chi phi (VND)', 'Trang thai'])
                            for s in state.history_sessions:
                                status = 'Da ra' if s.get('timeOut') else 'Dang trong bai'
                                writer.writerow([
                                    s.get('id', ''),
                                    s.get('cardUID', ''),
                                    s.get('plateIn', ''),
                                    s.get('timeIn', ''),
                                    s.get('plateOut', ''),
                                    s.get('timeOut', ''),
                                    s.get('durationMinutes', ''),
                                    s.get('cost', ''),
                                    status
                                ])
                        logger.info(f"Da xuat file: {filename}")
                    except Exception as e:
                        logger.error(f"Loi xuat file: {e}")
                    
                    # Reset stats, clear history but KEEP active sessions
                    state.total_in = len(state.active_sessions) # Nhung xe con trong bai duoc tinh la xe vao? Khong, reset luon ve 0 theo yeu cau.
                    # Nguoi dung muon reset "tổng xe vào, tổng xe ra", co nghia la trong ca lam viec moi.
                    state.total_in = 0
                    state.total_out = 0
                    state.last_cost = None
                    state.history_sessions = []
                    
                    await send_stats()
                    await broadcast({
                        'type': 'reset_history',
                        'payload': {},
                        'timestamp': datetime.now().isoformat()
                    })

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
        # Poll cổng VÀO (RC522 #1 trên SPI0-CE0) trong thread riêng
        card_uid = await asyncio.to_thread(rfid_read_card, 'entry')
        if card_uid:
            await handle_entry_rfid(card_uid)
            await asyncio.sleep(2)  # Debounce

        # Poll cổng RA (RC522 #2 trên SPI0-CE1) trong thread riêng
        card_uid_exit = await asyncio.to_thread(rfid_read_card, 'exit')
        if card_uid_exit:
            await handle_exit_rfid(card_uid_exit)
            await asyncio.sleep(2)  # Debounce

        await asyncio.sleep(0.05)  # Poll nhanh hơn: 20 lần/giây


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
    free_count = sum(1 for slot in all_statuses if slot['status'] == 'free')
    total_count = len(all_statuses)
    asyncio.create_task(update_lcd_info_async(free_count, total_count))
    
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
    update_lcd_info(state.total_slots, state.total_slots)  # Cập nhật ban đầu mặc định, sau đó update từ webcam

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
        if pi_gpio and pi_gpio.connected:
            pi_gpio.set_servo_pulsewidth(SERVO_ENTRY_PIN, 0)
            pi_gpio.set_servo_pulsewidth(SERVO_EXIT_PIN, 0)
            pi_gpio.stop()
            logger.info("Servo PWM đã tắt")
        if HW_AVAILABLE:
            GPIO.cleanup()
        if plate_processor:
            plate_processor.cleanup()
        if camera_mgr:
            camera_mgr.cleanup()