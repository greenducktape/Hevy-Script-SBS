import json
import os
import requests
import csv
from dotenv import load_dotenv

load_dotenv()

# Configuration
STATE_FILE = "state.json"
CSV_FILE = "exercise_ids.csv"
HEVY_API_KEY = os.getenv("HEVY_API_KEY")
HEVY_BASE_URL = "https://api.hevyapp.com/v1"

# The "Source of Truth" Mapping
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
    "6AC96645": "DB OHP",
    "29083183": "Chin-ups",
    "1B2B1E7C": "Pull-ups",
    "55E6546F": "Barbell rows"
}

ROUTINE_IDS = {
    "SbS Hyp Day 1": "e85acaee-289e-4b1f-8d6a-532c4eb3138f",
    "SbS Hyp Day 2": "2194411d-866e-4fd0-8596-fa2302b1421c",
    "SbS Hyp Day 3": "a4384cbb-8f1b-4517-bec2-09fdff80efb1"
}

# We'll now store which exercises belong to which routine ID
# to allow for auto-discovery and adding new lifts to the right day.
ROUTINE_MAP = {
    "e85acaee-289e-4b1f-8d6a-532c4eb3138f": ["Squat", "Sumo Deadlift", "Dips", "Chin-ups"],
    "2194411d-866e-4fd0-8596-fa2302b1421c": ["Bench Press", "OHP", "Bulgarian Split Squat", "Pull-ups"],
    "a4384cbb-8f1b-4517-bec2-09fdff80efb1": ["Block Pulls", "Long Pause Bench", "Lunges", "DB OHP", "Barbell rows"]
}

SBS_PROGRAM = {
    "primary": {
        1: (0.70, 10, 12), 2: (0.725, 9, 11), 3: (0.75, 8, 10), 4: (0.725, 9, 11), 5: (0.75, 8, 10), 6: (0.775, 7, 9), 7: (0.60, 14, 18),
        8: (0.725, 9, 11), 9: (0.75, 8, 10), 10: (0.775, 7, 9), 11: (0.75, 8, 10), 12: (0.775, 7, 9), 13: (0.80, 6, 8), 14: (0.60, 14, 18),
        15: (0.75, 8, 10), 16: (0.775, 7, 9), 17: (0.80, 6, 8), 18: (0.775, 7, 9), 19: (0.80, 6, 8), 20: (0.825, 5, 6), 21: (0.60, 14, 18)
    },
    "auxiliary": {
        1: (0.65, 12, 15), 2: (0.675, 11, 13), 3: (0.70, 10, 12), 4: (0.675, 11, 13), 5: (0.70, 10, 12), 6: (0.725, 9, 11), 7: (0.55, 17, 21),
        8: (0.675, 11, 13), 9: (0.70, 10, 12), 10: (0.725, 9, 11), 11: (0.70, 10, 12), 12: (0.725, 9, 11), 13: (0.75, 8, 10), 14: (0.55, 17, 21),
        15: (0.70, 10, 12), 16: (0.725, 9, 11), 17: (0.75, 8, 10), 18: (0.725, 9, 11), 19: (0.75, 8, 10), 20: (0.775, 7, 9), 21: (0.55, 17, 21)
    }
}

def load_state():
    if not os.path.exists(STATE_FILE): return None
    with open(STATE_FILE, "r") as f: return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f, indent=4)
    update_readme(state)
    update_hevy_routines(state)

def get_exercise_name_from_csv(ex_id):
    """Looks up an ID in the CSV to find the name."""
    try:
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                if row['id'] == ex_id:
                    return row['title']
    except: return f"Unknown Exercise ({ex_id})"
    return f"Unknown Exercise ({ex_id})"

def update_readme(state):
    week = state["current_week"]
    dashboard = f"# Hevy to SbS Sync (Hypertrophy) 🏋️‍♂️💪\n\n## 📅 Week {week} / 21\n\n| Exercise | TM | Next Weight | Normal Sets | AMRAP Target |\n| :--- | :--- | :--- | :--- | :--- |\n"
    for name, data in state["main_lifts"].items():
        intensity, norm, target = SBS_PROGRAM[data.get("category", "primary")].get(week, (0, 0, 0))
        weight = round((data["tm"] * intensity) / 2.5) * 2.5
        dashboard += f"| {name} | {data['tm']} kg | **{weight} kg** | 3x{norm} | {target} |\n"
    with open("README.md", "w") as f: f.write(dashboard)

def update_hevy_routines(state):
    if not HEVY_API_KEY: return
    headers = {"api-key": HEVY_API_KEY, "Content-Type": "application/json"}
    week = state["current_week"]
    
    # We reconstruct titles based on ROUTINE_IDS keys
    for base_title, r_id in ROUTINE_IDS.items():
        current_title = f"{base_title} (W{week})"
        print(f"Updating Hevy: {current_title}...")
        exercises_payload = []
        
        # Get exercises for this routine (including any auto-discovered ones)
        ex_names = ROUTINE_MAP.get(r_id, [])
        for name in ex_names:
            lift_data = state["main_lifts"].get(name)
            ex_id = next((k for k, v in LIFT_MAPPING.items() if v == name), None)
            
            if not lift_data: # Bodyweight/Accessories
                sets = [{"type": "normal", "reps": 10, "weight_kg": 0} for _ in range(4)]
                note = "Accessory"
            else:
                intensity, norm, target = SBS_PROGRAM[lift_data["category"]].get(week, (0, 0, 0))
                weight = round((lift_data["tm"] * intensity) / 2.5) * 2.5
                sets = [{"type": "normal", "reps": norm, "weight_kg": weight} for _ in range(3)]
                sets.append({"type": "failure", "reps": target, "weight_kg": weight})
                note = f"W{week}: 3x{norm}, 1x{target}+"
            
            if ex_id:
                exercises_payload.append({"exercise_template_id": ex_id, "notes": note, "sets": sets})

        try:
            r = requests.put(f"{HEVY_BASE_URL}/routines/{r_id}", headers=headers, json={"routine": {"title": current_title, "exercises": exercises_payload}})
            r.raise_for_status()
            print(f"   ✅ Updated {current_title}")
        except Exception as e: print(f"   ❌ Error updating {base_title}: {e}")

def get_multiplier(rep_diff):
    if rep_diff <= -2: return 0.95
    if rep_diff == -1: return 0.98
    if rep_diff == 0: return 1.0
    if rep_diff == 1: return 1.005
    if rep_diff == 2: return 1.01
    if rep_diff == 3: return 1.015
    if rep_diff == 4: return 1.02
    return 1.03

def sync_with_hevy():
    print("--- Hevy to SbS Sync ---")
    if not HEVY_API_KEY: return
    headers = {"api-key": HEVY_API_KEY, "Accept": "application/json"}
    try:
        r = requests.get(f"{HEVY_BASE_URL}/workouts", headers=headers, params={"pageSize": 1})
        r.raise_for_status()
        workouts = r.json().get("workouts", [])
        if not workouts: return
        workout = workouts[0]
    except: return

    state = load_state()
    if not state or workout.get("id") in state.get("processed_workouts_this_week", []): return

    print(f"🔄 Processing workout: {workout.get('title')}")
    found_any = False
    r_id = workout.get("routine_id")

    for ex in workout.get("exercises", []):
        ex_id = ex.get("exercise_template_id")
        lift_name = LIFT_MAPPING.get(ex_id)
        
        # AUTO-DISCOVERY LOGIC:
        if not lift_name:
            lift_name = get_exercise_name_from_csv(ex_id)
            print(f"✨ Auto-discovered new exercise: {lift_name}")
            LIFT_MAPPING[ex_id] = lift_name
            # Add to Routine Map if we know which routine this is
            if r_id and r_id in ROUTINE_MAP:
                if lift_name not in ROUTINE_MAP[r_id]:
                    ROUTINE_MAP[r_id].append(lift_name)

        if lift_name:
            # Initialize in state if missing
            if lift_name not in state["main_lifts"]:
                print(f"➕ Adding {lift_name} to tracking state.")
                state["main_lifts"][lift_name] = {
                    "tm": 100.0, # Default starting point
                    "target_reps": 12,
                    "category": "auxiliary"
                }

            found_any = True
            sets = ex.get("sets", [])
            last_set = next((s for s in reversed(sets) if s.get("type") == "failure"), sets[-1])
            reps = last_set.get("reps", 0)
            target = state["main_lifts"][lift_name]["target_reps"]
            state["main_lifts"][lift_name]["tm"] = round(state["main_lifts"][lift_name]["tm"] * get_multiplier(reps - target), 2)
            print(f"   💪 {lift_name}: {reps} reps (Target {target}) -> New TM: {state['main_lifts'][lift_name]['tm']}")

    if found_any:
        state.setdefault("processed_workouts_this_week", []).append(workout.get("id"))
        if len(state["processed_workouts_this_week"]) >= state.get("workouts_per_week", 3):
            state["current_week"] += 1
            state["processed_workouts_this_week"] = []
            for lift, data in state["main_lifts"].items():
                _, _, next_target = SBS_PROGRAM[data["category"]].get(state["current_week"], (0,0,0))
                state["main_lifts"][lift]["target_reps"] = next_target
        save_state(state)

if __name__ == "__main__":
    import sys
    if "--next-week" in sys.argv:
        s = load_state()
        s["current_week"] += 1
        s["processed_workouts_this_week"] = []
        for lift, data in s["main_lifts"].items():
            _, _, next_target = SBS_PROGRAM[data["category"]].get(s["current_week"], (0,0,0))
            s["main_lifts"][lift]["target_reps"] = next_target
        save_state(s)
    else:
        sync_with_hevy()
