# Competition Demo Flow

1. Start the app from the project root with `python ai/coach/workout_session.py`.
2. Show the dashboard's current local totals, recent history, exercise targets, and privacy notice.
3. Select Squat, Push-Up, Plank, or Full Workout. The full workout runs in this order: 10 squats, 8 push-ups, then a 30-second plank.
4. Grant Windows camera access if prompted and position the body so the analyzer can observe the required landmarks.
5. Demonstrate the analyzer's live measurement/progress and pose-derived form feedback. Press Q/Esc or close the camera to end the attempt.
6. Complete the target to advance. An incomplete attempt offers a retry; declining records an incomplete attempt with the actual measured values.
7. Review the workout summary, dashboard totals, and recent attempt after the camera closes.

Frames are processed locally. Do not present this build as Snapdragon NPU-accelerated: Qualcomm AI Hub optimization and device-specific benchmarks are future work. Current benchmark status: pending.