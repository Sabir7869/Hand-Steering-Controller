import os
from pathlib import Path
os.environ['GLOG_minloglevel'] = '3'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import cv2
import mediapipe as mp
import urllib.request


# ── MediaPipe hand skeleton connection pairs ───────────────────────────────────
_HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # Index finger
    (0, 9), (9, 10), (10, 11), (11, 12),     # Middle finger
    (0, 13), (13, 14), (14, 15), (15, 16),   # Ring finger
    (0, 17), (17, 18), (18, 19), (19, 20),   # Pinky
    (5, 9), (9, 13), (13, 17),               # Palm cross-connections
]

# ── URL for the official hand landmark model ───────────────────────────────────
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
)
_MODEL_FILENAME = str(Path(__file__).resolve().with_name("hand_landmarker.task"))


class HandDetector:
    """
    Detects a single hand in a video frame using the MediaPipe Tasks API
    (mediapipe >= 0.10.x), draws the landmarks, and returns them as a
    list of dicts with pixel coordinates.
    """

    def __init__(
        self,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.7,
        model_path: str = _MODEL_FILENAME,
    ):
        """
        Initialize the HandLandmarker.

        Args:
            max_num_hands:            Maximum number of hands to detect.
            min_detection_confidence: Score threshold for initial detection.
            min_tracking_confidence:  Score threshold for frame tracking.
            model_path:               Path to hand_landmarker.task file.
                                      Auto-downloaded if not found.
        """
        # ── 1. Ensure the model file is present ───────────────────────────────
        model_path = self._ensure_model(model_path)

        # ── 2. Configure the HandLandmarker (Tasks API) ───────────────────────
        base_options = mp.tasks.BaseOptions(model_asset_path=model_path)
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

        # ── 3. Create the landmarker ──────────────────────────────────────────
        self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)

        # ── 4. Internal state ─────────────────────────────────────────────────
        self._timestamp_ms: int = 0   # Must increase monotonically for VIDEO mode
        self.results = None            # Latest detection result

        # ── 5. Drawing style constants ─────────────────────────────────────────
        self.DOT_COLOR       = (0, 255, 0)     # Green dots
        self.LINE_COLOR      = (255, 255, 255) # White connection lines
        self.DOT_RADIUS      = 4
        self.LINE_THICKNESS  = 2

    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _ensure_model(path: str) -> str:
        """
        Return 'path' if it already exists; otherwise download the model
        from Google's storage bucket to that path and return it.
        """
        if os.path.exists(path):
            return path

        print(f"[HandDetector] Model not found at '{path}'.")
        print(f"[HandDetector] Downloading from:\n  {_MODEL_URL}")
        urllib.request.urlretrieve(_MODEL_URL, path)
        print(f"[HandDetector] Model saved to '{path}'.")
        return path

    # ──────────────────────────────────────────────────────────────────────────
    def find_hands(self, frame: "cv2.Mat", draw: bool = True) -> "cv2.Mat":
        """
        Run hand detection on a BGR frame and optionally draw the skeleton.

        Args:
            frame: BGR image from OpenCV.
            draw:  If True, draw landmarks and connections on the frame.

        Returns:
            The (annotated) frame.
        """
        # ── 6. Convert BGR → RGB (MediaPipe expects RGB) ──────────────────────
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # ── 7. Advance timestamp and run detection ─────────────────────────────
        # VIDEO mode requires a strictly increasing timestamp_ms
        self._timestamp_ms += 33
        self.results = self.landmarker.detect_for_video(mp_image, self._timestamp_ms)

        # ── 8. Draw skeleton if landmarks found and drawing is enabled ─────────
        if draw and self.results.hand_landmarks:
            h, w, _ = frame.shape
            for hand in self.results.hand_landmarks:
                # Draw connection lines first (rendered underneath the dots)
                for start_idx, end_idx in _HAND_CONNECTIONS:
                    x1, y1 = int(hand[start_idx].x * w), int(hand[start_idx].y * h)
                    x2, y2 = int(hand[end_idx].x * w),   int(hand[end_idx].y * h)
                    cv2.line(frame, (x1, y1), (x2, y2),
                             self.LINE_COLOR, self.LINE_THICKNESS, cv2.LINE_AA)

                # Draw landmark dots on top of lines
                for lm in hand:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.circle(frame, (cx, cy), self.DOT_RADIUS,
                               self.DOT_COLOR, cv2.FILLED)

        return frame

    # ──────────────────────────────────────────────────────────────────────────
    def find_landmarks(
        self, frame: "cv2.Mat", hand_index: int = 0
    ) -> list[dict]:
        """
        Extract pixel coordinates for all 21 landmarks of a detected hand.

        MediaPipe landmark indices:
            0       = WRIST
            1–4     = THUMB  (CMC → TIP)
            5–8     = INDEX  (MCP → TIP)  ← id 8 is index fingertip
            9–12    = MIDDLE
            13–16   = RING
            17–20   = PINKY

        Args:
            frame:      Used to obtain pixel dimensions.
            hand_index: Which hand to extract (0 = first detected hand).

        Returns:
            List of 21 dicts {'id', 'x', 'y'}, or [] when no hand detected.
        """
        landmark_list: list[dict] = []

        # ── 9. Guard: no results yet or no hands visible ───────────────────────
        if not self.results or not self.results.hand_landmarks:
            return landmark_list
        if hand_index >= len(self.results.hand_landmarks):
            return landmark_list

        # ── 10. Convert normalised [0, 1] → pixel coordinates ─────────────────
        hand = self.results.hand_landmarks[hand_index]
        h, w, _ = frame.shape
        for idx, lm in enumerate(hand):
            landmark_list.append({
                "id": idx,
                "x":  int(lm.x * w),
                "y":  int(lm.y * h),
            })

        return landmark_list

    # ──────────────────────────────────────────────────────────────────────────
    def process(
        self, frame: "cv2.Mat", draw: bool = True
    ) -> tuple["cv2.Mat", list[dict]]:
        """
        Convenience method: detect, draw, and return landmarks in one call.

        Returns:
            (annotated_frame, landmark_list)
            landmark_list is empty when no hand is detected.
        """
        frame     = self.find_hands(frame, draw=draw)
        landmarks = self.find_landmarks(frame)
        return frame, landmarks


# ── Quick smoke-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    detector = HandDetector()
    print("Hand detector running — press ESC to exit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        frame, landmarks = detector.process(frame)
        if landmarks:
            wrist = landmarks[0]
            print(f"Wrist → x: {wrist['x']}, y: {wrist['y']}")
        cv2.imshow("Hand Detector Test — ESC to exit", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
