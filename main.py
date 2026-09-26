# pyrefly: ignore [missing-import]
import cv2  # type: ignore # pyright: ignore
import math
import time
from collections import deque

# ── Import modules ──────────────────────────────────────────────────────────────
from detector   import HandDetector  # type: ignore # pyright: ignore
from controller import KeyboardController  # type: ignore # pyright: ignore
from gesture    import detect_gesture, GESTURE_INFO  # type: ignore # pyright: ignore

# ─────────────────────────────────────────────────────────────────────────────
# Steering zone constants (image width = 640)
# ─────────────────────────────────────────────────────────────────────────────
LEFT_BOUNDARY   = 220   # x < 220            → LEFT
RIGHT_BOUNDARY  = 420   # x > 420            → RIGHT
                        # 220 <= x <= 420    → STRAIGHT

# Visual styling for the zone overlay
_ZONE_ALPHA     = 0.25  # Transparency of the coloured zone bands
_LABEL_FONT     = cv2.FONT_HERSHEY_SIMPLEX

# Per-zone colour (BGR), zone label, and STEERING display text
_ZONES = {
    "LEFT":     {"color": (0,   140, 255), "label": "◀  LEFT",     "hud": "STEERING: LEFT"},
    "STRAIGHT": {"color": (50,  230,  50), "label": "▲  STRAIGHT", "hud": "STEERING: STRAIGHT"},
    "RIGHT":    {"color": (230, 210,   0), "label": "RIGHT  ▶",   "hud": "STEERING: RIGHT"},
}


# ─────────────────────────────────────────────────────────────────────────────
def get_steering(wrist_x: int) -> str:
    """Convert the wrist's X pixel coordinate into a steering command (one-hand fallback)."""
    if wrist_x < LEFT_BOUNDARY:
        return "RIGHT"
    elif wrist_x > RIGHT_BOUNDARY:
        return "LEFT"
    else:
        return "STRAIGHT"


# ─────────────────────────────────────────────────────────────────────────────
def draw_steering_zones(frame: "cv2.Mat", active: str = "") -> "cv2.Mat":
    """Draw three vertical steering zones on the frame as semi-transparent bands."""
    h, w, _ = frame.shape
    overlay  = frame.copy()

    # ── Define the three rectangular zones ────────────────────────────────────
    zones_rects = {
        "LEFT":     (0,                w,   0, LEFT_BOUNDARY),
        "STRAIGHT": (0,                h,   LEFT_BOUNDARY, RIGHT_BOUNDARY),
        "RIGHT":    (0,                h,   RIGHT_BOUNDARY, w),
    }

    for name, info in _ZONES.items():
        color = info["color"]
        alpha = _ZONE_ALPHA * 2.2 if name == active else _ZONE_ALPHA
        x1 = zones_rects[name][2]
        x2 = zones_rects[name][3]
        cv2.rectangle(overlay, (x1, 0), (x2, h), color, cv2.FILLED)
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        overlay = frame.copy()

    cv2.line(frame, (LEFT_BOUNDARY,  0), (LEFT_BOUNDARY,  h), (200, 200, 200), 2, cv2.LINE_AA)
    cv2.line(frame, (RIGHT_BOUNDARY, 0), (RIGHT_BOUNDARY, h), (200, 200, 200), 2, cv2.LINE_AA)

    label_y = 70
    zone_centres = {
        "LEFT":     LEFT_BOUNDARY  // 2,
        "STRAIGHT": (LEFT_BOUNDARY + RIGHT_BOUNDARY) // 2,
        "RIGHT":    (RIGHT_BOUNDARY + w) // 2,
    }
    for name, cx in zone_centres.items():
        label     = _ZONES[name]["label"]
        color     = _ZONES[name]["color"]
        scale     = 0.85 if name == active else 0.60
        thickness = 2    if name == active else 1
        txt_size  = cv2.getTextSize(label, _LABEL_FONT, scale, thickness)[0]
        txt_x     = cx - txt_size[0] // 2
        cv2.putText(frame, label, (txt_x, label_y),
                    _LABEL_FONT, scale, color, thickness, cv2.LINE_AA)

    return frame


# ─────────────────────────────────────────────────────────────────────────────
def draw_steering_hud(frame: "cv2.Mat", direction: str) -> "cv2.Mat":
    """Draw a STEERING: DIRECTION badge near the bottom of the frame."""
    h, w, _ = frame.shape
    color    = _ZONES[direction]["color"]
    text     = _ZONES[direction]["hud"]
    scale    = 1.3
    thick    = 3
    pad_x, pad_y = 28, 16

    txt_size = cv2.getTextSize(text, _LABEL_FONT, scale, thick)[0]
    txt_w, txt_h = txt_size

    pill_w = txt_w + pad_x * 2
    pill_h = txt_h + pad_y * 2
    pill_x = (w - pill_w) // 2
    pill_y = h - pill_h - 18

    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (pill_x, pill_y),
        (pill_x + pill_w, pill_y + pill_h),
        (20, 20, 20),
        cv2.FILLED,
        cv2.LINE_AA,
    )
    frame = cv2.addWeighted(overlay, 0.72, frame, 0.28, 0)

    cv2.rectangle(
        frame,
        (pill_x, pill_y),
        (pill_x + pill_w, pill_y + pill_h),
        color,
        2,
        cv2.LINE_AA,
    )

    txt_x = pill_x + pad_x
    txt_y = pill_y + pad_y + txt_h - 2

    cv2.putText(frame, text, (txt_x + 2, txt_y + 2),
                _LABEL_FONT, scale, (0, 0, 0), thick + 2, cv2.LINE_AA)
    cv2.putText(frame, text, (txt_x, txt_y),
                _LABEL_FONT, scale, color, thick, cv2.LINE_AA)

    return frame


# ─────────────────────────────────────────────────────────────────────────────
def draw_status_badge(frame: "cv2.Mat", hand_detected: bool) -> "cv2.Mat":
    """Draw status badge (DRIVING / NO HAND DETECTED) in the top-right corner."""
    if hand_detected:
        text  = "DRIVING"
        color = (50, 220, 50)
    else:
        text  = "NO HAND DETECTED"
        color = (50, 50, 220)

    h, w, _ = frame.shape
    scale    = 0.75
    thick    = 2
    pad_x, pad_y = 14, 10

    txt_size         = cv2.getTextSize(text, _LABEL_FONT, scale, thick)[0]
    txt_w, txt_h     = txt_size
    pill_w           = txt_w + pad_x * 2
    pill_h           = txt_h + pad_y * 2
    pill_x           = w - pill_w - 12
    pill_y           = 12

    overlay = frame.copy()
    cv2.rectangle(overlay, (pill_x, pill_y),
                  (pill_x + pill_w, pill_y + pill_h), (15, 15, 15), cv2.FILLED)
    frame = cv2.addWeighted(overlay, 0.70, frame, 0.30, 0)

    cv2.rectangle(frame, (pill_x, pill_y),
                  (pill_x + pill_w, pill_y + pill_h), color, 2, cv2.LINE_AA)

    txt_x = pill_x + pad_x
    txt_y = pill_y + pad_y + txt_h - 2
    cv2.putText(frame, text, (txt_x + 1, txt_y + 1),
                _LABEL_FONT, scale, (0, 0, 0), thick + 1, cv2.LINE_AA)
    cv2.putText(frame, text, (txt_x, txt_y),
                _LABEL_FONT, scale, color, thick, cv2.LINE_AA)

    return frame


# ─────────────────────────────────────────────────────────────────────────────
def draw_gesture_badge(frame: "cv2.Mat", gesture: str) -> "cv2.Mat":
    """Draw gesture name badge below the status badge."""
    if gesture in ("NONE", "STEERING", "BRAKING"):
        return frame

    info  = GESTURE_INFO[gesture]
    text  = info["label"]
    color = info["color"]

    h, w, _      = frame.shape
    scale        = 0.75
    thick        = 2
    pad_x, pad_y = 14, 10

    txt_size     = cv2.getTextSize(text, _LABEL_FONT, scale, thick)[0]
    txt_w, txt_h = txt_size
    pill_w       = txt_w + pad_x * 2
    pill_h       = txt_h + pad_y * 2
    pill_x       = w - pill_w - 12
    pill_y       = 62

    overlay = frame.copy()
    cv2.rectangle(overlay, (pill_x, pill_y),
                  (pill_x + pill_w, pill_y + pill_h), (15, 15, 15), cv2.FILLED)
    frame = cv2.addWeighted(overlay, 0.70, frame, 0.30, 0)

    cv2.rectangle(frame, (pill_x, pill_y),
                  (pill_x + pill_w, pill_y + pill_h), color, 2, cv2.LINE_AA)

    txt_x = pill_x + pad_x
    txt_y = pill_y + pad_y + txt_h - 2
    cv2.putText(frame, text, (txt_x + 1, txt_y + 1),
                _LABEL_FONT, scale, (0, 0, 0), thick + 1, cv2.LINE_AA)
    cv2.putText(frame, text, (txt_x, txt_y),
                _LABEL_FONT, scale, color, thick, cv2.LINE_AA)

    return frame


# ─────────────────────────────────────────────────────────────────────────────
def draw_dashboard(frame: "cv2.Mat", driving: bool, braking: bool, direction: str) -> "cv2.Mat":
    """Render key status dashboard HUD overlay on the frame."""
    h, w, _ = frame.shape
    
    overlay = frame.copy()
    cv2.rectangle(overlay, (15, 55), (320, 185), (15, 15, 15), cv2.FILLED)
    frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)
    
    cv2.rectangle(frame, (15, 55), (320, 185), (200, 200, 200), 1, cv2.LINE_AA)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    w_color = (50, 220, 50) if driving else (100, 100, 100)
    w_text = "[W] ACCELERATING" if driving else "[W] Forward"
    cv2.putText(frame, w_text, (30, 85), font, 0.6, w_color, 2 if driving else 1, cv2.LINE_AA)
    
    s_color = (50, 50, 220) if braking else (100, 100, 100)
    s_text = "[S] BRAKING" if braking else "[S] Brake/Reverse"
    cv2.putText(frame, s_text, (30, 115), font, 0.6, s_color, 2 if braking else 1, cv2.LINE_AA)
    
    a_active = (direction == "LEFT")
    a_color = (0, 140, 255) if a_active else (100, 100, 100)
    a_text = "[A] STEERING LEFT" if a_active else "[A] Steer Left"
    cv2.putText(frame, a_text, (30, 145), font, 0.6, a_color, 2 if a_active else 1, cv2.LINE_AA)
    
    d_active = (direction == "RIGHT")
    d_color = (230, 210, 0) if d_active else (100, 100, 100)
    d_text = "[D] STEERING RIGHT" if d_active else "[D] Steer Right"
    cv2.putText(frame, d_text, (30, 175), font, 0.6, d_color, 2 if d_active else 1, cv2.LINE_AA)
    
    return frame


# ─────────────────────────────────────────────────────────────────────────────
def open_camera() -> "cv2.VideoCapture | None":
    """Search for and open the first working camera index (0, 1, or 2)."""
    import sys
    is_windows = (sys.platform == "win32")

    for index in (0, 1, 2):
        if is_windows:
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                ret, _ = cap.read()
                if ret:
                    return cap
                cap.release()

        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            ret, _ = cap.read()
            if ret:
                return cap
            cap.release()

    return None


# ─────────────────────────────────────────────────────────────────────────────
def main():
    cap = open_camera()

    if cap is None:
        print("Error: Could not open any working webcam device.")
        return

    print("Webcam opened successfully. Press ESC to exit.")

    # Create detector optimized for two-hand tracking
    detector = HandDetector(
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    ctrl = KeyboardController()
    prev_time = time.time()
    window_visible = False

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("Error: Failed to capture frame.")
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            frame = detector.find_hands(frame, draw=True)
            
            hand0 = detector.find_landmarks(frame, 0)
            hand1 = detector.find_landmarks(frame, 1)
            
            active_hands = []
            if hand0:
                active_hands.append(hand0)
            if hand1:
                active_hands.append(hand1)
                
            num_active_hands = len(active_hands)

            direction = "STRAIGHT"
            gesture   = "NONE"
            is_braking = False
            
            if num_active_hands == 2:
                hand_a, hand_b = active_hands[0], active_hands[1]
                if hand_a[0]["x"] < hand_b[0]["x"]:
                    left_hand, right_hand = hand_a, hand_b
                else:
                    left_hand, right_hand = hand_b, hand_a
                    
                wrist_l = left_hand[0]
                wrist_r = right_hand[0]
                
                left_gesture = detect_gesture(left_hand)
                right_gesture = detect_gesture(right_hand)
                
                # If both hands are closed fists (BRAKE), apply brake.
                # In original gesture.py, Fist = BRAKE, Palm = ACCELERATE.
                is_braking = not (left_gesture in ("BRAKE", "START") and right_gesture in ("BRAKE", "START"))
                
                dx = wrist_r["x"] - wrist_l["x"]
                dy = wrist_r["y"] - wrist_l["y"]
                
                if dx != 0:
                    angle = math.degrees(math.atan2(dy, dx))
                else:
                    angle = 90.0 if dy > 0 else -90.0
                    
                # Mirror coordinate steering correction:
                # Clockwise rotation (negative angle) -> steer RIGHT
                # Counter-clockwise rotation (positive angle) -> steer LEFT
                if angle < -12.0:
                    direction = "LEFT"
                elif angle > 12.0:
                    direction = "RIGHT"
                else:
                    direction = "STRAIGHT"
                    
                gesture = "BRAKING" if is_braking else "STEERING"
                
                # Draw steering wheel overlay
                mid_x = (wrist_l["x"] + wrist_r["x"]) // 2
                mid_y = (wrist_l["y"] + wrist_r["y"]) // 2
                
                wheel_radius = int(math.hypot(dx, dy) // 2)
                wheel_radius = max(50, min(wheel_radius, 150))
                
                color = (50, 50, 220) if is_braking else _ZONES[direction]["color"]
                
                cv2.circle(frame, (mid_x, mid_y), wheel_radius, color, 3, cv2.LINE_AA)
                cv2.circle(frame, (mid_x, mid_y), 10, (150, 150, 150), cv2.FILLED, cv2.LINE_AA)
                cv2.line(frame, (wrist_l["x"], wrist_l["y"]), (wrist_r["x"], wrist_r["y"]), color, 3, cv2.LINE_AA)
                
                wrist_color = (0, 0, 255) if is_braking else (0, 255, 0)
                cv2.circle(frame, (wrist_l["x"], wrist_l["y"]), 12, wrist_color, cv2.FILLED)
                cv2.circle(frame, (wrist_r["x"], wrist_r["y"]), 12, wrist_color, cv2.FILLED)
                
                if is_braking:
                    hud_label = "BRAKING"
                else:
                    hud_label = f"Wheel: {angle:+.1f} deg"
                cv2.putText(frame, hud_label, (mid_x - 70, mid_y - wheel_radius - 15),
                            _LABEL_FONT, 0.65, color, 2, cv2.LINE_AA)
                
                cv2.putText(frame, f"Hands: 2", (15, h - 15), _LABEL_FONT, 0.75,
                            (255, 255, 255), 2, cv2.LINE_AA)

            # Keyboard drive dispatch
            if num_active_hands == 2:
                if is_braking:
                    ctrl.start_braking()
                else:
                    ctrl.start_driving()
                    
                if direction == "LEFT":
                    ctrl.turn_left()
                elif direction == "RIGHT":
                    ctrl.turn_right()
                else:
                    ctrl.straight()
            else:
                ctrl.stop()

            # HUD rendering
            if num_active_hands == 2:
                frame = draw_steering_hud(frame, direction)

            frame = draw_status_badge(frame, hand_detected=(num_active_hands == 2))
            frame = draw_gesture_badge(frame, gesture)

            # Calculate FPS
            curr_time = time.time()
            elapsed   = curr_time - prev_time
            fps       = 1.0 / elapsed if elapsed > 0 else 0.0
            prev_time = curr_time

            cv2.putText(frame, f"FPS: {fps:.1f}", (15, 35),
                        _LABEL_FONT, 1.0, (0, 255, 0), 2, cv2.LINE_AA)

            # Draw Dashboard Panel
            frame = draw_dashboard(frame, driving=ctrl._driving, braking=ctrl._braking, direction=direction)

            cv2.imshow("Hand Tracker — Press ESC to exit", frame)

            # Handle exit and window close cleanly
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                print("ESC pressed. Exiting.")
                break

            if not window_visible:
                if cv2.getWindowProperty("Hand Tracker — Press ESC to exit", cv2.WND_PROP_VISIBLE) >= 1:
                    window_visible = True
            
            if window_visible and cv2.getWindowProperty("Hand Tracker — Press ESC to exit", cv2.WND_PROP_VISIBLE) < 1:
                print("Window closed by user. Exiting.")
                break
    finally:
        ctrl.release_all()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
