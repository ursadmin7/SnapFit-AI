import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai.coach import exercise_runner, progress_tracker
from ai.coach.workout_session import Exercise, WorkoutSession


class WorkoutPipelineTests(unittest.TestCase):
    def test_workout_session_only_advances_on_real_target_values(self):
        session = WorkoutSession("Test", [Exercise("Squat", target_reps=10)])
        exercise = session.current_exercise()

        exercise.completed_reps = 9
        exercise.completed = False
        self.assertFalse(session.complete_current_exercise({"reps": 9, "duration_seconds": 5}))
        self.assertEqual(session.current_index, 0)

        self.assertTrue(session.complete_current_exercise({
            "reps": 10,
            "duration_seconds": 12,
            "completed": True,
        }))
        self.assertEqual(session.current_index, 1)
        self.assertEqual(exercise.completed_reps, 10)

    def test_runner_handles_missing_and_invalid_result_json(self):
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "exercise_result.json"
            with patch.object(exercise_runner, "RESULT_FILE", str(result_path)):
                runner = exercise_runner.ExerciseRunner()
                self.assertIsNone(runner.read_result())
                result_path.write_text("{bad json", encoding="utf-8")
                self.assertIsNone(runner.read_result())

    def test_progress_appends_attempts_and_keeps_existing_records(self):
        with tempfile.TemporaryDirectory() as directory:
            progress_path = Path(directory) / "progress.json"
            workouts_path = Path(directory) / "workouts.json"
            workouts_path.write_text(
                json.dumps([{"workout_name": "Earlier", "completed": True}]),
                encoding="utf-8",
            )
            with (
                patch.object(progress_tracker, "PROGRESS_FILE", str(progress_path)),
                patch.object(progress_tracker, "WORKOUTS_FILE", str(workouts_path)),
            ):
                tracker = progress_tracker.ProgressTracker()
                session = WorkoutSession("Partial", [Exercise("Squat", target_reps=10)])
                session.started_at = 100.0
                session.ended_at = 112.0
                session.exercises[0].completed_reps = 4
                session.completed = False
                tracker.record_workout(session)

                saved_workouts = json.loads(workouts_path.read_text(encoding="utf-8"))
                saved_progress = json.loads(progress_path.read_text(encoding="utf-8"))
                self.assertEqual(len(saved_workouts), 2)
                self.assertFalse(saved_workouts[-1]["completed"])
                self.assertEqual(saved_workouts[-1]["squats"], 4)
                self.assertEqual(saved_progress["total_squats"], 4)
                self.assertEqual(saved_progress["total_workouts"], 0)
                self.assertEqual(saved_progress["total_workout_attempts"], 2)


if __name__ == "__main__":
    unittest.main()