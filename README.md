# SnapFit AI

SnapFit AI is a privacy-first fitness coach for Windows PCs. It uses the MediaPipe Tasks Pose Landmarker and a local webcam to estimate exercise form, count repetitions, time valid plank holds, and save workout progress on the device.

## Problem

People exercising at home often lack immediate, repeatable feedback about movement and session progress. Sending camera video to a remote service is unnecessary for this MVP and creates avoidable privacy concerns.

## Solution

SnapFit AI runs pose inference and exercise analysis locally. Its camera coaches provide feedback from detected body landmarks and store only exercise results and workout history in local JSON files.

## Features

- Local real-time pose processing with MediaPipe Tasks and OpenCV.
- Squat and push-up rep tracking from measured joint angles.
- Plank timing while the detected body alignment meets the analyzer's thresholds.
- Dashboard for individual exercises and the ordered full workout.
- Actual-result target checks, retry prompts, summaries, and persistent progress.
- No video upload or remote inference.

## Architecture

The Tkinter dashboard presents workout choices and local progress. `WorkoutManager` creates the selected workout; `ExerciseRunner` clears the prior result and launches the existing OpenCV analyzer in a child process. Each analyzer writes `data/exercise_result.json`. The session validates its observed count or hold time before advancing. `ProgressTracker` appends the attempt to `data/workouts.json` and updates aggregate values in `data/progress.json`.

The full workout order and targets are Squat (10 reps), Push-Up (8 reps), then Plank (30 seconds). Individual exercise choices use those same targets.

## AI Pipeline

1. OpenCV reads webcam frames locally.
2. Frames are converted to MediaPipe images and passed to the Pose Landmarker in video mode.
3. Exercise logic evaluates visible landmarks and measurements: knee angle for squats, elbow angle and shoulder-hip-ankle alignment for push-ups, and body-line/hip angles for planks.
4. The analyzer draws a local HUD with progress and measurement-based feedback.
5. Actual detected counts and valid-hold duration are written to the local exercise-result file.

## Installation

Use Python 3.10 or newer on Windows and ensure Tkinter is included with the Python installation. The model file must exist at `models/pose_landmarker_full.task`.

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The repository's existing `.venv` can be used directly. Requirements name the currently installed MediaPipe Tasks and OpenCV packages; no runtime upgrade is required to run the existing environment.

## How to Run

From the project root:

```powershell
python ai/coach/workout_session.py
```

The existing terminal interface remains available as a fallback if the desktop dashboard cannot initialize. The dashboard also runs directly with `python app/dashboard.py`.

During exercise, stand where the required landmarks are visible. Close the camera window or press Q/Esc to end an attempt. An attempt that ends before its actual target remains incomplete and can be retried; it is never marked complete merely because the camera closes.

## Project Structure

```text
ai/coach/       Workout orchestration, exercise runner, and local progress storage
ai/exercise/    Squat, push-up, and plank camera analyzers
ai/pose/        Pose Landmarker camera verification utility
app/            Tkinter dashboard
data/           Local exercise result, aggregate progress, and workout history
docs/           Architecture, performance, demo, competition, and final status
models/         MediaPipe Pose Landmarker task model
tests/          Offline workout pipeline tests
```

## Privacy

Camera frames are processed on the local PC and are not uploaded by this application. The app stores workout counts, durations, completion status, and timestamps in local JSON files. Keep the project data directory on a device and account you trust.

AI fitness guidance is for general informational purposes. Exercise within your limits.

## Snapdragon Optimization Strategy

Implemented today: local MediaPipe pose detection, webcam processing, exercise analysis, feedback, and local workout tracking. The application does not currently demonstrate Qualcomm NPU execution. MediaPipe's configured delegate/provider behavior has not been benchmarked or verified as Snapdragon NPU acceleration.

Future work: evaluate model conversion and optimization with Qualcomm AI Hub, integrate a supported Snapdragon NPU runtime/provider, and compare CPU/GPU/NPU latency and power on specified hardware. Report measurements only after repeatable device tests.

## Limitations

- Camera position, lighting, occlusion, clothing, and individual movement can affect landmark accuracy and thresholds.
- Current pose/form thresholds are heuristic coaching signals, not medical or injury-prevention advice.
- Push-up analysis tracks the person nearest the frame center; multi-person workouts are not a supported workflow.
- Results are local JSON files and are not synchronized between devices.
- No performance benchmark has been recorded; benchmarking is pending.

## Future Improvements

- Add automated webcam-independent analyzer tests and repeatable hardware benchmarks.
- Improve calibration, side-view guidance, and pose-loss recovery.
- Evaluate Qualcomm AI Hub optimization and Snapdragon hardware-specific inference only on compatible hardware.
- Add export/backup controls for locally stored progress.