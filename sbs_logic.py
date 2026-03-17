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

# SBS 21-Week Program Data: (Intensity %, AMRAP Target)
SBS_PROGRAM = {
    "primary": {
        1: (0.70, 10), 2: (0.75, 8), 3: (0.80, 6), 4: (0.725, 9), 5: (0.775, 7), 6: (0.825, 5), 7: (0.50, 0),
        8: (0.75, 8), 9: (0.80, 6), 10: (0.85, 4), 11: (0.775, 7), 12: (0.825, 5), 13: (0.875, 3), 14: (0.50, 0),
        15: (0.80, 6), 16: (0.85, 4), 17: (0.90, 2), 18: (0.825, 5), 19: (0.875, 3), 20: (0.925, 2), 21: (1.00, 1)
    },
    "auxiliary": {
        1: (0.60, 14), 2: (0.65, 12), 3: (0.70, 10), 4: (0.625, 13), 5: (0.675, 11), 6: (0.725, 9), 7: (0.50, 0),
        8: (0.65, 12), 9: (0.70, 10), 10: (0.75, 8), 11: (0.675, 11), 12: (0.725, 9), 13: (0.775, 7), 14: (0.50, 0),
        15: (0.70, 10), 16: (0.75, 8), 17: (0.80, 6), 18: (0.725, 9), 19: (0.775, 7), 20: (0.825, 5), 21: (1.00, 1)
    }
}

def load_state():
    if not os.path.exists(STATE_FILE): return None
    with open(STATE_FILE, "r") as f: return json.load(f)

def update_readme(state):
    """Updates README.md with a live dashboard of the current training state."""
    week = state["current_week"]
    lifts = state["main_lifts"]
    
    dashboard = f"""# Hevy to SbS Sync 🏋️‍♂️🤖

![Sync Status](https://github.com/greenducktape/Hevy-Script-SBS/actions/workflows/sync_hevy.yml/badge.svg)

## 📅 Current Program State: **Week {week} / 21**
*Next session targets are automatically calculated based on your Training Max (TM).*

| Exercise | Category | Current TM | Next Target Weight | Next Target Reps |
| :--- | :--- | :--- | :--- | :--- |
"""
    for name, data in lifts.items():
        cat = data.get("category", "primary")
        intensity, target = SBS_PROGRAM[cat].get(week, (0, 0))
        weight = round((data["tm"] * intensity) / 2.5) * 2.5
        dashboard += f"| {name} | {cat.capitalize()} | {data['tm']} kg | **{weight} kg** | {target} |\n"

    dashboard += f"""
---
### 🛠 How it works
- **Syncing:** Every night at 11 PM UTC, GitHub fetches your latest Hevy workout.
- **Auto-Advance:** After **{state.get('workouts_per_week', 3)} unique workouts**, the week automatically increments.
- **Manual Control:** Use the [Actions Tab](https://github.com/greenducktape/Hevy-Script-SBS/actions) to force a sync or advance the week.

*Last updated: Week {week}*
"""
    with open("README.md", "w") as f:
        f.write(dashboard)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)
    update_readme(state)

def get_multiplier(rep_difference):
    multipliers = {-2: 0.95, -1: 0.98, 0: 1.0, 1: 1.005, 2: 1.01, 3: 1.015, 4: 1.02, 5: 1.03}
    if rep_difference <= -2: return multipliers[-2]
    if rep_difference >= 5: return multipliers[5]
    return multipliers.get(rep_difference, 1.0)

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
    """Calculates weights and targets for the given week."""
    if week_number > 21: return state
    print(f"\n--- PREPARING WEEK {week_number} ---")
    for lift, data in state["main_lifts"].items():
        intensity, target = SBS_PROGRAM[data.get("category", "primary")].get(week_number, (0, 0))
        weight = round((data["tm"] * intensity) / 2.5) * 2.5
        state["main_lifts"][lift]["target_reps"] = target
        print(f"{lift:<22} | Weight: {weight:>6} kg | Target: {target}")
    return state

def sync_with_hevy():
    print("--- Hevy to SbS Sync ---")
    workout = fetch_latest_workout()
    if not workout: return

    workout_id = workout.get("id")
    state = load_state()
    if not state: return

    # Check if this specific workout has already been processed this week
    if workout_id in state.get("processed_workouts_this_week", []):
        print(f"Workout {workout.get('title')} (ID: {workout_id}) already processed.")
        return

    print(f"Processing new workout: {workout.get('title')}")
    found_any = False
    for ex in workout.get("exercises", []):
        lift_name = LIFT_MAPPING.get(ex.get("exercise_template_id"))
        if lift_name and lift_name in state["main_lifts"]:
            found_any = True
            sets = ex.get("sets", [])
            last_set = next((s for s in reversed(sets) if s.get("type") == "failure"), sets[-1])
            state = calculate_new_tm(state, lift_name, last_set.get("reps", 0), state["main_lifts"][lift_name]["target_reps"])

    if found_any:
        # Record this workout as processed
        state.setdefault("processed_workouts_this_week", []).append(workout_id)
        
        # Check if we finished the week
        if len(state["processed_workouts_this_week"]) >= state.get("workouts_per_week", 3):
            print("\nWeek complete! Automatically advancing...")
            state["current_week"] += 1
            state["processed_workouts_this_week"] = [] # Reset for next week
            state = update_targets_for_week(state, state["current_week"])
        
        save_state(state)
        print("\nSync complete. State saved.")
    else:
        print("No matching lifts found in this workout.")

if __name__ == "__main__":
    import sys
    if "--next-week" in sys.argv:
        state = load_state()
        state["current_week"] += 1
        state["processed_workouts_this_week"] = []
        state = update_targets_for_week(state, state["current_week"])
        save_state(state)
        print(f"Manually advanced to Week {state['current_week']}.")
    else:
        sync_with_hevy()
