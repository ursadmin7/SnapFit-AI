import json
import os
from datetime import datetime


# ============================================================
# SNAPFIT AI - PROGRESS TRACKER
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")

PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")
WORKOUTS_FILE = os.path.join(DATA_DIR, "workouts.json")


# ============================================================
# DEFAULT DATA
# ============================================================

DEFAULT_PROGRESS = {
    "total_workouts": 0,
    "completed_workouts": 0,
    "total_workout_attempts": 0,
    "total_squats": 0,
    "total_pushups": 0,
    "total_plank_seconds": 0,
    "total_duration_seconds": 0,
    "total_calories": 0,
    "best_workout_duration": None,
    "last_workout": None
}


# ============================================================
# FILE MANAGEMENT
# ============================================================

def ensure_data_directory():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json(file_path, default_data):
    ensure_data_directory()

    if not os.path.exists(file_path):
        return default_data.copy() if isinstance(default_data, dict) else list(default_data)

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(default_data, dict) and isinstance(data, dict):
                return {**default_data, **data}
            if isinstance(default_data, list) and isinstance(data, list):
                return data
            return default_data.copy() if isinstance(default_data, dict) else list(default_data)

    except (json.JSONDecodeError, OSError):
        return default_data.copy() if isinstance(default_data, dict) else list(default_data)


def save_json(file_path, data):
    ensure_data_directory()

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


# ============================================================
# PROGRESS TRACKER
# ============================================================

class ProgressTracker:

    def __init__(self):
        self.progress = load_json(
            PROGRESS_FILE,
            DEFAULT_PROGRESS
        )

        self.workouts = load_json(
            WORKOUTS_FILE,
            []
        )
        self.progress["total_workouts"] = int(
            self.progress.get("total_workouts", 0)
        )
        self.progress["completed_workouts"] = max(
            int(self.progress.get("completed_workouts", 0)),
            self.progress["total_workouts"],
        )
        self.progress["total_workout_attempts"] = max(
            int(self.progress.get("total_workout_attempts", 0)),
            len(self.workouts),
        )

    # --------------------------------------------------------
    # RECORD WORKOUT
    # --------------------------------------------------------

    def record_workout(self, session):

        squat_count = 0
        pushup_count = 0
        plank_seconds = 0

        for exercise in session.exercises:

            name = exercise.name.lower()

            if "squat" in name:
                squat_count += exercise.completed_reps

            elif "push" in name:
                pushup_count += exercise.completed_reps

            elif "plank" in name:
                plank_seconds += exercise.completed_seconds

        duration = session.duration_seconds()

        if duration is None:
            duration = 0

        calories = self.estimate_calories(
            session,
            duration
        )

        workout_record = {
            "workout_name": session.workout_name,
            "date": datetime.now().isoformat(timespec="seconds"),
            "duration_seconds": round(duration, 2),
            "completed": bool(getattr(session, "completed", False)),
            "squats": squat_count,
            "pushups": pushup_count,
            "plank_seconds": plank_seconds,
            "calories": calories
        }

        self.workouts.append(workout_record)

        # Update totals
        self.progress["total_workout_attempts"] += 1
        if workout_record["completed"]:
            self.progress["total_workouts"] += 1
            self.progress["completed_workouts"] += 1
        self.progress["total_squats"] += squat_count
        self.progress["total_pushups"] += pushup_count
        self.progress["total_plank_seconds"] += plank_seconds
        self.progress["total_duration_seconds"] += duration
        self.progress["total_calories"] += calories

        # Best workout duration
        best = self.progress["best_workout_duration"]

        if best is None or duration < best:
            self.progress["best_workout_duration"] = round(
                duration,
                2
            )

        self.progress["last_workout"] = workout_record["date"]

        # Save everything
        save_json(
            PROGRESS_FILE,
            self.progress
        )

        save_json(
            WORKOUTS_FILE,
            self.workouts
        )

        return workout_record

    # --------------------------------------------------------
    # CALORIE ESTIMATION
    # --------------------------------------------------------

    def estimate_calories(self, session, duration):

        # Simple approximate estimate.
        # Later this can be replaced with a personalized model.

        minutes = duration / 60

        calories = minutes * 5

        return round(calories, 1)

    # --------------------------------------------------------
    # DISPLAY PROGRESS
    # --------------------------------------------------------

    def display_progress(self):

        print()
        print("=" * 60)
        print("SNAPFIT AI - YOUR PROGRESS")
        print("=" * 60)

        print()

        print(
            f"Total Workouts       : "
            f"{self.progress['total_workouts']}"
        )

        print(
            f"Workout Attempts    : "
            f"{self.progress['total_workout_attempts']}"
        )

        print(
            f"Total Squats         : "
            f"{self.progress['total_squats']}"
        )

        print(
            f"Total Push-Ups       : "
            f"{self.progress['total_pushups']}"
        )

        print(
            f"Total Plank Time     : "
            f"{self.progress['total_plank_seconds']} seconds"
        )

        print(
            f"Total Calories       : "
            f"{self.progress['total_calories']} kcal"
        )

        total_duration = self.progress[
            "total_duration_seconds"
        ]

        print(
            f"Total Workout Time   : "
            f"{round(total_duration / 60, 1)} minutes"
        )

        best = self.progress["best_workout_duration"]

        if best is not None:
            print(
                f"Best Workout Time    : "
                f"{best} seconds"
            )

        print()

        print("=" * 60)


# ============================================================
# TEST
# ============================================================

def main():

    print()
    print("=" * 60)
    print("SNAPFIT AI - PROGRESS TRACKER")
    print("=" * 60)

    tracker = ProgressTracker()

    print()
    print("Progress system initialized successfully.")

    tracker.display_progress()

    print()
    print("Data directory:")
    print(DATA_DIR)

    print()
    print("Progress file:")
    print(PROGRESS_FILE)

    print()
    print("Workout history:")
    print(WORKOUTS_FILE)


if __name__ == "__main__":
    main()