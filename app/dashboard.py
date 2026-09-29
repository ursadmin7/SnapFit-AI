import threading
import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.coach.exercise_runner import ExerciseRunner
from ai.coach.progress_tracker import ProgressTracker
from ai.coach.workout_session import WorkoutManager, display_session, run_session


BG = "#f3f5f2"
INK = "#182b28"
MUTED = "#65746e"
ACCENT = "#b5e653"
PANEL = "#ffffff"


class SnapFitDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("SnapFit AI")
        self.root.geometry("1040x760")
        self.root.minsize(860, 660)
        self.root.configure(bg=BG)
        self.manager = WorkoutManager()
        self.tracker = ProgressTracker()
        self.runner = ExerciseRunner()
        self.selection = tk.StringVar(value="Full Workout")
        self.status = tk.StringVar(value="Ready when you are")
        self._build()
        self.refresh()

    def _build(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", padding=8, fieldbackground=PANEL)

        header = tk.Frame(self.root, bg=INK, padx=34, pady=26)
        header.pack(fill="x")
        tk.Label(header, text="SNAPFIT AI", bg=INK, fg="white",
                 font=("Segoe UI Semibold", 24)).pack(anchor="w")
        tk.Label(header, text="Private, on-device movement coaching",
                 bg=INK, fg="#c4d2cb", font=("Segoe UI", 11)).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(self.root, bg=BG, padx=34, pady=25)
        body.pack(fill="both", expand=True)

        controls = tk.Frame(body, bg=BG)
        controls.pack(fill="x")
        tk.Label(controls, text="START WORKOUT", bg=BG, fg=INK,
                 font=("Segoe UI Semibold", 12)).pack(anchor="w")
        row = tk.Frame(controls, bg=BG)
        row.pack(fill="x", pady=(10, 21))
        choices = ("Squat", "Push-Up", "Plank", "Full Workout")
        self.exercise_picker = ttk.Combobox(row, textvariable=self.selection,
                                            values=choices, state="readonly", width=24)
        self.exercise_picker.pack(side="left", padx=(0, 12))
        self.start_button = tk.Button(row, text="Start Workout", command=self.start_workout,
                                      bg=ACCENT, fg=INK, activebackground="#c8f077",
                                      relief="flat", bd=0, padx=20, pady=11,
                                      font=("Segoe UI Semibold", 11), cursor="hand2")
        self.start_button.pack(side="left")
        tk.Label(row, textvariable=self.status, bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side="left", padx=18)

        tk.Label(body, text="YOUR PROGRESS", bg=BG, fg=INK,
                 font=("Segoe UI Semibold", 12)).pack(anchor="w", pady=(0, 10))
        stats = tk.Frame(body, bg=BG)
        stats.pack(fill="x")
        self.stat_values = {}
        for key, label in (("workouts", "Completed Workouts"),
                           ("squats", "Squats"),
                           ("pushups", "Push-Ups"),
                           ("plank", "Plank Seconds")):
            tile = tk.Frame(stats, bg=PANEL, padx=17, pady=14,
                            highlightthickness=1, highlightbackground="#dce3dd")
            tile.pack(side="left", fill="both", expand=True, padx=(0, 10))
            value = tk.Label(tile, text="0", bg=PANEL, fg=INK,
                             font=("Segoe UI Semibold", 22))
            value.pack(anchor="w")
            tk.Label(tile, text=label, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))
            self.stat_values[key] = value

        content = tk.Frame(body, bg=BG)
        content.pack(fill="both", expand=True, pady=(24, 0))
        left = tk.Frame(content, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 20))
        tk.Label(left, text="SESSION PLAN", bg=BG, fg=INK,
                 font=("Segoe UI Semibold", 12)).pack(anchor="w", pady=(0, 10))
        self.plan_list = tk.Listbox(left, height=6, bg=PANEL, fg=INK,
                                    font=("Segoe UI", 11), relief="flat",
                                    highlightthickness=1, highlightbackground="#dce3dd",
                                    activestyle="none", selectbackground="#e8f2d7")
        self.plan_list.pack(fill="x")
        tk.Label(left, text="AI fitness guidance is for general informational purposes. Exercise within your limits.",
                 bg=BG, fg=MUTED, wraplength=440, justify="left",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(12, 0))

        right = tk.Frame(content, bg=BG)
        right.pack(side="right", fill="both", expand=True)
        tk.Label(right, text="RECENT WORKOUTS", bg=BG, fg=INK,
                 font=("Segoe UI Semibold", 12)).pack(anchor="w", pady=(0, 10))
        self.recent_list = tk.Listbox(right, height=8, bg=PANEL, fg=INK,
                                      font=("Segoe UI", 10), relief="flat",
                                      highlightthickness=1, highlightbackground="#dce3dd",
                                      activestyle="none", selectbackground="#e8f2d7")
        self.recent_list.pack(fill="both", expand=True)

        footer = tk.Frame(self.root, bg="#e8ece8", padx=34, pady=10)
        footer.pack(fill="x", side="bottom")
        tk.Label(footer, text="Camera frames are processed locally on this PC; no video is uploaded.",
                 bg="#e8ece8", fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")

        self.selection.trace_add("write", lambda *_: self.update_plan())

    def update_plan(self):
        choice = self.selection.get()
        selection_map = {"Squat": 1, "Push-Up": 2, "Plank": 3, "Full Workout": 4}
        session = self.manager.create_session(selection_map[choice])
        self.plan_list.delete(0, tk.END)
        for index, exercise in enumerate(session.exercises, start=1):
            target = f"{exercise.target_reps} reps" if exercise.target_reps else f"{exercise.target_seconds} seconds"
            self.plan_list.insert(tk.END, f"{index:02d}   {exercise.name:<12} {target}")

    def refresh(self):
        self.tracker = ProgressTracker()
        progress = self.tracker.progress
        self.stat_values["workouts"].configure(text=str(progress.get("total_workouts", 0)))
        self.stat_values["squats"].configure(text=str(progress.get("total_squats", 0)))
        self.stat_values["pushups"].configure(text=str(progress.get("total_pushups", 0)))
        self.stat_values["plank"].configure(text=str(progress.get("total_plank_seconds", 0)))
        self.recent_list.delete(0, tk.END)
        for workout in reversed(self.tracker.workouts[-8:]):
            outcome = "Complete" if workout.get("completed", True) else "Attempt"
            self.recent_list.insert(
                tk.END,
                f"{workout.get('date', '')[:16]}   {workout.get('workout_name', 'Workout')}   "
                f"{outcome}   {int(workout.get('duration_seconds', 0))}s",
            )
        self.update_plan()

    def _retry_prompt(self):
        response = threading.Event()
        result = {"retry": False}

        def ask():
            result["retry"] = messagebox.askyesno(
                "Target not reached", "Would you like to retry this exercise?"
            )
            response.set()

        self.root.after(0, ask)
        response.wait()
        return "y" if result["retry"] else "n"

    def start_workout(self):
        selection_map = {"Squat": 1, "Push-Up": 2, "Plank": 3, "Full Workout": 4}
        session = self.manager.create_session(selection_map[self.selection.get()])
        self.start_button.configure(state="disabled")
        self.exercise_picker.configure(state="disabled")
        self.status.set("Starting local camera coach...")

        def run():
            try:
                self.root.after(0, lambda: self.status.set("Camera coach is running"))
                run_session(session, retry_prompt=self._retry_prompt)
                self.tracker.record_workout(session)
                self.root.after(0, self._finish_workout, session)
            except Exception as error:
                self.root.after(0, self._show_error, str(error))

        threading.Thread(target=run, daemon=True).start()

    def _finish_workout(self, session):
        display_session(session)
        summary_lines = []
        for item in session.exercises:
            value = (
                f"{item.name}: {item.completed_reps} reps"
                if item.target_reps
                else f"{item.name}: {item.completed_seconds:.1f} seconds"
            )
            if item.error:
                value += f"\n  {item.error}"
            summary_lines.append(value)
        summary = "\n".join(summary_lines)
        messagebox.showinfo(
            "Workout Summary",
            f"{session.workout_name}\n"
            f"Status: {'Complete' if session.completed else 'Incomplete'}\n"
            f"Duration: {session.duration_seconds():.1f} seconds\n\n{summary}",
        )
        self.start_button.configure(state="normal")
        self.exercise_picker.configure(state="readonly")
        self.status.set("Ready when you are")
        self.refresh()

    def _show_error(self, detail):
        self.start_button.configure(state="normal")
        self.exercise_picker.configure(state="readonly")
        self.status.set("Workout could not start")
        messagebox.showerror("SnapFit AI", f"The workout could not finish.\n\n{detail}")


def main():
    root = tk.Tk()
    SnapFitDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()