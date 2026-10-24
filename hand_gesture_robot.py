import math
import time

import cv2
import mediapipe as mp
import serial
import serial.tools.list_ports
from flask import Flask, Response

# ===== AUTO-DETECT ESP32 PORT =====
def find_esp32_port():
    ports = serial.tools.list_ports.comports()
    print("[+] Available ports:")
    for p in ports:
        print(f"  {p.device}: {p.description}")
    for p in ports:
        text = f"{p.description} {p.device}".upper()
        if any(k in text for k in ("USB", "CH340", "CP210", "ESP32", "ACM")):
            print(f"[+] Found ESP32 at {p.device}")
            return p.device
    return None

PORT = find_esp32_port()
if PORT is None:
    print("[-] ESP32 not found!")
    exit()

# ===== SERIAL CONFIGURATION =====
BAUD = 115200
esp32 = None

def init_serial():
    global esp32
    try:
        esp32 = serial.Serial()
        esp32.port = PORT
        esp32.baudrate = BAUD
        esp32.timeout = 1
        esp32.dtr = False
        esp32.rts = False
        esp32.open()
        time.sleep(2)
        print(f"[+] Serial connection established on {PORT}")
        return True
    except Exception as e:
        print(f"[-] Serial connection failed: {e}")
        esp32 = None
        return False

init_serial()

# ===== FLASK & CAMERA =====
app = Flask(__name__)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("Error: Cannot open USB camera!")
    exit()
print("[+] Camera opened successfully")

# ===== MEDIAPIPE SETUP =====
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
HL = mp_hands.HandLandmark

# ===== GLOBAL VARIABLES =====
last_command = None
pending_command = None
confirm_counter = 0
CONFIRM_THRESHOLD = 3        # frames a gesture must be stable before sending
POINT_THRESHOLD = 0.05       # min horizontal offset (normalized) to count as left/right

STOP_CMD = b"STOP,0\n"

# ===== GESTURE RECOGNITION =====
def _dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

def finger_states(lm):
    """Return [thumb, index, middle, ring, pinky] -> True if extended.
    Uses distances from the wrist, so it works for any hand orientation
    (including a finger pointing sideways) and for either hand."""
    wrist = lm[HL.WRIST]

    # Thumb: tip farther from the pinky base than the IP joint is
    pinky_mcp = lm[HL.PINKY_MCP]
    thumb = _dist(lm[HL.THUMB_TIP], pinky_mcp) > _dist(lm[HL.THUMB_IP], pinky_mcp) * 1.1

    def extended(tip, pip):
        return _dist(lm[tip], wrist) > _dist(lm[pip], wrist) * 1.05

    index = extended(HL.INDEX_FINGER_TIP, HL.INDEX_FINGER_PIP)
    middle = extended(HL.MIDDLE_FINGER_TIP, HL.MIDDLE_FINGER_PIP)
    ring = extended(HL.RING_FINGER_TIP, HL.RING_FINGER_PIP)
    pinky = extended(HL.PINKY_TIP, HL.PINKY_PIP)
    return [thumb, index, middle, ring, pinky]

def classify_gesture(lm):
    """Return (command_bytes, label, bgr_color). Unknown -> STOP."""
    thumb, index, middle, ring, pinky = finger_states(lm)

    # Open palm: all five fingers open -> STOP
    if thumb and index and middle and ring and pinky:
        return STOP_CMD, "STOP (PALM)", (0, 0, 255)

    # V sign: index + middle up, ring + pinky down -> FORWARD
    if index and middle and not ring and not pinky:
        return b"FORWARD,70\n", "FORWARD (V)", (0, 255, 0)

    # Fist: all four fingers closed (thumb ignored) -> BACKWARD
    if not index and not middle and not ring and not pinky:
        return b"BACKWARD,70\n", "BACKWARD (FIST)", (255, 0, 0)

    # Pointing: only index extended; direction from index base -> tip
    if index and not middle and not ring and not pinky:
        dx = lm[HL.INDEX_FINGER_TIP].x - lm[HL.INDEX_FINGER_MCP].x
        dy = lm[HL.INDEX_FINGER_TIP].y - lm[HL.INDEX_FINGER_MCP].y
        if abs(dx) > abs(dy):  # mostly horizontal
            if dx < -POINT_THRESHOLD:
                return b"LEFT,70\n", "LEFT (POINT)", (0, 255, 255)
            if dx > POINT_THRESHOLD:
                return b"RIGHT,70\n", "RIGHT (POINT)", (255, 255, 0)

    # Anything else is unknown -> STOP
    return STOP_CMD, "STOP (UNKNOWN)", (0, 0, 255)

# ===== SERIAL SEND FUNCTION =====
def send_command(command_bytes):
    global esp32
    if esp32 is None or not esp32.is_open:
        print("[-] ESP32 not connected!")
        return False
    try:
        print(f"[SEND] {command_bytes.decode().strip()}")
        esp32.write(command_bytes)
        esp32.flush()
        while esp32.in_waiting > 0:
            response = esp32.readline().decode(errors="ignore").strip()
            if response:
                print(f"[ESP32] {response}")
        return True
    except Exception as e:
        print(f"[-] Send error: {e}")
        return False

# ===== FLASK ROUTES =====
@app.route("/")
def index():
    return """
    <html>
    <head>
        <title>Gesture Control Robot - Live Stream</title>
        <style>
            body { text-align: center; font-family: Arial; background-color: #1a1a1a; color: white; }
            h1 { color: #00ff00; }
            img { border: 3px solid #00ff00; margin: 20px; }
            .info { font-size: 18px; margin: 20px; background: #333; padding: 15px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>Gesture Control Robot - Live Stream</h1>
        <img src="/video_feed" width="640" height="480">
        <div class="info">
            <p><strong>Gesture Control:</strong></p>
            <p>V sign (index + middle) &rarr; FORWARD | Fist &rarr; BACKWARD</p>
            <p>Point left &rarr; LEFT | Point right &rarr; RIGHT</p>
            <p>Open palm / no hand / unknown &rarr; STOP</p>
        </div>
    </body>
    </html>
    """

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

# ===== FRAME GENERATION WITH HAND DETECTION =====
def generate_frames():
    global last_command, pending_command, confirm_counter

    with mp_hands.Hands(
        max_num_hands=1,
        model_complexity=0,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    ) as hands:

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)  # mirror view: your left = screen left
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                current_command, display_text, action_color = classify_gesture(hand_landmarks.landmark)
                no_hand = False
            else:
                current_command = STOP_CMD
                display_text = "STOP (NO HAND)"
                action_color = (0, 0, 255)
                no_hand = True

            # Debounce: require a stable gesture, but stop immediately if hand is lost
            if no_hand:
                pending_command = current_command
                confirm_counter = CONFIRM_THRESHOLD
            elif current_command == pending_command:
                confirm_counter += 1
            else:
                pending_command = current_command
                confirm_counter = 1

            # Only send when the gesture changes
            if confirm_counter >= CONFIRM_THRESHOLD and pending_command != last_command:
                if send_command(pending_command):
                    last_command = pending_command

            cv2.putText(frame, f"Action: {display_text}", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, action_color, 2)

            connected = esp32 is not None and esp32.is_open
            cv2.putText(frame, f"Serial: {'CONNECTED' if connected else 'DISCONNECTED'}", (10, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 255, 0) if connected else (0, 0, 255), 2)

            ok, buffer = cv2.imencode(".jpg", frame)
            if not ok:
                continue

            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")

if __name__ == "__main__":
    print("[+] Starting Gesture Control Robot Server...")
    print(f"[+] Serial Port: {PORT} at {BAUD} baud")
    print("[+] Open browser and go to: http://YOUR_PI_IP:5000")

    try:
        app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\n[+] Shutting down...")
    finally:
        if esp32 and esp32.is_open:
            send_command(STOP_CMD)
            time.sleep(0.3)
            esp32.close()
        cap.release()
        print("[+] Done!")