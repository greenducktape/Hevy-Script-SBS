import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
STATE_FILE = "state.json"
HEVY_API_KEY = os.getenv("HEVY_API_KEY")
HEVY_BASE_URL = "https://api.hevyapp.com/v1"

# Mapping: Hevy exercise_template_id -> Internal Lift Name in state.json
LIFT_MAPPING = {
    "D04AC939": "Squat",
    "79D0BB3A": "Bench Press",
    "D20D7BBE": "Sumo Deadlift",
    "7B8D84E8": "OHP",
    "6FCD7755": "Dips",
    "B5D3A742": "Bulgarian Split Squat",
    "FE389074": "Block Pulls",
    "50DFDFAB": "Long Pause Bench",
    "6E6EE645": "Lunges",
    "6AC96645": "DB OHP"
}

# SBS Hypertrophy 21-Week Program Data
# Logic: Primary lifts start 70%, Auxiliary start 65%. 
# Wave 2 is +2.5% intensity and -1 rep.
SBS_PROGRAM = {
    "primary": {
        1: (0.70, 12), 2: (0.725, 11), 3: (0.75, 10), 4: (0.725, 11), 5: (0.75, 10), 6: (0.775, 9), 7: (0.50, 0),
        8: (0.75, 10), 9: (0.775, 9), 10: (0.80, 8), 11: (0.775, 9), 12: (0.80, 8), 13: (0.825, 7), 14: (0.50, 0),
        15: (0.80, 8), 16: (0.825, 7), 17: (0.85, 6), 18: (0.825, 7), 19: (0.85, 6), 20: (0.875, 5), 21: (0.50, 0)
    },
    "auxiliary": {
        1: (0.65, 15), 2: (0.675, 13), 3: (0.70, 12), 4: (0.675, 13), 5: (0.70, 12), 6: (0.725, 11), 7: (0.50, 0),
        8: (0.70, 12), 9: (0.725, 11), 10: (0.75, 10), 11: (0.725, 11), 12: (0.75, 10), 13: (0.775, 9), 14: (0.50, 0),
        15: (0.75, 10), 16: (0.775, 9), 17: (0.80, 8), 18: (0.775, 9), 19: (0.80, 8), 20: (0.825, 7), 21: (0.50, 0)
    }
}

def load_state():
    if not os.path.exists(STATE_FILE): return None
    with open(STATE_FILE, "r") as f: return json.load(f)

def update_readme(state):
    """Updates README.md with a live dashboard of the current training state."""
    week = state["current_week"]
    lifts = state["main_lifts"]
    dashboard = f"""# Hevy to SbS Sync (Hypertrophy) 🏋️‍♂️💪

![Sync Status](https://github.com/greenducktape/Hevy-Script-SBS/actions/workflows/sync_hevy.yml/badge.svg)

## 📅 Program State: **Week {week} / 21**
*Targets automatically calculated for Hypertrophy RTF.*

| Exercise | Category | Current TM | Next Weight | Next AMRAP Target |
| :--- | :--- | :--- | :--- | :--- |
"""
    for name, data in lifts.items():
        cat = data.get("category", "primary")
        intensity, target = SBS_PROGRAM[cat].get(week, (0, 0))
        weight = round((data["tm"] * intensity) / 2.5) * 2.5
        dashboard += f"| {name} | {cat.capitalize()} | {data['tm']} kg | **{weight} kg** | {target} |\n"
    
    dashboard += f"\n*Last updated: Week {week}*\n"
    with open("README.md", "w") as f: f.write(dashboard)

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f, indent=4)
    update_readme(state)

def get_multiplier(rep_difference):
    # Hypertrophy RTF Multipliers
    if rep_difference <= -2: return 0.95
    if rep_difference == -1: return 0.98
    if rep_difference == 0: return 1.0
    if rep_difference == 1: return 1.005
    if rep_difference == 2: return 1.01
    if rep_difference == 3: return 1.015
    if rep_difference == 4: return 1.02
    return 1.03 # >= 5

def calculate_new_tm(state, lift_name, actual_reps, target_reps):
    lift_data = state["main_lifts"][lift_name]
    rep_diff = actual_reps - target_reps
    new_tm = round(lift_data["tm"] * get_multiplier(rep_diff), 2)
    state["main_lifts"][lift_name]["tm"] = new_tm
    print(f"   -> Updated {lift_name}: TM {lift_data['tm']} -> {new_tm} (Diff: {rep_diff})")
    return state

def fetch_latest_workout():
    if not HEVY_API_KEY: return None
    headers = {"api-key": HEVY_API_KEY, "Accept": "application/json"}
    try:
        response = requests.get(f"{HEVY_BASE_URL}/workouts", headers=headers, params={"pageSize": 1})
        response.raise_for_status()
        workouts = response.json().get("workouts", [])
        return workouts[0] if workouts else None
    except Exception as e:
        print(f"Error fetching: {e}"); return None

def update_targets_for_week(state, week_number):
    if week_number > 21: return state
    print(f"\n--- PREPARING HYPERTROPHY WEEK {week_number} ---")
    for lift, data in state["main_lifts"].items():
        intensity, target = SBS_PROGRAM[data.get("category", "primary")].get(week_number, (0, 0))
        state["main_lifts"][lift]["target_reps"] = target
    return state

def sync_with_hevy():
    print("--- Hevy to SbS Sync (Hypertrophy) ---")
    workout = fetch_latest_workout()
    if not workout: return
    workout_id = workout.get("id")
    state = load_state()
    if not state or workout_id in state.get("processed_workouts_this_week", []): return

    found_any = False
    for ex in workout.get("exercises", []):
        lift_name = LIFT_MAPPING.get(ex.get("exercise_template_id"))
        if lift_name and lift_name in state["main_lifts"]:
            found_any = True
            sets = ex.get("sets", [])
            last_set = next((s for s in reversed(sets) if s.get("type") == "failure"), sets[-1])
            state = calculate_new_tm(state, lift_name, last_set.get("reps", 0), state["main_lifts"][lift_name]["target_reps"])

    if found_any:
        state.setdefault("processed_workouts_this_week", []).append(workout_id)
        if len(state["processed_workouts_this_week"]) >= state.get("workouts_per_week", 3):
            state["current_week"] += 1
            state["processed_workouts_this_week"] = []
            state = update_targets_for_week(state, state["current_week"])
        save_state(state)
    else:
        print("No matching lifts found.")

if __name__ == "__main__":
    import sys
    if "--next-week" in sys.argv:
        state = load_state()
        state["current_week"] += 1
        state["processed_workouts_this_week"] = []
        state = update_targets_for_week(state, state["current_week"])
        save_state(state)
    else:
        sync_with_hevy()
