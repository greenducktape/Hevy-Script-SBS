import json
import os
import csv
import requests
from dotenv import load_dotenv

load_dotenv()

STATE_FILE = "state.json"
CSV_FILE = "exercise_ids.csv"
HEVY_API_KEY = os.getenv("HEVY_API_KEY")
HEVY_BASE_URL = "https://api.hevyapp.com/v1"

def load_all_exercises_from_csv():
    """Pre-loads all exercise IDs and names from the CSV into a mapping."""
    mapping = {}
    try:
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                if row.get('id') and row.get('title'):
                    mapping[row['id']] = row['title']
    except FileNotFoundError:
        print(f"Warning: {CSV_FILE} not found. Auto-discovery will be limited.")
    return mapping

LIFT_MAPPING = load_all_exercises_from_csv()

ROUTINE_IDS = {"SbS Hyp Day 1":"e85acaee-289e-4b1f-8d6a-532c4eb3138f","SbS Hyp Day 2":"2194411d-866e-4fd0-8596-fa2302b1421c","SbS Hyp Day 3":"a4384cbb-8f1b-4517-bec2-09fdff80efb1"}

SBS_PROGRAM = {
    "primary": {1:(0.7,10,12),2:(0.725,9,11),3:(0.75,8,10),4:(0.725,9,11),5:(0.75,8,10),6:(0.775,7,9),7:(0.6,14,18),8:(0.725,9,11),9:(0.75,8,10),10:(0.775,7,9),11:(0.75,8,10),12:(0.775,7,9),13:(0.8,6,8),14:(0.6,14,18),15:(0.75,8,10),16:(0.775,7,9),17:(0.8,6,8),18:(0.775,7,9),19:(0.8,6,8),20:(0.825,5,6),21:(0.6,14,18)},
    "auxiliary": {1:(0.65,12,15),2:(0.675,11,13),3:(0.7,10,12),4:(0.675,11,13),5:(0.7,10,12),6:(0.725,9,11),7:(0.55,17,21),8:(0.675,11,13),9:(0.7,10,12),10:(0.725,9,11),11:(0.7,10,12),12:(0.725,9,11),13:(0.75,8,10),14:(0.55,17,21),15:(0.7,10,12),16:(0.725,9,11),17:(0.75,8,10),18:(0.725,9,11),19:(0.75,8,10),20:(0.775,7,9),21:(0.55,17,21)}
}

def load_state():
    with open(STATE_FILE, "r") as f: return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f, indent=4)
    update_readme(state)
    update_hevy_routines(state)

def update_readme(state):
    week, lifts = state["current_week"], state["main_lifts"]
    dashboard = f"""# Hevy to SbS Sync (Hypertrophy) 🏋️‍♂️💪

## 📅 Week {week} / 21

| Exercise | TM | Next Weight | Sets | AMRAP |
| :--- | :--- | :--- | :--- | :--- |
"""
    for name, data in lifts.items():
        intensity, norm, target = SBS_PROGRAM[data.get("category", "primary")].get(week, (0,0,0))
        weight = round((data["tm"] * intensity) / 2.5) * 2.5
        dashboard += f"| {name} | {data['tm']} kg | **{weight} kg** | 3x{norm} | {target} |\n"

    dashboard += """
**Note on Bodyweight Lifts:** For exercises like Dips or Pull-ups, progression is achieved by adding weight. To track this, switch to the 'Weighted Dips' or 'Weighted Pull-ups' exercise in Hevy. The script will auto-discover and track the new weighted version.
"""
    with open("README.md", "w") as f: f.write(dashboard)

def update_hevy_routines(state):
    headers = {"api-key": HEVY_API_KEY, "Content-Type": "application/json"}
    week, routine_map = state["current_week"], state["routine_map"]
    for r_id, ex_names in routine_map.items():
        base_title = next((k for k, v in ROUTINE_IDS.items() if v == r_id), "Unknown")
        current_title = f"{base_title} (W{week})"
        exercises_payload = []
        for name in ex_names:
            lift_data = state["main_lifts"].get(name, {})
            ex_id = next((k for k, v in LIFT_MAPPING.items() if v == name), None)
            intensity, norm, target = SBS_PROGRAM[lift_data.get("category", "primary")].get(week, (0,0,0))
            weight = round((lift_data.get("tm", 0) * intensity) / 2.5) * 2.5
            sets = [{"type": "normal", "reps": norm, "weight_kg": weight} for _ in range(3)]
            sets.append({"type": "failure", "reps": target, "weight_kg": weight})
            if ex_id: exercises_payload.append({"exercise_template_id": ex_id, "notes": f"W{week}: 3x{norm}, 1x{target}+", "sets": sets})
        try:
            r = requests.put(f"{HEVY_BASE_URL}/routines/{r_id}", headers=headers, json={"routine": {"title": current_title, "exercises": exercises_payload}})
            r.raise_for_status()
        except: pass

def get_multiplier(rep_diff):
    multipliers = {0: 1.0, 1: 1.005, 2: 1.01, 3: 1.015, 4: 1.02}
    if rep_diff <= -2: return 0.95
    if rep_diff == -1: return 0.98
    return multipliers.get(rep_diff, 1.03)

def sync_with_hevy():
    headers = {"api-key": HEVY_API_KEY, "Accept": "application/json"}
    try:
        r = requests.get(f"{HEVY_BASE_URL}/workouts", headers=headers, params={"pageSize": 1})
        r.raise_for_status()
        workouts = r.json().get("workouts", [])
        if not workouts: return
        workout = workouts[0]
    except: return
    
    state = load_state()
    if workout.get("id") in state.get("processed_workouts_this_week", []): return
    
    found_any = False
    for ex in workout.get("exercises", []):
        ex_id = ex.get("exercise_template_id")
        lift_name = LIFT_MAPPING.get(ex_id)

        if lift_name:
            if lift_name not in state["main_lifts"]:
                last_set = ex.get("sets", [])[-1]
                weight, reps = last_set.get("weight_kg", 0), last_set.get("reps", 0)
                new_tm = round((weight / (1.0278 - (0.0278 * reps))) * 0.90, 2) if weight and reps > 1 else 100.0
                state["main_lifts"][lift_name] = {"tm": new_tm, "target_reps": 15, "category": "auxiliary"}
                if r_id := workout.get("routine_id"):
                    if r_id in state["routine_map"] and lift_name not in state["routine_map"][r_id]:
                        state["routine_map"][r_id].append(lift_name)
            
            found_any = True
            last_set = ex.get("sets", [])[-1]
            reps, target = last_set.get("reps", 0), state["main_lifts"][lift_name]["target_reps"]
            state["main_lifts"][lift_name]["tm"] = round(state["main_lifts"][lift_name]["tm"] * get_multiplier(reps - target), 2)
            
    if found_any:
        state["processed_workouts_this_week"].append(workout.get("id"))
        if len(state["processed_workouts_this_week"]) >= state["workouts_per_week"]:
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
    else: sync_with_hevy()
