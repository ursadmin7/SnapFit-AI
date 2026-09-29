import cv2
import time
import math
import os
import json
from collections import deque

from mediapipe.tasks import python
import mediapipe as mp
from mediapipe.tasks.python import vision


# ============================================================
# SNAPFIT AI - REAL-TIME SQUAT COACH
# ============================================================

MODEL_PATH = "models/pose_landmarker_full.task"
CAMERA_INDEX = 0
WINDOW_NAME = "SnapFit AI - Squat Coach"

TARGET_REPS = 10

# More forgiving thresholds for normal webcam positioning.
MIN_VISIBILITY = 0.30
SMOOTHING_FRAMES = 5
DOWN_ANGLE = 130
UP_ANGLE = 155
MIN_REP_TIME = 0.50

LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28


def calculate_angle(a, b, c):
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])

    mag_ba = math.hypot(ba[0], ba[1])
    mag_bc = math.hypot(bc[0], bc[1])

    if mag_ba == 0 or mag_bc == 0:
        return None

    cosine = (ba[0] * bc[0] + ba[1] * bc[1]) / (mag_ba * mag_bc)
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))


def landmark_visible(landmark):
    return getattr(landmark, "visibility", 1.0) >= MIN_VISIBILITY


class SquatAnalyzer:
    def __init__(self):
        self.reps = 0
        self.stage = "UP"
        self.feedback = "Stand upright"
        self.angle_history = deque(maxlen=SMOOTHING_FRAMES)
        self.last_rep_time = 0.0
        self.started_at = time.time()
        self.completed = False
        self.current_angle = None

    def smooth_angle(self, angle):
        if angle is None:
            return None

        self.angle_history.append(angle)
        return sum(self.angle_history) / len(self.angle_history)

    def update(self, angle):
        angle = self.smooth_angle(angle)
        self.current_angle = angle

        if angle is None:
            self.feedback = "Move into camera view"
            return

        if angle < DOWN_ANGLE:
            self.stage = "DOWN"
            self.feedback = "Good depth"

        elif angle > UP_ANGLE:
            if self.stage == "DOWN":
                now = time.time()

                if now - self.last_rep_time >= MIN_REP_TIME:
                    self.reps += 1
                    self.last_rep_time = now

                    if self.reps >= TARGET_REPS:
                        self.completed = True
                        self.feedback = "TARGET COMPLETE"
                    else:
                        self.feedback = "Good rep"

            self.stage = "UP"

        else:
            if self.stage == "UP":
                self.feedback = "Squat down"
            else:
                self.feedback = "Stand up"

    def result(self):
        return {
            "exercise": "Squat",
            "reps": self.reps,
            "duration_seconds": round(time.time() - self.started_at, 2),
            "completed": self.completed,
        }


def create_landmarker():
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)

    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.40,
        min_pose_presence_confidence=0.40,
        min_tracking_confidence=0.40,
    )

    return vision.PoseLandmarker.create_from_options(options)


def main():
    print()
    print("Initializing SnapFit AI Squat Coach...")
    print(f"Target: {TARGET_REPS} squats")

    landmarker = create_landmarker()
    camera = cv2.VideoCapture(CAMERA_INDEX)

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

    if not camera.isOpened():
        print("ERROR: Could not open camera.")
        landmarker.close()
        return {
            "exercise": "Squat",
            "reps": 0,
            "duration_seconds": 0,
            "completed": False,
        }

    analyzer = SquatAnalyzer()

    print()
    print("Squat AI Detection Started.")
    print("Stand far enough back for your full body to be visible.")
    print("Complete the target reps.")
    print("Press Q or ESC to stop.")

    start_time = time.time()

    try:
        while True:
            success, frame = camera.read()

            if not success:
                break

            frame = cv2.flip(frame, 1)

            timestamp_ms = int((time.time() - start_time) * 1000)

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=frame,
            )

            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            angle = None

            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]

                left_hip = landmarks[LEFT_HIP]
                left_knee = landmarks[LEFT_KNEE]
                left_ankle = landmarks[LEFT_ANKLE]

                right_hip = landmarks[RIGHT_HIP]
                right_knee = landmarks[RIGHT_KNEE]
                right_ankle = landmarks[RIGHT_ANKLE]

                angles = []

                if (
                    landmark_visible(left_hip)
                    and landmark_visible(left_knee)
                    and landmark_visible(left_ankle)
                ):
                    value = calculate_angle(
                        (left_hip.x, left_hip.y),
                        (left_knee.x, left_knee.y),
                        (left_ankle.x, left_ankle.y),
                    )
                    if value is not None:
                        angles.append(value)

                if (
                    landmark_visible(right_hip)
                    and landmark_visible(right_knee)
                    and landmark_visible(right_ankle)
                ):
                    value = calculate_angle(
                        (right_hip.x, right_hip.y),
                        (right_knee.x, right_knee.y),
                        (right_ankle.x, right_ankle.y),
                    )
                    if value is not None:
                        angles.append(value)

                if angles:
                    # If both legs are visible, average them.
                    # If only one is reliable, use the available leg.
                    angle = sum(angles) / len(angles)
                    analyzer.update(angle)
                else:
                    analyzer.update(None)
            else:
                analyzer.update(None)

            # HUD
            cv2.rectangle(frame, (0, 0), (960, 155), (20, 20, 20), -1)

            cv2.putText(
                frame,
                "SNAPFIT AI - SQUAT COACH",
                (25, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (255, 255, 255),
                2,
            )

            cv2.putText(
                frame,
                f"REPS: {analyzer.reps}/{TARGET_REPS}",
                (25, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )

            cv2.putText(
                frame,
                f"STAGE: {analyzer.stage}",
                (300, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )

            cv2.putText(
                frame,
                f"TIME: {time.time() - analyzer.started_at:.1f}s",
                (570, 115),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

            angle_text = (
                f"KNEE ANGLE: {analyzer.current_angle:.1f}"
                if analyzer.current_angle is not None
                else "KNEE ANGLE: --"
            )

            cv2.putText(
                frame,
                angle_text,
                (570, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

            cv2.putText(
                frame,
                analyzer.feedback,
                (25, 115),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

            cv2.putText(
                frame,
                "DOWN < 130   |   UP > 155",
                (25, 145),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1,
            )

            if analyzer.completed:
                cv2.putText(
                    frame,
                    "TARGET COMPLETE!",
                    (300, 205),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (255, 255, 255),
                    3,
                )

                cv2.imshow(WINDOW_NAME, frame)
                cv2.waitKey(1200)
                break

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:
                print("Exit requested.")
                break

            if cv2.getWindowProperty(
                WINDOW_NAME, cv2.WND_PROP_VISIBLE
            ) < 1:
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()
        landmarker.close()

    result = analyzer.result()

    print()
    print("=" * 50)
    print("SQUAT AI RESULT")
    print("=" * 50)
    print(f"Exercise: {result['exercise']}")
    print(f"Reps: {result['reps']}/{TARGET_REPS}")
    print(f"Duration: {result['duration_seconds']} seconds")
    print(f"Completed: {result['completed']}")
    print("=" * 50)

    return result


if __name__ == "__main__":

    result = main()

    # Save the actual AI result so the workout system
    # can read it instead of assuming the exercise
    # was completed just because the program exited.

    project_root = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )

    result_file = os.path.join(
        project_root,
        "data",
        "exercise_result.json"
    )

    os.makedirs(
        os.path.dirname(result_file),
        exist_ok=True
    )

    with open(
        result_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            indent=4
        )

    print()
    print("AI result saved successfully.")