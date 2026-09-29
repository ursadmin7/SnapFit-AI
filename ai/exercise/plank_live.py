import cv2
import time
import math
import os
import json
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ============================================================
# SNAPFIT AI - PLANK COACH
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
WINDOW_NAME = "SnapFit AI - Plank Coach"
TARGET_SECONDS = 30
RESULT_FILE = os.path.join(BASE_DIR, "data", "exercise_result.json")

# MediaPipe landmark indices
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28

MIN_VISIBILITY = 0.40


# ============================================================
# UTILITY
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

    cosine = (
        (ba[0] * bc[0] + ba[1] * bc[1])
        / (mag_ba * mag_bc)
    )

    cosine = max(-1.0, min(1.0, cosine))

    return math.degrees(math.acos(cosine))


def visible(landmarks, index):
    if index >= len(landmarks):
        return False

    return landmarks[index].visibility >= MIN_VISIBILITY


def point(landmarks, index):
    return (
        landmarks[index].x,
        landmarks[index].y
    )


def average_point(landmarks, a, b):
    return (
        (landmarks[a].x + landmarks[b].x) / 2,
        (landmarks[a].y + landmarks[b].y) / 2
    )


# ============================================================
# PLANK ANALYSIS
# ============================================================

def calculate_body_line_angle(landmarks):
    required = [
        LEFT_SHOULDER,
        RIGHT_SHOULDER,
        LEFT_HIP,
        RIGHT_HIP,
        LEFT_ANKLE,
        RIGHT_ANKLE
    ]

    if not all(visible(landmarks, i) for i in required):
        return None

    shoulder = average_point(
        landmarks,
        LEFT_SHOULDER,
        RIGHT_SHOULDER
    )

    hip = average_point(
        landmarks,
        LEFT_HIP,
        RIGHT_HIP
    )

    ankle = average_point(
        landmarks,
        LEFT_ANKLE,
        RIGHT_ANKLE
    )

    return calculate_angle(
        shoulder,
        hip,
        ankle
    )


def calculate_hip_sag_angle(landmarks):
    required = [
        LEFT_SHOULDER,
        LEFT_HIP,
        LEFT_KNEE
    ]

    if not all(visible(landmarks, i) for i in required):
        return None

    return calculate_angle(
        point(landmarks, LEFT_SHOULDER),
        point(landmarks, LEFT_HIP),
        point(landmarks, LEFT_KNEE)
    )


# ============================================================
# SKELETON
# ============================================================

CONNECTIONS = [
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),

    (11, 23),
    (12, 24),

    (23, 24),

    (23, 25),
    (25, 27),

    (24, 26),
    (26, 28)
]


def draw_skeleton(frame, landmarks):
    height, width = frame.shape[:2]

    for a, b in CONNECTIONS:
        if visible(landmarks, a) and visible(landmarks, b):

            p1 = (
                int(landmarks[a].x * width),
                int(landmarks[a].y * height)
            )

            p2 = (
                int(landmarks[b].x * width),
                int(landmarks[b].y * height)
            )

            cv2.line(
                frame,
                p1,
                p2,
                (0, 255, 0),
                3
            )

    for index in [
        LEFT_SHOULDER,
        RIGHT_SHOULDER,
        LEFT_HIP,
        RIGHT_HIP,
        LEFT_KNEE,
        RIGHT_KNEE,
        LEFT_ANKLE,
        RIGHT_ANKLE
    ]:

        if visible(landmarks, index):

            p = (
                int(landmarks[index].x * width),
                int(landmarks[index].y * height)
            )

            cv2.circle(
                frame,
                p,
                5,
                (0, 0, 255),
                -1
            )


# ============================================================
# MAIN
# ============================================================

def main():

    if not os.path.exists(MODEL_PATH):
        print("ERROR: Pose model not found.")
        print(MODEL_PATH)
        save_result(0.0)
        return

    print("Initializing SnapFit AI Plank Coach...")

    base_options = python.BaseOptions(
        model_asset_path=MODEL_PATH
    )

    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.45,
        min_pose_presence_confidence=0.45,
        min_tracking_confidence=0.45
    )

    detector = vision.PoseLandmarker.create_from_options(
        options
    )

    camera = cv2.VideoCapture(
        CAMERA_INDEX,
        cv2.CAP_DSHOW
    )

    if not camera.isOpened():
        print("ERROR: Could not open camera.")
        detector.close()
        save_result(0.0)
        return

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

    cv2.namedWindow(
        WINDOW_NAME,
        cv2.WINDOW_NORMAL
    )

    cv2.resizeWindow(
        WINDOW_NAME,
        960,
        540
    )

    start_time_ms = int(
        time.monotonic_ns() // 1_000_000
    )

    plank_active = False
    start_plank_time = 0.0
    best_time = 0.0

    feedback = "Get into plank position"

    try:

        while True:

            success, frame = camera.read()

            if not success:
                break

            frame = cv2.flip(frame, 1)

            height, width = frame.shape[:2]

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb
            )

            timestamp = (
                int(time.monotonic_ns() // 1_000_000)
                - start_time_ms
            )

            result = detector.detect_for_video(
                mp_image,
                timestamp
            )

            poses = (
                result.pose_landmarks
                if result.pose_landmarks
                else []
            )

            body_angle = None
            hip_angle = None

            if poses:

                landmarks = poses[0]

                draw_skeleton(
                    frame,
                    landmarks
                )

                body_angle = calculate_body_line_angle(
                    landmarks
                )

                hip_angle = calculate_hip_sag_angle(
                    landmarks
                )

                if body_angle is not None:

                    # Good plank generally keeps
                    # shoulder-hip-ankle near straight.
                    good_body = body_angle >= 155

                    good_hip = (
                        hip_angle is None
                        or hip_angle >= 150
                    )

                    if good_body and good_hip:

                        if not plank_active:

                            plank_active = True
                            start_plank_time = time.monotonic()

                            feedback = "GOOD PLANK - HOLD"

                        elapsed = (
                            time.monotonic()
                            - start_plank_time
                        )

                        best_time = max(
                            best_time,
                            elapsed
                        )

                    else:

                        if plank_active:

                            feedback = "Fix your body position"

                        plank_active = False

                else:

                    plank_active = False
                    feedback = "Show your full body"

            else:

                plank_active = False
                feedback = "No person detected"

            # ------------------------------------------------
            # TIMER
            # ------------------------------------------------

            current_time = 0.0

            if plank_active:

                current_time = (
                    time.monotonic()
                    - start_plank_time
                )

            if current_time >= TARGET_SECONDS:
                feedback = "GREAT JOB - TARGET COMPLETE"

            # ------------------------------------------------
            # HUD
            # ------------------------------------------------

            overlay = frame.copy()

            cv2.rectangle(
                overlay,
                (15, 15),
                (390, 205),
                (10, 10, 10),
                -1
            )

            cv2.addWeighted(
                overlay,
                0.75,
                frame,
                0.25,
                0,
                frame
            )

            cv2.putText(
                frame,
                "SNAPFIT AI - PLANK COACH",
                (30, 48),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2
            )

            cv2.putText(
                frame,
                f"PLANK TIME: {current_time:.1f}/{TARGET_SECONDS}s",
                (30, 88),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"BEST: {best_time:.1f}s",
                (30, 125),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            if body_angle is not None:

                cv2.putText(
                    frame,
                    f"BODY ANGLE: {body_angle:.1f}",
                    (30, 160),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2
                )

            cv2.putText(
                frame,
                f"FEEDBACK: {feedback}",
                (30, 195),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 215, 255),
                2
            )

            cv2.putText(
                frame,
                "Q / ESC: Quit",
                (width - 150, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )

            cv2.imshow(
                WINDOW_NAME,
                frame
            )

            if current_time >= TARGET_SECONDS:
                cv2.waitKey(1000)
                break

            key = cv2.waitKey(1) & 0xFF

            if key in (
                ord("q"),
                ord("Q"),
                27
            ):
                print("Exit requested.")
                break

            if cv2.getWindowProperty(
                WINDOW_NAME,
                cv2.WND_PROP_VISIBLE
            ) < 1:
                break

    except KeyboardInterrupt:

        print("Interrupted by user.")

    finally:

        print("Cleaning up resources...")

        camera.release()
        detector.close()

        cv2.destroyAllWindows()
        cv2.waitKey(1)

        result = save_result(best_time)
        print(
            f"Plank hold: {result['duration_seconds']:.1f}/"
            f"{TARGET_SECONDS}s | Completed: {result['completed']}"
        )
        print("SnapFit AI Plank Coach stopped.")


def save_result(held_seconds):
    result = {
        "exercise": "Plank",
        "reps": 0,
        "duration_seconds": round(max(0.0, held_seconds), 2),
        "completed": held_seconds >= TARGET_SECONDS,
    }

    try:
        os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
        with open(RESULT_FILE, "w", encoding="utf-8") as result_file:
            json.dump(result, result_file, indent=4)
    except OSError as error:
        print(f"ERROR: Could not save plank result: {error}")

    return result

if __name__ == "__main__":
    main()