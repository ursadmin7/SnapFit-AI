import time
import os
import sys
import tkinter as tk

from dataclasses import dataclass

try:
    from .progress_tracker import ProgressTracker
    from .exercise_runner import ExerciseRunner
except ImportError:
    from progress_tracker import ProgressTracker
    from exercise_runner import ExerciseRunner


# ============================================================
# SNAPFIT AI - WORKOUT ORCHESTRATOR
# ============================================================


@dataclass
class Exercise:
    name: str
    target_reps: int = 0
    target_seconds: int = 0

    completed_reps: int = 0
    completed_seconds: int = 0
    completed: bool = False
    error: str = ""


@dataclass
class WorkoutSession:

    workout_name: str
    exercises: list[Exercise]

    current_index: int = 0

    started_at: float | None = None
    ended_at: float | None = None
    completed: bool = False

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    def start(self):
        self.started_at = time.time()
        self.ended_at = None

    # --------------------------------------------------------
    # CURRENT EXERCISE
    # --------------------------------------------------------

    def current_exercise(self):

        if self.current_index >= len(self.exercises):
            return None

        return self.exercises[self.current_index]

    # --------------------------------------------------------
    # COMPLETE EXERCISE
    # --------------------------------------------------------

    def complete_current_exercise(self, result):

        exercise = self.current_exercise()

        if exercise is None:
            return False

        exercise.completed_reps = int(result.get("reps", 0))
        exercise.completed_seconds = float(result.get("duration_seconds", 0))
        exercise.error = str(result.get("error", ""))
        exercise.completed = bool(result.get("completed", False))

        target_reached = (
            exercise.completed_reps >= exercise.target_reps
            if exercise.target_reps
            else exercise.completed_seconds >= exercise.target_seconds
        )

        if not target_reached or not exercise.completed:
            exercise.completed = False
            return False

        self.current_index += 1

        return True

    # --------------------------------------------------------
    # FINISH
    # --------------------------------------------------------

    def finish(self):
        self.ended_at = time.time()

    # --------------------------------------------------------
    # DURATION
    # --------------------------------------------------------

    def duration_seconds(self):

        if self.started_at is None:
            return 0

        end_time = self.ended_at

        if end_time is None:
            end_time = time.time()

        return end_time - self.started_at

    # --------------------------------------------------------
    # PROGRESS
    # --------------------------------------------------------

    def progress(self):

        if not self.exercises:
            return 100

        completed = sum(
            1
            for exercise in self.exercises
            if exercise.completed
        )

        return int(
            completed / len(self.exercises) * 100
        )


# ============================================================
# WORKOUT PRESETS
# ============================================================


WORKOUTS = {
    1: {"name": "Squat", "exercises": [Exercise("Squat", target_reps=10)]},
    2: {"name": "Push-Up", "exercises": [Exercise("Push-Up", target_reps=8)]},
    3: {"name": "Plank", "exercises": [Exercise("Plank", target_seconds=30)]},
    4: {
        "name": "Full Workout",
        "exercises": [
            Exercise("Squat", target_reps=10),
            Exercise("Push-Up", target_reps=8),
            Exercise("Plank", target_seconds=30),
        ],
    },
}


# ============================================================
# WORKOUT MANAGER
# ============================================================


class WorkoutManager:

    def display_workouts(self):

        print()
        print("=" * 60)
        print("SNAPFIT AI - WORKOUTS")
        print("=" * 60)

        for number, workout in WORKOUTS.items():

            print()
            print(
                f"{number}. {workout['name']}"
            )

            for exercise in workout["exercises"]:

                if exercise.target_reps > 0:

                    print(
                        f"   {exercise.name:<10}: "
                        f"{exercise.target_reps} reps"
                    )

                else:

                    print(
                        f"   {exercise.name:<10}: "
                        f"{exercise.target_seconds} seconds"
                    )

        print()
        print("=" * 60)

    def create_session(self, choice):

        workout = WORKOUTS.get(choice)

        if workout is None:
            return None

        exercises = []

        for exercise in workout["exercises"]:

            exercises.append(
                Exercise(
                    name=exercise.name,
                    target_reps=exercise.target_reps,
                    target_seconds=exercise.target_seconds
                )
            )

        return WorkoutSession(
            workout_name=workout["name"],
            exercises=exercises
        )


# ============================================================
# DISPLAY SESSION
# ============================================================


def display_session(session):

    print()
    print("=" * 60)
    print("SNAPFIT AI - WORKOUT SESSION")
    print("=" * 60)

    print()
    print(f"Workout: {session.workout_name}")
    print()

    for index, exercise in enumerate(
        session.exercises,
        start=1
    ):

        if exercise.target_reps > 0:
            target = f"{exercise.target_reps} reps"
        else:
            target = f"{exercise.target_seconds} seconds"

        status = (
            "COMPLETED"
            if exercise.completed
            else "PENDING"
        )

        print(
            f"{index}. "
            f"{exercise.name:<10} "
            f"{target:<15} "
            f"{status}"
        )

    print()
    print(
        f"Progress: {session.progress()}%"
    )

    print("=" * 60)


# ============================================================
# RUN REAL AI EXERCISE
# ============================================================


def run_session(session, retry_prompt=input):

    session.start()

    runner = ExerciseRunner()

    print()
    print("=" * 60)
    print("REAL AI WORKOUT STARTED")
    print("=" * 60)

    while True:

        exercise = session.current_exercise()

        if exercise is None:
            break

        print()
        print("=" * 60)

        print(
            f"CURRENT EXERCISE: "
            f"{exercise.name}"
        )

        if exercise.target_reps > 0:

            print(
                f"TARGET: "
                f"{exercise.target_reps} REPS"
            )

        else:

            print(
                f"TARGET: "
                f"{exercise.target_seconds} SECONDS"
            )

        print("=" * 60)

        print()
        print("Starting AI exercise coach...")

        result = runner.run_exercise(
            exercise.name
        )

        # ----------------------------------------------------
        # CHECK REAL AI RESULT
        # ----------------------------------------------------

        if result is None:

            print()
            print("Exercise was stopped or no result was returned.")

            session.finish()

            return False

        # ----------------------------------------------------
        # STORE ACTUAL RESULT
        # ----------------------------------------------------

        exercise.completed_reps = int(result.get("reps", 0))
        exercise.completed_seconds = float(result.get("duration_seconds", 0))
        exercise.error = str(result.get("error", ""))
        target_reached = (
            exercise.completed_reps >= exercise.target_reps
            if exercise.target_reps > 0
            else exercise.completed_seconds >= exercise.target_seconds
        )
        exercise.completed = bool(result.get("completed", False)) and target_reached

        # ----------------------------------------------------
        # DISPLAY RESULT
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("AI EXERCISE RESULT")
        print("=" * 60)

        if exercise.target_reps > 0:

            print(
                f"Completed Reps : "
                f"{exercise.completed_reps}/"
                f"{exercise.target_reps}"
            )

        else:

            print(
                f"Completed Time : "
                f"{exercise.completed_seconds:.1f}/"
                f"{exercise.target_seconds} seconds"
            )

        print(
            f"Exercise Status: "
            f"{'COMPLETED' if exercise.completed else 'INCOMPLETE'}"
        )

        print("=" * 60)

        # ----------------------------------------------------
        # INCOMPLETE EXERCISE
        # ----------------------------------------------------

        if not exercise.completed:

            print()
            print(
                "Target was not completed."
            )

            retry = retry_prompt(
                "Retry this exercise? (Y/N): "
            ).strip().lower()

            if retry == "y":

                print()
                print("Retrying exercise...")
                continue

            print()
            print("Workout stopped.")

            session.finish()

            return False

        # ----------------------------------------------------
        # EXERCISE COMPLETED
        # ----------------------------------------------------

        session.current_index += 1

        display_session(session)

    session.finish()

    session.completed = all(exercise.completed for exercise in session.exercises)
    return session.completed

# ============================================================
# SUMMARY
# ============================================================


def display_summary(session):

    print()
    print("=" * 60)
    print("SNAPFIT AI - WORKOUT COMPLETE")
    print("=" * 60)

    print()
    print(
        f"Workout: {session.workout_name}"
    )

    print(
        f"Duration: "
        f"{session.duration_seconds():.1f} seconds"
    )

    print(
        f"Progress: "
        f"{session.progress()}%"
    )

    print()
    print("EXERCISES")
    print("-" * 60)

    for exercise in session.exercises:

        if exercise.target_reps > 0:

            print(
                f"{exercise.name}: "
                f"{exercise.completed_reps}/"
                f"{exercise.target_reps} reps"
            )

        else:

            print(
                f"{exercise.name}: "
                f"{exercise.completed_seconds}/"
                f"{exercise.target_seconds} seconds"
            )

        if exercise.error:
            print(f"  Note: {exercise.error}")

    print()
    print("=" * 60)


# ============================================================
# MAIN
# ============================================================


def main_cli():

    print()
    print("=" * 60)
    print("SNAPFIT AI WORKOUT ORCHESTRATOR")
    print("=" * 60)

    manager = WorkoutManager()

    manager.display_workouts()

    try:

        choice = int(input("Select exercise or workout (1-4): "))

    except ValueError:

        print("Invalid workout selection.")
        return

    session = manager.create_session(choice)

    if session is None:

        print("Invalid workout selection.")
        return

    display_session(session)

    run_session(session)
    display_summary(session)

    # --------------------------------------------------------
    # SAVE PROGRESS
    # --------------------------------------------------------

    tracker = ProgressTracker()

    workout_record = tracker.record_workout(
        session
    )

    print()
    print("=" * 60)
    print("WORKOUT ATTEMPT SAVED")
    print("=" * 60)

    print()
    print(
        f"Workout: "
        f"{workout_record['workout_name']}"
    )

    print(
        f"Squats: "
        f"{workout_record['squats']}"
    )

    print(
        f"Push-Ups: "
        f"{workout_record['pushups']}"
    )

    print(
        f"Plank: "
        f"{workout_record['plank_seconds']} seconds"
    )

    print(
        f"Calories: "
        f"{workout_record['calories']} kcal"
    )

    print()
    print(f"Completed: {session.completed}")
    print("Workout data saved successfully.")

    print("=" * 60)


def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        from app.dashboard import main as dashboard_main
        dashboard_main()
    except (ImportError, tk.TclError) as error:
        print(f"Desktop dashboard unavailable: {error}")
        print("Starting the existing terminal workout interface.")
        main_cli()


if __name__ == "__main__":
    main()