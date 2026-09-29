import cv2
import time

camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not camera.isOpened():
    print("ERROR: Could not open webcam.")
    exit()

print("Webcam opened successfully.")
print("Reading camera frames...")

frame_count = 0
start_time = time.time()

while True:
    success, frame = camera.read()

    if not success:
        print("ERROR: Camera opened, but no frame was received.")
        break

    frame_count += 1

    cv2.putText(
        frame,
        f"Frames: {frame_count}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow("SnapFit AI - Camera Test", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

elapsed = time.time() - start_time

camera.release()
cv2.destroyAllWindows()

print(f"Frames received: {frame_count}")

if elapsed > 0:
    print(f"Approx FPS: {frame_count / elapsed:.2f}")

print("Camera test finished.")