"""
camera_diagnostic.py — Standalone premium webcam diagnostics utility.

Helps test, measure, and verify webcam performance, backends,
resolution capabilities, and frame rates.
"""

import sys
import time
# pyrefly: ignore [missing-import]
import cv2

# Colors for HUD styling (BGR)
COLOR_TEXT = (255, 255, 255)  # White
COLOR_HUD = (0, 200, 255)     # Gold/orange
COLOR_ALERT = (50, 50, 255)    # Red
COLOR_OK = (50, 220, 50)       # Lime green
COLOR_GRID = (100, 100, 100)   # Grey

def draw_hud(frame, info):
    """Draw a rich dashboard diagnostic overlay on the frame."""
    h, w, _ = frame.shape
    
    # ── Dark semi-transparent pill overlay for the HUD ───────────────────────
    overlay = frame.copy()
    cv2.rectangle(overlay, (15, 15), (320, 240), (20, 20, 20), cv2.FILLED)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, dst=frame)
    
    # Border around the HUD box
    cv2.rectangle(frame, (15, 15), (320, 240), COLOR_HUD, 2, cv2.LINE_AA)
    
    # ── Draw HUD Content ─────────────────────────────────────────────────────
    font = cv2.FONT_HERSHEY_SIMPLEX
    y = 40
    line_height = 25
    
    # App Header
    cv2.putText(frame, "WEBCAM DIAGNOSTICS", (30, y), font, 0.65, COLOR_HUD, 2, cv2.LINE_AA)
    y += 30
    
    # Specs
    cv2.putText(frame, f"Device Index:  {info['index']}", (30, y), font, 0.5, COLOR_TEXT, 1, cv2.LINE_AA)
    y += line_height
    cv2.putText(frame, f"Backend:       {info['backend']}", (30, y), font, 0.5, COLOR_TEXT, 1, cv2.LINE_AA)
    y += line_height
    cv2.putText(frame, f"Resolution:    {w} x {h}", (30, y), font, 0.5, COLOR_TEXT, 1, cv2.LINE_AA)
    y += line_height
    cv2.putText(frame, f"Startup Time:  {info['startup']:.3f} s", (30, y), font, 0.5, COLOR_TEXT, 1, cv2.LINE_AA)
    y += line_height
    cv2.putText(frame, f"Target FPS:    {info['target_fps']}", (30, y), font, 0.5, COLOR_TEXT, 1, cv2.LINE_AA)
    y += line_height
    cv2.putText(frame, f"Current FPS:   {info['current_fps']:.1f}", (30, y), font, 0.5, COLOR_OK, 2, cv2.LINE_AA)
    y += line_height
    cv2.putText(frame, f"Frame Count:   {info['frames']}", (30, y), font, 0.5, COLOR_TEXT, 1, cv2.LINE_AA)

    # ── Draw Calibration Grid ────────────────────────────────────────────────
    # Horizontal grid lines
    for i in range(1, 4):
        y_grid = int(h * (i / 4.0))
        cv2.line(frame, (0, y_grid), (w, y_grid), COLOR_GRID, 1, cv2.LINE_AA)
    # Vertical grid lines
    for j in range(1, 4):
        x_grid = int(w * (j / 4.0))
        cv2.line(frame, (x_grid, 0), (x_grid, h), COLOR_GRID, 1, cv2.LINE_AA)
        
    # Center crosshair
    cv2.drawMarker(frame, (w // 2, h // 2), COLOR_ALERT, cv2.MARKER_CROSS, 24, 2)
    
    # ── Instructions Overlay at bottom ───────────────────────────────────────
    cv2.putText(frame, "Press ESC to Quit", (15, h - 15), font, 0.55, COLOR_ALERT, 2, cv2.LINE_AA)
    cv2.putText(frame, "Diagnostics Active", (w - 180, h - 15), font, 0.55, COLOR_OK, 2, cv2.LINE_AA)


def run_diagnostics():
    print("=" * 60)
    print("           WEBCAM DIAGNOSTIC & SPEC PROBER")
    print("=" * 60)
    print("Python version:", sys.version)
    print("OpenCV version:", cv2.__version__)
    print("\n[INFO] Scanning for cameras on indices 0, 1, 2...")
    
    is_windows = (sys.platform == "win32")
    working_cameras = []
    
    # ── Probe Devices ────────────────────────────────────────────────────────
    for index in (0, 1, 2):
        # On Windows, try CAP_DSHOW and default backends
        backends_to_try = [cv2.CAP_DSHOW, None] if is_windows else [None]
        for backend in backends_to_try:
            backend_label = "DSHOW" if backend == cv2.CAP_DSHOW else "DEFAULT"
            t0 = time.perf_counter()
            
            if backend is not None:
                cap = cv2.VideoCapture(index, backend)
            else:
                cap = cv2.VideoCapture(index)
                
            opened = cap.isOpened()
            dt = time.perf_counter() - t0
            
            if opened:
                ret, frame = cap.read()
                if ret:
                    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    bname = cap.getBackendName()
                    print(f" [OK] Camera Index {index} [{backend_label}]: Opened in {dt:.3f}s. Resolution: {w}x{h}, FPS: {fps}, Backend: {bname}")
                    working_cameras.append({
                        "index": index,
                        "backend_label": backend_label,
                        "backend_api": backend,
                        "startup": dt,
                        "default_w": w,
                        "default_h": h,
                        "default_fps": fps,
                        "backend_name": bname
                    })
                cap.release()
                break  # If this index works, no need to try other backends for it
            else:
                cap.release()
                
    if not working_cameras:
        print("\n[ERROR] No working cameras found on index 0, 1, or 2!")
        print("Please check USB connections, privacy settings, and driver status.")
        return

    # Choose the first working camera for the visual benchmark
    best_cam = working_cameras[0]
    print(f"\n[INFO] Launching visual preview on best camera:")
    print(f"       Index: {best_cam['index']} ({best_cam['backend_label']})")
    print(f"       Resolution: {best_cam['default_w']}x{best_cam['default_h']}")
    print("-" * 60)

    # Initialize camera for benchmark
    t0 = time.perf_counter()
    if best_cam['backend_api'] is not None:
        cap = cv2.VideoCapture(best_cam['index'], best_cam['backend_api'])
    else:
        cap = cv2.VideoCapture(best_cam['index'])
    
    # Enforce standard 640x480 for comparison
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    startup_time = time.perf_counter() - t0
    
    info = {
        "index": best_cam['index'],
        "backend": cap.getBackendName(),
        "startup": startup_time,
        "target_fps": cap.get(cv2.CAP_PROP_FPS),
        "current_fps": 0.0,
        "frames": 0
    }
    
    prev_time = time.perf_counter()
    window_visible = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Failed to read frame from webcam.")
            break
            
        info["frames"] += 1
        
        # Calculate current real-time FPS
        curr_time = time.perf_counter()
        elapsed = curr_time - prev_time
        prev_time = curr_time
        fps = 1.0 / elapsed if elapsed > 0 else 0.0
        
        # Simple rolling average for FPS display smoothing
        if info["current_fps"] == 0.0:
            info["current_fps"] = fps
        else:
            info["current_fps"] = info["current_fps"] * 0.9 + fps * 0.1
            
        # Draw the rich overlay
        draw_hud(frame, info)
        
        cv2.imshow("Webcam Diagnostics HUD", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            print("\n[INFO] Diagnostic preview closed by user.")
            break

        # Exit cleanly if the window is closed by the user clicking the "X" button
        # We guard this check by tracking if the window has ever become visible.
        if not window_visible:
            if cv2.getWindowProperty("Webcam Diagnostics HUD", cv2.WND_PROP_VISIBLE) >= 1:
                window_visible = True
        
        if window_visible and cv2.getWindowProperty("Webcam Diagnostics HUD", cv2.WND_PROP_VISIBLE) < 1:
            print("\n[INFO] Diagnostic window closed by user.")
            break

    cap.release()
    cv2.destroyAllWindows()
    print("=" * 60)
    print("                   DIAGNOSTICS COMPLETE")
    print("=" * 60)

main = run_diagnostics

if __name__ == "__main__":
    main()
