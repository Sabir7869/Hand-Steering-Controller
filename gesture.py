"""
gesture.py — Hand gesture recognition using MediaPipe landmark coordinates.

Detected gestures
─────────────────
  Open Palm   → ACCELERATE   (all 4 fingers extended)
  Closed Fist → BRAKE        (all 4 fingers curled)
  Thumbs Up   → START        (thumb up, all 4 fingers curled)
  Peace Sign  → PAUSE        (index + middle up, ring + pinky curled)
  (none)      → NONE         (ambiguous / transitional pose)

Landmark index reference (MediaPipe convention)
───────────────────────────────────────────────
  0  = WRIST
  1  = THUMB_CMC   2  = THUMB_MCP   3  = THUMB_IP    4  = THUMB_TIP
  5  = INDEX_MCP   6  = INDEX_PIP   7  = INDEX_DIP   8  = INDEX_TIP
  9  = MIDDLE_MCP  10 = MIDDLE_PIP  11 = MIDDLE_DIP  12 = MIDDLE_TIP
  13 = RING_MCP    14 = RING_PIP    15 = RING_DIP    16 = RING_TIP
  17 = PINKY_MCP   18 = PINKY_PIP   19 = PINKY_DIP   20 = PINKY_TIP

In image coordinates y increases downward, so:
  "finger extended" ↔  tip.y  <  pip.y   (tip is higher on-screen)
  "finger curled"   ↔  tip.y  >= pip.y
"""


# ── Landmark IDs ──────────────────────────────────────────────────────────────
_WRIST       = 0
_THUMB_CMC   = 1
_THUMB_MCP   = 2
_THUMB_IP    = 3
_THUMB_TIP   = 4

# Finger tip / PIP pairs: (tip_id, pip_id)
_FINGER_PAIRS = [
    (8,  6),   # Index
    (12, 10),  # Middle
    (16, 14),  # Ring
    (20, 18),  # Pinky
]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _y(lm: list[dict], idx: int) -> int:
    """Return the y-pixel coordinate of landmark *idx*."""
    return lm[idx]["y"]


def _x(lm: list[dict], idx: int) -> int:
    """Return the x-pixel coordinate of landmark *idx*."""
    return lm[idx]["x"]


def _finger_extended(lm: list[dict], tip_id: int, pip_id: int) -> bool:
    """
    Return True when the finger is extended (straightened).

    A finger is considered extended when its tip is higher on-screen than
    its PIP joint, i.e. tip.y < pip.y (smaller y = higher pixel row).

    Args:
        lm:     List of 21 landmark dicts {'id', 'x', 'y'}.
        tip_id: Landmark index of the fingertip.
        pip_id: Landmark index of the PIP (proximal inter-phalangeal) joint.

    Returns:
        True if extended, False if curled.
    """
    return _y(lm, tip_id) < _y(lm, pip_id)


def _fingers_state(lm: list[dict]) -> list[bool]:
    """
    Return a 4-element list of booleans indicating which fingers are extended.

    Order: [index, middle, ring, pinky]
    """
    return [_finger_extended(lm, tip, pip) for tip, pip in _FINGER_PAIRS]


def _thumb_up(lm: list[dict]) -> bool:
    """
    Return True when the thumb is clearly pointing upward.

    Detection: thumb tip must be above (smaller y than) the wrist AND
    above the thumb MCP joint, forming an upward chain.
    A generous vertical gap is required to avoid false positives during
    fist or open-palm poses.
    """
    tip_y  = _y(lm, _THUMB_TIP)
    mcp_y  = _y(lm, _THUMB_MCP)
    wrist_y = _y(lm, _WRIST)

    # Tip must be above MCP by at least 20 px, and above wrist
    return (mcp_y - tip_y) > 20 and tip_y < wrist_y


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

# Gesture display metadata: label shown on-screen and BGR colour
GESTURE_INFO: dict[str, dict] = {
    "ACCELERATE": {"label": "ACCELERATE",        "color": (50,  220,  50)},   # Green
    "BRAKE":      {"label": "BRAKE",             "color": (50,   50, 220)},   # Red
    "START":      {"label": "START",             "color": (0,   200, 255)},   # Amber
    "PAUSE":      {"label": "PAUSE",             "color": (200, 120,  20)},   # Blue-ish
    "NONE":       {"label": "...",               "color": (140, 140, 140)},   # Grey
}


def detect_gesture(landmarks: list[dict]) -> str:
    """
    Classify the current hand pose into one of five gesture labels.

    Gesture rules (evaluated top-to-bottom; first match wins)
    ──────────────────────────────────────────────────────────
    BRAKE        — all 4 fingers curled AND thumb NOT clearly up.
                   Fist is checked before open palm to avoid ambiguity
                   when fingers are mid-motion.

    ACCELERATE   — all 4 fingers extended (open palm).

    START        — all 4 fingers curled AND thumb clearly pointing up
                   (classic thumbs-up pose).

    PAUSE        — index + middle extended, ring + pinky curled
                   (peace / victory sign).

    NONE         — any other / transitional pose.

    Args:
        landmarks: List of 21 dicts [{'id': int, 'x': int, 'y': int}]
                   as returned by HandDetector.find_landmarks().
                   Must contain exactly 21 entries.

    Returns:
        One of: "ACCELERATE", "BRAKE", "START", "PAUSE", "NONE".
    """
    # ── Guard: require all 21 landmarks ───────────────────────────────────────
    if len(landmarks) < 21:
        return "NONE"

    lm             = landmarks                 # Shorthand
    index, middle, ring, pinky = _fingers_state(lm)
    all_curled     = not any([index, middle, ring, pinky])
    all_extended   = all([index, middle, ring, pinky])

    # ── 1. BRAKE — closed fist (all curled, thumb not prominently up) ─────────
    if all_curled and not _thumb_up(lm):
        return "BRAKE"

    # ── 2. ACCELERATE — open palm (all fingers extended) ─────────────────────
    if all_extended:
        return "ACCELERATE"

    # ── 3. START — thumbs-up (all fingers curled, thumb clearly up) ──────────
    if all_curled and _thumb_up(lm):
        return "START"

    # ── 4. PAUSE — peace sign (index + middle up, ring + pinky down) ─────────
    if index and middle and not ring and not pinky:
        return "PAUSE"

    # ── 5. Unrecognised / transitional pose ───────────────────────────────────
    return "NONE"
