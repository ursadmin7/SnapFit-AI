import math
from collections import deque


# ============================================================
# MEDIAPIPE LANDMARKS
# ============================================================

LEFT_HIP = 23
LEFT_KNEE = 25
LEFT_ANKLE = 27

RIGHT_HIP = 24
RIGHT_KNEE = 26
RIGHT_ANKLE = 28


# ============================================================
# SETTINGS
# ============================================================

SMOOTHING_FRAMES = 7

MIN_VISIBILITY = 0.35

CALIBRATION_FRAMES = 60

DOWN_DROP = 35

UP_DROP = 15

MIN_DOWN_FRAMES = 4

MIN_UP_FRAMES = 4


# ============================================================
# ANGLE
# ============================================================

def calculate_angle(a, b, c):

    ba_x = a.x - b.x
    ba_y = a.y - b.y

    bc_x = c.x - b.x
    bc_y = c.y - b.y

    dot = (
        ba_x * bc_x +
        ba_y * bc_y
    )

    magnitude_ba = math.sqrt(
        ba_x ** 2 +
        ba_y ** 2
    )

    magnitude_bc = math.sqrt(
        bc_x ** 2 +
        bc_y ** 2
    )

    if magnitude_ba == 0 or magnitude_bc == 0:
        return None

    cosine = dot / (
        magnitude_ba * magnitude_bc
    )

    cosine = max(
        -1.0,
        min(1.0, cosine)
    )

    return math.degrees(
        math.acos(cosine)
    )


# ============================================================
# LANDMARK VALIDATION
# ============================================================

def valid_landmark(landmark):

    if landmark is None:
        return False

    visibility = getattr(
        landmark,
        "visibility",
        1.0
    )

    return visibility >= MIN_VISIBILITY


# ============================================================
# GET LANDMARK
# ============================================================

def get_landmark(landmarks, index):

    if landmarks is None:
        return None

    if index >= len(landmarks):
        return None

    landmark = landmarks[index]

    if not valid_landmark(landmark):
        return None

    return landmark


# ============================================================
# LEFT KNEE
# ============================================================

def get_left_knee_angle(landmarks):

    hip = get_landmark(
        landmarks,
        LEFT_HIP
    )

    knee = get_landmark(
        landmarks,
        LEFT_KNEE
    )

    ankle = get_landmark(
        landmarks,
        LEFT_ANKLE
    )

    if hip is None or knee is None or ankle is None:
        return None

    return calculate_angle(
        hip,
        knee,
        ankle
    )


# ============================================================
# RIGHT KNEE
# ============================================================

def get_right_knee_angle(landmarks):

    hip = get_landmark(
        landmarks,
        RIGHT_HIP
    )

    knee = get_landmark(
        landmarks,
        RIGHT_KNEE
    )

    ankle = get_landmark(
        landmarks,
        RIGHT_ANKLE
    )

    if hip is None or knee is None or ankle is None:
        return None

    return calculate_angle(
        hip,
        knee,
        ankle
    )


# ============================================================
# AVERAGE KNEE ANGLE
# ============================================================

def get_average_knee_angle(landmarks):

    left = get_left_knee_angle(
        landmarks
    )

    right = get_right_knee_angle(
        landmarks
    )

    angles = []

    if left is not None:
        angles.append(left)

    if right is not None:
        angles.append(right)

    if not angles:
        return None

    return sum(angles) / len(angles)


# ============================================================
# SQUAT ANALYZER
# ============================================================

class SquatAnalyzer:

    def __init__(self):

        self.reps = 0

        self.stage = "CALIBRATING"

        self.current_angle = None

        self.smoothed_angle = None

        self.angle_history = deque(
            maxlen=SMOOTHING_FRAMES
        )

        self.calibration_angles = []

        self.baseline_angle = None

        self.down_threshold = None

        self.up_threshold = None

        self.down_frames = 0

        self.up_frames = 0

        self.form_feedback = (
            "Stand normally"
        )

        self.depth_reached = False


    # ========================================================
    # SMOOTHING
    # ========================================================

    def smooth_angle(self, angle):

        self.angle_history.append(
            angle
        )

        return (
            sum(self.angle_history)
            /
            len(self.angle_history)
        )


    # ========================================================
    # CALIBRATION
    # ========================================================

    def calibrate(self, angle):

        self.calibration_angles.append(
            angle
        )

        if len(
            self.calibration_angles
        ) >= CALIBRATION_FRAMES:

            self.baseline_angle = (
                sum(
                    self.calibration_angles
                )
                /
                len(
                    self.calibration_angles
                )
            )

            self.down_threshold = (
                self.baseline_angle
                - DOWN_DROP
            )

            self.up_threshold = (
                self.baseline_angle
                - UP_DROP
            )

            self.stage = "UP"

            self.form_feedback = (
                "Calibration complete"
            )

            return True

        return False


    # ========================================================
    # UPDATE
    # ========================================================

    def update(self, landmarks):

        angle = get_average_knee_angle(
            landmarks
        )

        if angle is None:

            self.current_angle = None

            self.form_feedback = (
                "Show hips, knees and ankles"
            )

            return self.get_result()


        self.current_angle = angle

        self.smoothed_angle = (
            self.smooth_angle(angle)
        )

        angle = self.smoothed_angle


        # ====================================================
        # CALIBRATION
        # ====================================================

        if self.baseline_angle is None:

            self.calibrate(angle)

            progress = int(
                (
                    len(
                        self.calibration_angles
                    )
                    /
                    CALIBRATION_FRAMES
                )
                * 100
            )

            self.form_feedback = (
                f"Calibrating... {progress}%"
            )

            return self.get_result()


        # ====================================================
        # DOWN
        # ====================================================

        if angle <= self.down_threshold:

            self.down_frames += 1

            self.up_frames = 0

            if (
                self.down_frames
                >= MIN_DOWN_FRAMES
            ):

                self.stage = "DOWN"

                self.depth_reached = True

                self.form_feedback = (
                    "Good depth"
                )


        # ====================================================
        # MIDDLE
        # ====================================================

        elif angle < self.up_threshold:

            self.up_frames = 0

            if self.stage == "DOWN":

                self.form_feedback = (
                    "Keep moving up"
                )

            else:

                self.form_feedback = (
                    "Go lower"
                )


        # ====================================================
        # UP
        # ====================================================

        else:

            self.up_frames += 1

            self.down_frames = 0

            if (
                self.stage == "DOWN"
                and
                self.depth_reached
                and
                self.up_frames
                >= MIN_UP_FRAMES
            ):

                self.reps += 1

                self.stage = "UP"

                self.depth_reached = False

                self.form_feedback = (
                    "Good rep!"
                )

            elif self.stage == "UP":

                self.form_feedback = (
                    "Ready"
                )


        return self.get_result()


    # ========================================================
    # RESULT
    # ========================================================

    def get_result(self):

        return {

            "angle": (
                round(
                    self.smoothed_angle,
                    1
                )
                if self.smoothed_angle is not None
                else None
            ),

            "reps": self.reps,

            "stage": self.stage,

            "feedback": self.form_feedback,

            "baseline": (
                round(
                    self.baseline_angle,
                    1
                )
                if self.baseline_angle is not None
                else None
            ),

            "down_threshold": (
                round(
                    self.down_threshold,
                    1
                )
                if self.down_threshold is not None
                else None
            ),

            "up_threshold": (
                round(
                    self.up_threshold,
                    1
                )
                if self.up_threshold is not None
                else None
            )
        }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "SnapFit AI Squat Analyzer"
    )

    print(
        "=========================="
    )

    print()

    print(
        "Adaptive squat analyzer loaded."
    )

    print()

    print(
        "Features:"
    )

    print(
        "- Adaptive calibration"
    )

    print(
        "- Knee angle smoothing"
    )

    print(
        "- Landmark visibility filtering"
    )

    print(
        "- Relative squat detection"
    )

    print(
        "- DOWN/UP state machine"
    )

    print(
        "- Rep validation"
    )

    print(
        "- False-rep protection"
    )