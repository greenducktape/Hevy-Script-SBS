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
    "6AC96645": "DB OHP",
    "29083183": "Chin-ups",
    "1B2B1E7C": "Pull-ups",
    "55E6546F": "Barbell rows"
}

ROUTINE_IDS = {
    "SbS Hyp Day 1 (W1)": "e85acaee-289e-4b1f-8d6a-532c4eb3138f",
    "SbS Hyp Day 2 (W1)": "2194411d-866e-4fd0-8596-fa2302b1421c",
    "SbS Hyp Day 3 (W1)": "a4384cbb-8f1b-4517-bec2-09fdff80efb1"
}

ROUTINE_EXERCISES = {
    "SbS Hyp Day 1 (W1)": ["Squat", "Sumo Deadlift", "Dips", "Chin-ups"],
    "SbS Hyp Day 2 (W1)": ["Bench Press", "OHP", "Bulgarian Split Squat", "Pull-ups"],
    "SbS Hyp Day 3 (W1)": ["Block Pulls", "Long Pause Bench", "Lunges", "DB OHP", "Barbell rows"]
}

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

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f, indent=4)
    update_readme(state)
    update_hevy_routines(state)

def update_readme(state):
    week = state["current_week"]
    dashboard = f"# Hevy to SbS Sync (Hypertrophy) 🏋️‍♂️💪\n\n## 📅 Week {week} / 21\n\n| Exercise | TM | Next Weight | Target |\n| :--- | :--- | :--- | :--- |\n"
    for name, data in state["main_lifts"].items():
        intensity, target = SBS_PROGRAM[data.get("category", "primary")].get(week, (0, 0))
        weight = round((data["tm"] * intensity) / 2.5) * 2.5
        dashboard += f"| {name} | {data['tm']} kg | **{weight} kg** | {target} |\n"
    with open("README.md", "w") as f: f.write(dashboard)

def update_hevy_routines(state):
    if not HEVY_API_KEY: return
    headers = {"api-key": HEVY_API_KEY, "Content-Type": "application/json"}
    week = state["current_week"]
    for title, routine_id in ROUTINE_IDS.items():
        print(f"Pushing updates to Hevy: {title}...")
        exercises_payload = []
        for ex_name in ROUTINE_EXERCISES[title]:
            lift_data = state["main_lifts"].get(ex_name)
            ex_id = next((k for k, v in LIFT_MAPPING.items() if v == ex_name), None)
            if not lift_data:
                sets = [{"type": "normal", "reps": 10, "weight_kg": 0} for _ in range(4)]
                target = 0
            else:
                intensity, target = SBS_PROGRAM[lift_data["category"]].get(week, (0, 0))
                weight = round((lift_data["tm"] * intensity) / 2.5) * 2.5
                reps = 10 if lift_data["category"] == "primary" else 12
                sets = [{"type": "normal", "reps": reps, "weight_kg": weight} for _ in range(3)]
                sets.append({"type": "failure", "reps": target, "weight_kg": weight})
            exercises_payload.append({"exercise_template_id": ex_id, "notes": f"W{week} Target: {target}", "sets": sets})
        payload = {"routine": {"title": title, "exercises": exercises_payload}}
        try:
            r = requests.put(f"{HEVY_BASE_URL}/routines/{routine_id}", headers=headers, json=payload)
            if r.status_code != 200:
                print(f"   ❌ Error {r.status_code}: {r.text}")
            r.raise_for_status()
            print(f"   ✅ Updated {title}")
        except Exception as e:
            print(f"   ❌ Failed {title}: {e}")

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
    if not HEVY_API_KEY:
        print("❌ Error: HEVY_API_KEY not found.")
        return
    
    headers = {"api-key": HEVY_API_KEY, "Accept": "application/json"}
    try:
        r = requests.get(f"{HEVY_BASE_URL}/workouts", headers=headers, params={"pageSize": 1})
        r.raise_for_status()
        workouts = r.json().get("workouts", [])
        if not workouts:
            print("ℹ️ No workouts found in Hevy.")
            return
        workout = workouts[0]
    except Exception as e:
        print(f"❌ API Error: {e}")
        return

    state = load_state()
    if workout.get("id") in state.get("processed_workouts_this_week", []):
        print(f"ℹ️ Workout '{workout.get('title')}' already processed. Skipping.")
        return

    print(f"🔄 Processing: {workout.get('title')} ({workout.get('id')})")
    found_any = False
    for ex in workout.get("exercises", []):
        lift_name = LIFT_MAPPING.get(ex.get("exercise_template_id"))
        if lift_name and lift_name in state["main_lifts"]:
            found_any = True
            sets = ex.get("sets", [])
            last_set = next((s for s in reversed(sets) if s.get("type") == "failure"), sets[-1])
            reps = last_set.get("reps", 0)
            target = state["main_lifts"][lift_name]["target_reps"]
            multiplier = get_multiplier(reps - target)
            old_tm = state["main_lifts"][lift_name]["tm"]
            state["main_lifts"][lift_name]["tm"] = round(old_tm * multiplier, 2)
            print(f"   💪 {lift_name}: {reps} reps (Target {target}) -> TM {old_tm} -> {state['main_lifts'][lift_name]['tm']}")

    if found_any:
        state.setdefault("processed_workouts_this_week", []).append(workout.get("id"))
        if len(state["processed_workouts_this_week"]) >= state.get("workouts_per_week", 3):
            print("🎊 Week complete! Advancing...")
            state["current_week"] += 1
            state["processed_workouts_this_week"] = []
        save_state(state)
        print("✅ Sync successful.")
    else:
        print("ℹ️ No main lifts found in this workout. It won't count toward your 3-day goal.")

if __name__ == "__main__":
    import sys
    if "--next-week" in sys.argv:
        print("⏩ Manually advancing to next week...")
        s = load_state()
        s["current_week"] += 1
        s["processed_workouts_this_week"] = []
        save_state(s)
    else:
        sync_with_hevy()
