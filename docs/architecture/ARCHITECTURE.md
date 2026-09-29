# Architecture

## Runtime Flow

`workout_session.py` is the root launch command and opens `app/dashboard.py`. The dashboard uses the existing workout manager, runner, and progress tracker; it does not implement pose detection. The dashboard starts a worker thread for the workout so its controls remain responsive while the analyzer child process owns the webcam.

```text
Dashboard
  -> WorkoutManager creates a single-exercise or Full Workout session
  -> ExerciseRunner removes stale exercise_result.json
  -> squat_live.py / pushup_live.py / plank_live.py runs as a child process
  -> MediaPipe Pose Landmarker detects local webcam landmarks
  -> Analyzer measures exercise state and renders feedback
  -> exercise_result.json contains observed reps, duration, and completion
  -> WorkoutSession checks result against the configured target
  -> ProgressTracker appends the attempt and updates local aggregates
```

## Ownership

- `ai/exercise/`: MediaPipe Tasks model setup, OpenCV camera lifecycle, landmark measurements, HUD, and actual exercise result output.
- `ai/coach/exercise_runner.py`: child-process launch, stale-result clearing, result validation, and process/missing-file errors.
- `ai/coach/workout_session.py`: workout presets, target comparison, retries, ordering, and summary.
- `ai/coach/progress_tracker.py`: backwards-compatible JSON loading and local history/aggregate persistence.
- `app/dashboard.py`: exercise selection, progress display, recent workout attempts, retry interaction, and summary.

## Data and Failure Behavior

The result file is a single local handoff between a sequential analyzer process and the session. It is deleted before each launch. Invalid or missing output cannot be accepted as completion. Process failures become an incomplete result where possible. Camera/model errors remain incomplete and cannot advance the workout. Progress and history JSON are stored under `data/`; existing history is loaded before appending.

All inference and camera processing are local. The current code does not configure or claim a Qualcomm NPU delegate. Qualcomm AI Hub conversion, provider integration, and hardware validation are future work.