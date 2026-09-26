"""
controller.py — Virtual keyboard controller for game steering via DirectInput scan codes.

Uses Windows SendInput API with raw hardware scan codes (DirectInput).
This bypasses high-level virtual key filters and User Interface Privilege
Isolation (UIPI), allowing the simulated keys to reach hardware-polled games,
web browsers, and WebGL canvases (such as Unity/Construct games on CrazyGames).

Key mappings (Standard WASD)
────────────────────────────
  W (Scan Code 0x11) → Forward / Accelerate
  A (Scan Code 0x1E) → Steer Left
  D (Scan Code 0x20) → Steer Right
"""

from __future__ import annotations

import ctypes
import sys
from typing import Optional

__all__ = ["KeyboardController", "KEY_LEFT", "KEY_RIGHT", "KEY_FORWARD"]

# Key bindings matching the original file constants (strings for compatibility)
KEY_LEFT = 'a'
KEY_RIGHT = 'd'
KEY_FORWARD = 'w'

# Hardware Scan Codes (Keyboard Set 1)
SCAN_W = 0x11  # 'w'
SCAN_A = 0x1E  # 'a'
SCAN_D = 0x20  # 'd'
SCAN_S = 0x1F  # 's'

# ULONG_PTR scales automatically: 4 bytes on 32-bit, 8 bytes on 64-bit Windows.
ULONG_PTR = ctypes.c_size_t


class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR)
    ]


class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort)
    ]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR)
    ]


class Input_I(ctypes.Union):
    _fields_ = [
        ("ki", KeyBdInput),
        ("mi", MouseInput),
        ("hi", HardwareInput)
    ]


class Input(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", Input_I)
    ]


# dwFlags values
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002


# ---------------------------------------------------------------------------
# Key press / release primitives
# ---------------------------------------------------------------------------
def _win_press_key(scancode: int) -> None:
    """Send a raw keydown event using SendInput API."""
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, scancode, KEYEVENTF_SCANCODE, 0, 0)
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def _win_release_key(scancode: int) -> None:
    """Send a raw keyup event using SendInput API."""
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, scancode, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, 0)
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


# Fallback for non-Windows platforms (using pynput)
_fallback_controller = None
if sys.platform != "win32":
    try:
        from pynput.keyboard import Controller
        _fallback_controller = Controller()
    except ImportError:
        pass


class KeyboardController:
    """
    Simulates keyboard input for game steering using DirectInput scan codes.

    Fixes the bugs from the original pynput version:
    1. Works on browser and WebGL game engines (using raw hardware scan codes).
    2. Turning left/right no longer releases the W key (acceleration), preventing
       the car from freezing/stopping during steering maneuvers.
    """

    # Scan codes managed by this controller
    _ALL_KEYS = (SCAN_A, SCAN_D, SCAN_W, SCAN_S)

    def __init__(self) -> None:
        self.current_state: str | None = None
        self._driving: bool = False
        self._braking: bool = False
        self._is_windows = (sys.platform == "win32")

    def _press(self, scancode: int) -> None:
        if self._is_windows:
            _win_press_key(scancode)
        elif _fallback_controller:
            char = "w" if scancode == SCAN_W else "s" if scancode == SCAN_S else "a" if scancode == SCAN_A else "d"
            _fallback_controller.press(char)

    def _release(self, scancode: int) -> None:
        if self._is_windows:
            _win_release_key(scancode)
        elif _fallback_controller:
            char = "w" if scancode == SCAN_W else "s" if scancode == SCAN_S else "a" if scancode == SCAN_A else "d"
            _fallback_controller.release(char)

    def _press_only(self, scancode: int, state_name: str) -> None:
        """Release other direction keys and press the target scancode."""
        if self.current_state == state_name:
            # Prevent keyboard event flooding (pressing an already held key causes lag/freezing)
            return

        # BUG FIX: Only release direction keys (A and D).
        # The original code called self._release_all_keys() here, which
        # released the W key and stopped the car from accelerating.
        self._release_direction_keys()

        self._press(scancode)
        self.current_state = state_name
        print(f"[Controller] {state_name}")

    def _release_direction_keys(self) -> None:
        """Release steering scan codes (A and D) only."""
        self._release(SCAN_A)
        self._release(SCAN_D)

    def _release_all_keys(self) -> None:
        """Release W, A, and D scan codes."""
        for code in self._ALL_KEYS:
            self._release(code)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API (Matches Original Main loop Calls)
    # ──────────────────────────────────────────────────────────────────────────

    def turn_left(self) -> None:
        """Hold the A key to steer left."""
        self._press_only(SCAN_A, "LEFT")

    def turn_right(self) -> None:
        """Hold the D key to steer right."""
        self._press_only(SCAN_D, "RIGHT")

    def straight(self) -> None:
        """Release A and D so the car drives straight (W remains held)."""
        if self.current_state in ("STRAIGHT", None):
            return

        self._release_direction_keys()
        self.current_state = "STRAIGHT"
        print("[Controller] STRAIGHT")

    def start_driving(self) -> None:
        """Hold the W key to accelerate."""
        if self._braking:
            self._release(SCAN_S)
            self._braking = False

        if self._driving:
            # Prevent keyboard event flooding (pressing an already held key causes lag/freezing)
            return

        self._press(SCAN_W)
        self._driving = True
        print("[Controller] W HELD  — DRIVING")

    def start_braking(self) -> None:
        """Hold the S key to brake/reverse (releases W)."""
        if self._driving:
            self._release(SCAN_W)
            self._driving = False

        if self._braking:
            # Prevent keyboard event flooding (pressing an already held key causes lag/freezing)
            return

        self._press(SCAN_S)
        self._braking = True
        print("[Controller] S HELD  — BRAKING")

    def stop(self) -> None:
        """Release W, A, D, and S keys to stop the vehicle."""
        if not self._driving and not self._braking and self.current_state is None:
            return

        self._release_all_keys()
        self._driving = False
        self._braking = False
        self.current_state = None
        print("[Controller] ALL RELEASED — STOPPED")

    def release_all(self) -> None:
        """Clean up and release all keys."""
        self._release_all_keys()
        self._driving = False
        self._braking = False
        self.current_state = None
        print("[Controller] ALL RELEASED")

    def __repr__(self) -> str:
        return (
            f"KeyboardController("
            f"state={self.current_state!r}, driving={self._driving})"
        )


if __name__ == "__main__":
    import time
    ctrl = KeyboardController()
    print("DirectInput scan-code keyboard controller smoke test.")
    ctrl.turn_left()
    time.sleep(1)
    ctrl.turn_right()
    time.sleep(1)
    ctrl.release_all()
    print("Done.")
