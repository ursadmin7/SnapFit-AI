import cv2
import time
import math
import os
import json
from collections import deque

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ============================================================
# SNAPFIT AI - PHASE 3 PUSH-UP ANALYZER & FORM COACH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "pose_landmarker_full.task"
)

CAMERA_INDEX = 0
WINDOW_NAME = "SnapFit AI - Push-Up Coach (Phase 3)"
TARGET_REPS = 8

RESULT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "exercise_result.json"
)
# Pose Landmark Indices
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_ELBOW, RIGHT_ELBOW = 13, 14
LEFT_WRIST, RIGHT_WRIST = 15, 16
LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_ANKLE, RIGHT_ANKLE = 27, 28

MIN_VISIBILITY = 0.40
SMOOTHING_FRAMES = 5
CALIBRATION_SECONDS = 2.0
MIN_REP_TIME = 0.5

CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24), (23, 25), (25, 27), (24, 26), (26, 28)
]


# ============================================================
# MATHEMATICAL HELPERS
# ============================================================

def calculate_angle(a, b, c):
    ax, ay = a
    bx, by = b
    cx, cy = c

    ba = (ax - bx, ay - by)
    bc = (cx - bx, cy - by)

    mag_ba = math.hypot(ba[0], ba[1])
    mag_bc = math.hypot(bc[0], bc[1])

    if mag_ba == 0 or mag_bc == 0:
        return None

    cosine = (ba[0] * bc[0] + ba[1] * bc[1]) / (mag_ba * mag_bc)
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))


def visible(landmarks, index):
    if index >= len(landmarks):
        return False
    return landmarks[index].visibility >= MIN_VISIBILITY


def get_elbow_angle(landmarks):
    left_vis = (visible(landmarks, LEFT_SHOULDER) and visible(landmarks, LEFT_ELBOW) and visible(landmarks, LEFT_WRIST))
    right_vis = (visible(landmarks, RIGHT_SHOULDER) and visible(landmarks, RIGHT_ELBOW) and visible(landmarks, RIGHT_WRIST))

    left_angle, right_angle = None, None

    if left_vis:
        left_angle = calculate_angle(
            (landmarks[LEFT_SHOULDER].x, landmarks[LEFT_SHOULDER].y),
            (landmarks[LEFT_ELBOW].x, landmarks[LEFT_ELBOW].y),
            (landmarks[LEFT_WRIST].x, landmarks[LEFT_WRIST].y)
        )

    if right_vis:
        right_angle = calculate_angle(
            (landmarks[RIGHT_SHOULDER].x, landmarks[RIGHT_SHOULDER].y),
            (landmarks[RIGHT_ELBOW].x, landmarks[RIGHT_ELBOW].y),
            (landmarks[RIGHT_WRIST].x, landmarks[RIGHT_WRIST].y)
        )

    if left_angle is None and right_angle is None:
        return None
    if left_angle is not None and right_angle is None:
        return left_angle
    if right_angle is not None and left_angle is None:
        return right_angle

    if left_angle is None:
        return right_angle
    if right_angle is None:
        return left_angle
    return (left_angle + right_angle) / 2.0


def check_spine_alignment(landmarks):
    """Evaluates shoulder-hip-ankle angle to detect hip sagging or arching."""
    if not (visible(landmarks, LEFT_SHOULDER) and visible(landmarks, LEFT_HIP) and visible(landmarks, LEFT_ANKLE)):
        return True, 180.0

    hip_angle = calculate_angle(
        (landmarks[LEFT_SHOULDER].x, landmarks[LEFT_SHOULDER].y),
        (landmarks[LEFT_HIP].x, landmarks[LEFT_HIP].y),
        (landmarks[LEFT_ANKLE].x, landmarks[LEFT_ANKLE].y)
    )

    if hip_angle is None:
        return True, 180.0

    # If angle deviates significantly from straight line (180 deg)
    is_straight = 150.0 <= hip_angle <= 210.0
    return is_straight, hip_angle


def get_body_center_and_bbox(landmarks, width, height):
    points = [(landmarks[i].x * width, landmarks[i].y * height) for i in range(len(landmarks)) if visible(landmarks, i)]
    if not points:
        return (width / 2.0, height / 2.0), (0, 0, width, height)

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (sum(xs) / len(xs), sum(ys) / len(ys)), (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))


# ============================================================
# PUSH-UP TRACKER CLASS
# ============================================================

class PushupTracker:
    def __init__(self, person_id):
        self.person_id = person_id
        self.reps = 0
        self.stage = "CALIBRATING"
        self.feedback = "Hold top plank position"
        self.feedback_color = (0, 215, 255)
        self.angle_history = deque(maxlen=SMOOTHING_FRAMES)
        self.calibration_angles = []
        self.calibration_start = time.monotonic()
        self.baseline_angle = None
        self.down_threshold = 95.0
        self.up_threshold = 150.0
        self.last_rep_time = 0.0
        self.center = (0.0, 0.0)
        self.reached_depth = False

    def update(self, landmarks):
        elbow_ang = get_elbow_angle(landmarks)
        spine_ok, hip_ang = check_spine_alignment(landmarks)

        if elbow_ang is None:
            self.feedback = "Arms obscured! Adjust camera"
            self.feedback_color = (0, 0, 255)
            return None, self.stage, self.feedback

        self.angle_history.append(elbow_ang)
        smooth_angle = sum(self.angle_history) / len(self.angle_history)

        # Calibration Phase
        if self.baseline_angle is None:
            self.stage = "CALIBRATING"
            self.calibration_angles.append(smooth_angle)
            elapsed = time.monotonic() - self.calibration_start
            remaining = max(0.0, CALIBRATION_SECONDS - elapsed)
            self.feedback = f"Hold high plank {remaining:.1f}s"
            self.feedback_color = (0, 215, 255)

            if elapsed >= CALIBRATION_SECONDS:
                sorted_angles = sorted(self.calibration_angles)
                self.baseline_angle = sorted_angles[int(len(sorted_angles) * 0.75)]
                self.up_threshold = max(140.0, self.baseline_angle * 0.90)
                self.down_threshold = 95.0
                self.stage = "UP"
                self.feedback = "Ready - Begin Push-Ups!"
                self.feedback_color = (0, 255, 0)
            return smooth_angle, self.stage, self.feedback

        # Spine Form Enforcement
        if not spine_ok:
            self.feedback = "Keep body straight! Don't sag hips"
            self.feedback_color = (0, 0, 255)

        # Rep Lifecycle Analysis
        if smooth_angle <= self.down_threshold:
            self.reached_depth = True
            if self.stage == "UP":
                self.stage = "DOWN"
                if spine_ok:
                    self.feedback = "Good chest depth! Push up"
                    self.feedback_color = (0, 255, 0)

        elif smooth_angle >= self.up_threshold:
            if self.stage == "DOWN":
                now = time.monotonic()
                if self.reached_depth and (now - self.last_rep_time >= MIN_REP_TIME):
                    self.reps += 1
                    self.last_rep_time = now
                    self.feedback = "GREAT PUSH-UP!"
                    self.feedback_color = (0, 255, 0)
                else:
                    self.feedback = "Lower chest further!"
                    self.feedback_color = (0, 0, 255)
                self.stage = "UP"
                self.reached_depth = False
            else:
                self.stage = "UP"
                if spine_ok:
                    self.feedback = "Ready"
                    self.feedback_color = (255, 255, 255)

        else:
            if self.stage == "UP" and not self.reached_depth:
                self.feedback = "Lower chest down..."
                self.feedback_color = (0, 215, 255)

        return smooth_angle, self.stage, self.feedback


# ============================================================
# RENDERING & DISPLAY
# ============================================================

def draw_hud_panel(frame, x, y, w, h, bg_color=(15, 15, 15), alpha=0.8):
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), bg_color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def draw_skeleton(frame, landmarks, active=False):
    height, width = frame.shape[:2]
    line_col = (0, 255, 0) if active else (255, 180, 0)
    point_col = (0, 0, 255) if active else (255, 100, 0)

    for a, b in CONNECTIONS:
        if visible(landmarks, a) and visible(landmarks, b):
            p1 = (int(landmarks[a].x * width), int(landmarks[a].y * height))
            p2 = (int(landmarks[b].x * width), int(landmarks[b].y * height))
            cv2.line(frame, p1, p2, line_col, 3 if active else 2)

    for idx in [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST, LEFT_HIP, RIGHT_HIP, LEFT_ANKLE, RIGHT_ANKLE]:
        if visible(landmarks, idx):
            p = (int(landmarks[idx].x * width), int(landmarks[idx].y * height))
            cv2.circle(frame, p, 5, point_col, -1)


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Pose landmarker model missing at:\n{MODEL_PATH}")
        return

    print("Initializing SnapFit AI Push-Up Coach...")
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=2,
        min_pose_detection_confidence=0.45,
        min_pose_presence_confidence=0.45,
        min_tracking_confidence=0.45
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not camera.isOpened():
        print("ERROR: Webcam missing.")
        detector.close()
        return

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 960, 540)

    trackers = {}
    next_id = 1
    start_ms = int(time.monotonic_ns() // 1_000_000)
    workout_start = time.monotonic()
    final_reps = 0
    highest_reps = 0
    try:
        while True:
            success, frame = camera.read()
            if not success:
                break

            frame = cv2.flip(frame, 1)
            height, width = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            timestamp_ms = int(time.monotonic_ns() // 1_000_000) - start_ms
            result = detector.detect_for_video(mp_image, timestamp_ms)

            detected_poses = result.pose_landmarks if result.pose_landmarks else []
            active_id = None
            min_center_dist = float('inf')
            frame_center_x = width / 2.0
            current_frame_trackers = {}

            for landmarks in detected_poses:
                center, bbox = get_body_center_and_bbox(landmarks, width, height)

                matched_id = None
                best_dist = 120.0

                for tid, tr in trackers.items():
                    d = math.hypot(center[0] - tr.center[0], center[1] - tr.center[1])
                    if d < best_dist:
                        best_dist = d
                        matched_id = tid

                if matched_id is None:
                    matched_id = next_id
                    next_id += 1
                    tracker = PushupTracker(matched_id)
                else:
                    tracker = trackers[matched_id]

                tracker.center = center
                current_frame_trackers[matched_id] = (tracker, landmarks, bbox)

                dist_to_center = abs(center[0] - frame_center_x)
                if dist_to_center < min_center_dist:
                    min_center_dist = dist_to_center
                    active_id = matched_id

            trackers = {tid: data[0] for tid, data in current_frame_trackers.items()}
            if trackers:
                highest_reps = max(highest_reps, *(tracker.reps for tracker in trackers.values()))

            for tid, (tracker, landmarks, bbox) in current_frame_trackers.items():
                is_active = (tid == active_id)
                smooth_angle, stage, feedback = tracker.update(landmarks)

                draw_skeleton(frame, landmarks, active=is_active)

                bx1, by1, bx2, by2 = bbox
                box_color = (0, 255, 0) if is_active else (255, 180, 0)
                cv2.rectangle(frame, (bx1, by1), (bx2, by2), box_color, 2 if is_active else 1)

            # Render HUD Display Panel
            draw_hud_panel(frame, 15, 15, 360, 220, bg_color=(10, 10, 10), alpha=0.8)

            cv2.putText(frame, "EXERCISE: PUSH-UPS", (25, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

            if active_id and active_id in trackers:
                act_tr = trackers[active_id]
                cv2.putText(frame, f"PUSH-UPS: {act_tr.reps}/{TARGET_REPS}", (25, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 3)
                cv2.putText(frame, f"STAGE: {act_tr.stage}", (25, 130),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
                cv2.putText(frame, f"FEEDBACK: {act_tr.feedback}", (25, 175),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, act_tr.feedback_color, 2)
                if act_tr.reps >= TARGET_REPS:
                    cv2.putText(frame, "TARGET COMPLETE", (width - 310, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "NO PERSON DETECTED", (25, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

            elapsed = time.monotonic() - workout_start
            cv2.putText(frame, f"TIME: {elapsed:.1f}s", (25, 215),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

            cv2.putText(frame, "Q / ESC: Quit", (width - 140, height - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):
                break

            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break

            if active_id and trackers[active_id].reps >= TARGET_REPS:
                cv2.waitKey(1000)
                break

    except KeyboardInterrupt:
        pass
    finally:
        final_reps = max(
            highest_reps,
            max((tracker.reps for tracker in trackers.values()), default=0),
        )

        duration = time.monotonic() - workout_start
        result_data = {
            "exercise": "Push-Up",
            "reps": final_reps,
            "duration_seconds": round(duration, 2),
            "completed": final_reps >= TARGET_REPS,
        }

        try:
            os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
            with open(RESULT_FILE, "w", encoding="utf-8") as file:
                json.dump(result_data, file, indent=4)
        except OSError as error:
            print(f"ERROR: Could not save result: {error}")

        camera.release()
        detector.close()
        cv2.destroyAllWindows()
        cv2.waitKey(1)

    print()
    print("=" * 50)
    print("PUSH-UP AI RESULT")
    print("=" * 50)
    print(f"Reps      : {final_reps}/{TARGET_REPS}")
    print(f"Duration  : {duration:.2f} seconds")
    print(f"Completed : {result_data['completed']}")
    print("=" * 50)


if __name__ == "__main__":
    main()