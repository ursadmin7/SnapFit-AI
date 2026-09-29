# Snapdragon AI Lab Build & Present

## Project Pitch

SnapFit AI is a private, on-device fitness coach that turns webcam pose landmarks into simple rep counts, plank timing, form cues, and locally stored workout progress.

## Implemented

- MediaPipe Tasks Pose Landmarker and real-time webcam processing.
- Squat, push-up, and plank exercise analysis using detected landmarks and angles.
- Feedback HUDs, target checks, retry flow, full-workout ordering, dashboard, and local JSON progress.
- No camera/video upload path in the application.

## Snapdragon Positioning

Snapdragon-powered Windows PCs are the intended optimization target. Current code performs on-device inference, but this implementation has not demonstrated Qualcomm NPU execution. Qualcomm AI Hub model optimization, NPU runtime integration, and hardware-specific benchmarking remain future deployment work.

## Demo Claims and Evidence

Demonstrate actual webcam-derived values and the locally persisted result/history. Do not claim medical accuracy, injury prevention, NPU use, or performance figures. There is no recorded benchmark yet; benchmarking is pending.

## Next Milestones

1. Collect repeatable baseline measurements on named Windows hardware.
2. Evaluate Qualcomm AI Hub compatibility and the supported NPU execution path.
3. Validate pose quality and latency against the CPU baseline.
4. Publish only reproducible measurements and clearly identify the hardware/runtime used.