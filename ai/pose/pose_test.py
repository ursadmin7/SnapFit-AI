import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = "models/pose_landmarker_full.task"
WINDOW_NAME = "SnapFit AI - Pose Detection"


# ============================================================
# CREATE POSE LANDMARKER
# ============================================================

print("Loading SnapFit AI Pose Landmarker...")

base_options = python.BaseOptions(
    model_asset_path=MODEL_PATH
)

options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.IMAGE,
    num_poses=1
)

try:
    detector = vision.PoseLandmarker.create_from_options(options)
except Exception as error:
    print()
    print("ERROR: Could not load Pose Landmarker.")
    print(error)
    raise SystemExit(1)

print("Pose Landmarker loaded successfully.")


# ============================================================
# OPEN WEBCAM
# ============================================================

print("Opening webcam...")

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("ERROR: Could not open webcam.")
    detector.close()
    raise SystemExit(1)


# Try to use a reasonable camera resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)


# ============================================================
# CREATE WINDOW
# ============================================================

cv2.namedWindow(
    WINDOW_NAME,
    cv2.WINDOW_NORMAL
)

cv2.resizeWindow(
    WINDOW_NAME,
    1280,
    720
)


print()
print("==========================================")
print("SnapFit AI Pose Detection Started")
print("==========================================")
print("Show your full body to the camera.")
print()
print("Press Q or ESC to quit.")
print("You can also CLOSE the camera window.")
print()


# ============================================================
# MEDIAPIPE DRAWING CONNECTIONS
# ============================================================

# MediaPipe Pose landmark connections
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),

    (9, 10),

    (11, 12),

    (11, 13), (13, 15),
    (15, 17), (15, 19), (15, 21),
    (17, 19),

    (12, 14), (14, 16),
    (16, 18), (16, 20), (16, 22),
    (18, 20),

    (11, 23),
    (12, 24),

    (23, 24),

    (23, 25),
    (25, 27),
    (27, 29),
    (27, 31),
    (29, 31),

    (24, 26),
    (26, 28),
    (28, 30),
    (28, 32),
    (30, 32)
]


# ============================================================
# MAIN CAMERA LOOP
# ============================================================

try:

    while True:

        # ----------------------------------------------------
        # Read camera frame
        # ----------------------------------------------------

        success, frame = cap.read()

        if not success:
            print("ERROR: Could not read webcam frame.")
            break


        # ----------------------------------------------------
        # Flip camera horizontally
        # ----------------------------------------------------

        frame = cv2.flip(frame, 1)


        # ----------------------------------------------------
        # Get frame dimensions
        # ----------------------------------------------------

        height, width = frame.shape[:2]


        # ----------------------------------------------------
        # Convert BGR → RGB
        # ----------------------------------------------------

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )


        # ----------------------------------------------------
        # Create MediaPipe Image
        # ----------------------------------------------------

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )


        # ----------------------------------------------------
        # Run Pose AI
        # ----------------------------------------------------

        result = detector.detect(mp_image)


        # ----------------------------------------------------
        # Count detected poses
        # ----------------------------------------------------

        pose_count = len(result.pose_landmarks)


        # ----------------------------------------------------
        # Draw detected body
        # ----------------------------------------------------

        if pose_count > 0:

            landmarks = result.pose_landmarks[0]


            # -----------------------------------------------
            # Draw connections
            # -----------------------------------------------

            for start_index, end_index in POSE_CONNECTIONS:

                start = landmarks[start_index]
                end = landmarks[end_index]

                start_x = int(start.x * width)
                start_y = int(start.y * height)

                end_x = int(end.x * width)
                end_y = int(end.y * height)

                cv2.line(
                    frame,
                    (start_x, start_y),
                    (end_x, end_y),
                    (0, 255, 0),
                    3
                )


            # -----------------------------------------------
            # Draw landmarks
            # -----------------------------------------------

            for index, landmark in enumerate(landmarks):

                x = int(landmark.x * width)
                y = int(landmark.y * height)

                # Ignore points outside the image
                if (
                    x < 0
                    or x >= width
                    or y < 0
                    or y >= height
                ):
                    continue

                cv2.circle(
                    frame,
                    (x, y),
                    6,
                    (0, 0, 255),
                    -1
                )


            # -----------------------------------------------
            # Display landmark count
            # -----------------------------------------------

            cv2.putText(
                frame,
                f"Landmarks: {len(landmarks)}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2
            )


            # -----------------------------------------------
            # Display detection status
            # -----------------------------------------------

            cv2.putText(
                frame,
                "POSE DETECTED",
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

        else:

            cv2.putText(
                frame,
                "NO POSE DETECTED",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 0, 255),
                2
            )


        # ----------------------------------------------------
        # Display pose count
        # ----------------------------------------------------

        cv2.putText(
            frame,
            f"People: {pose_count}",
            (20, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        # ----------------------------------------------------
        # Display instructions
        # ----------------------------------------------------

        cv2.putText(
            frame,
            "Q / ESC = Quit",
            (20, height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )


        # ----------------------------------------------------
        # Show frame
        # ----------------------------------------------------

        cv2.imshow(
            WINDOW_NAME,
            frame
        )


        # ----------------------------------------------------
        # Keyboard handling
        # ----------------------------------------------------

        key = cv2.waitKey(1) & 0xFF

        # Q
        if key == ord("q") or key == ord("Q"):
            print("Q pressed. Closing...")
            break

        # ESC
        if key == 27:
            print("ESC pressed. Closing...")
            break

        # Window X button
        try:

            window_status = cv2.getWindowProperty(
                WINDOW_NAME,
                cv2.WND_PROP_VISIBLE
            )

            if window_status < 1:
                print("Camera window closed.")
                break

        except cv2.error:
            break


# ============================================================
# HANDLE CTRL+C
# ============================================================

except KeyboardInterrupt:

    print()
    print("Program interrupted by user.")


# ============================================================
# CLEANUP
# ============================================================

finally:

    print("Cleaning up...")

    cap.release()

    detector.close()

    cv2.destroyAllWindows()

    # Give Windows time to close the OpenCV window
    cv2.waitKey(1)

    print("SnapFit AI Pose Detection stopped.")