import os
import sys
import json
import subprocess


# ============================================================
# SNAPFIT AI - EXERCISE RUNNER
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

EXERCISE_DIR = os.path.join(
    PROJECT_ROOT,
    "ai",
    "exercise"
)

RESULT_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "exercise_result.json"
)


# ============================================================
# EXERCISE CONFIGURATION
# ============================================================

EXERCISES = {
    "Squat": {
        "file": "squat_live.py",
        "display": "Squat AI Coach",
        "target": 10,
        "unit": "reps"
    },

    "Push-Up": {
        "file": "pushup_live.py",
        "display": "Push-Up AI Coach",
        "target": 8,
        "unit": "reps"
    },

    "Plank": {
        "file": "plank_live.py",
        "display": "Plank AI Coach",
        "target": 30,
        "unit": "seconds"
    }
}


# ============================================================
# EXERCISE RUNNER
# ============================================================

class ExerciseRunner:

    def __init__(self):
        self.exercise_dir = EXERCISE_DIR

    # --------------------------------------------------------
    # GET EXERCISE
    # --------------------------------------------------------

    def get_exercise(self, exercise_name):
        return EXERCISES.get(exercise_name)

    # --------------------------------------------------------
    # CHECK EXERCISE
    # --------------------------------------------------------

    def exercise_exists(self, exercise_name):

        exercise = self.get_exercise(exercise_name)

        if exercise is None:
            return False

        file_path = os.path.join(
            self.exercise_dir,
            exercise["file"]
        )

        return os.path.exists(file_path)

    # --------------------------------------------------------
    # LIST EXERCISES
    # --------------------------------------------------------

    def list_exercises(self):

        print()
        print("=" * 60)
        print("SNAPFIT AI - EXERCISE ENGINES")
        print("=" * 60)

        for name, config in EXERCISES.items():

            exists = self.exercise_exists(name)

            status = (
                "READY"
                if exists
                else "MISSING"
            )

            print()
            print(
                f"{name:<12} "
                f"{config['display']:<25} "
                f"[{status}]"
            )

        print()
        print("=" * 60)

    # --------------------------------------------------------
    # CLEAR OLD RESULT
    # --------------------------------------------------------

    def clear_result(self):

        try:

            if os.path.exists(RESULT_FILE):
                os.remove(RESULT_FILE)
            return True

        except Exception as error:

            print(
                f"Warning: Could not clear old result: {error}"
            )
            return False

    def save_failed_result(self, exercise_name, message):
        result = {
            "exercise": exercise_name,
            "reps": 0,
            "duration_seconds": 0,
            "completed": False,
            "error": message,
        }
        try:
            os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
            with open(RESULT_FILE, "w", encoding="utf-8") as result_file:
                json.dump(result, result_file, indent=4)
        except OSError as error:
            print(f"Could not save the failure result: {error}")
        return result

    # --------------------------------------------------------
    # READ RESULT
    # --------------------------------------------------------

    def read_result(self):

        if not os.path.exists(RESULT_FILE):

            print()
            print(
                "WARNING: Exercise did not return "
                "an AI result."
            )

            return None

        try:

            with open(
                RESULT_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                result = json.load(file)

            if not isinstance(result, dict):
                return None

            return result

        except Exception as error:

            print()
            print(
                f"WARNING: Could not read exercise result: "
                f"{error}"
            )

            return None

    # --------------------------------------------------------
    # RUN EXERCISE
    # --------------------------------------------------------

    def run_exercise(self, exercise_name):

        exercise = self.get_exercise(
            exercise_name
        )

        if exercise is None:

            print(
                f"Unknown exercise: "
                f"{exercise_name}"
            )

            return None

        file_path = os.path.join(
            self.exercise_dir,
            exercise["file"]
        )

        if not os.path.exists(file_path):

            print()
            print(
                "Exercise engine not found:"
            )

            print(file_path)

            return None

        if not os.path.exists(os.path.join(PROJECT_ROOT, "models", "pose_landmarker_full.task")):
            print("Pose model is missing. Restore models/pose_landmarker_full.task first.")
            return None

        print()
        print("=" * 60)
        print(
            f"STARTING {exercise_name.upper()} AI"
        )
        print("=" * 60)

        print()
        print(
            "Target:",
            exercise["target"],
            exercise["unit"]
        )

        print(
            "Camera AI exercise coach starting..."
        )

        print(
            "Complete the target or press Q/ESC to stop."
        )

        print()

        # Remove result from previous exercise.
        if not self.clear_result():
            return self.save_failed_result(
                exercise_name,
                "Could not clear the previous exercise result.",
            )

        try:

            process = subprocess.run(
                [
                    sys.executable,
                    file_path
                ],
                cwd=PROJECT_ROOT
            )

            # ------------------------------------------------
            # PROCESS ERROR
            # ------------------------------------------------

            if process.returncode != 0:

                print()
                print(
                    f"{exercise_name} AI exited "
                    f"with code {process.returncode}."
                )

                return self.save_failed_result(
                    exercise_name,
                    f"Exercise process exited with code {process.returncode}.",
                )

            # ------------------------------------------------
            # READ ACTUAL AI RESULT
            # ------------------------------------------------

            result = self.read_result()

            if result is None:

                print()
                print(
                    "Exercise finished, but no AI result "
                    "was received."
                )

                return self.save_failed_result(
                    exercise_name,
                    "No result file was returned by the exercise analyzer.",
                )

            if result.get("exercise") != exercise_name:
                print("Exercise result does not match the selected analyzer.")
                return self.save_failed_result(
                    exercise_name,
                    "The analyzer returned a mismatched exercise result.",
                )

            try:
                reps = int(result.get("reps", 0))
                duration = float(result.get("duration_seconds", 0))
            except (TypeError, ValueError):
                print("Exercise result contains invalid count or duration data.")
                return self.save_failed_result(
                    exercise_name,
                    "The analyzer returned invalid count or duration data.",
                )

            if reps < 0 or duration < 0:
                print("Exercise result cannot contain negative values.")
                return self.save_failed_result(
                    exercise_name,
                    "The analyzer returned negative count or duration data.",
                )

            result["reps"] = reps
            result["duration_seconds"] = duration
            result["completed"] = bool(
                reps >= exercise["target"]
                if exercise["unit"] == "reps"
                else duration >= exercise["target"]
            )

            # ------------------------------------------------
            # DISPLAY RESULT
            # ------------------------------------------------

            print()
            print("=" * 60)
            print("EXERCISE RESULT")
            print("=" * 60)

            print(
                f"Exercise : "
                f"{result.get('exercise', exercise_name)}"
            )

            if exercise["unit"] == "reps":

                print(
                    f"Reps     : "
                    f"{result.get('reps', 0)}/"
                    f"{exercise['target']}"
                )

            else:

                print(
                    f"Time     : "
                    f"{result.get('duration_seconds', 0)}s/"
                    f"{exercise['target']}s"
                )

            print(
                f"Completed: "
                f"{result.get('completed', False)}"
            )

            print("=" * 60)

            # ------------------------------------------------
            # RETURN ACTUAL RESULT
            # ------------------------------------------------

            return result

        except KeyboardInterrupt:

            print()
            print(
                "Exercise stopped by user."
            )

            return self.save_failed_result(exercise_name, str(error))

        except Exception as error:

            print()
            print(
                "Error starting exercise:"
            )

            print(error)

            return None


# ============================================================
# TEST
# ============================================================

def main():

    print()
    print("=" * 60)
    print("SNAPFIT AI - EXERCISE RUNNER")
    print("=" * 60)

    runner = ExerciseRunner()

    runner.list_exercises()

    print()
    print("Exercise Runner initialized.")
    print()
    print("Available exercises:")

    for name in EXERCISES:

        print(
            f"  - {name}"
        )


if __name__ == "__main__":
    main()