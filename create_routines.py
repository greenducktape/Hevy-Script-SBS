import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
HEVY_API_KEY = os.getenv("HEVY_API_KEY")
HEVY_BASE_URL = "https://api.hevyapp.com/v1"
STATE_FILE = "state.json"

# IDs from your provided list
EXERCISE_IDS = {
    "Squat": "D04AC939",
    "Bench Press": "79D0BB3A",
    "Sumo Deadlift": "D20D7BBE",
    "OHP": "7B8D84E8",
    "Dips": "6FCD7755",
    "Bulgarian Split Squat": "B5D3A742",
    "Block Pulls": "FE389074",
    "Long Pause Bench": "50DFDFAB",
    "Lunges": "6E6EE645",
    "DB OHP": "6AC96645",
    "Chin-ups": "29083183",
    "Pull-ups": "1B2B1E7C",
    "Barbell rows": "55E6546F"
}

def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def create_routine(title, exercises_data):
    if not HEVY_API_KEY: return
    headers = {"api-key": HEVY_API_KEY, "Content-Type": "application/json", "Accept": "application/json"}
    payload = {"routine": {"title": title, "folder_id": None, "exercises": exercises_data}}
    try:
        response = requests.post(f"{HEVY_BASE_URL}/routines", headers=headers, json=payload)
        response.raise_for_status()
        print(f"Successfully created: {title}")
    except Exception as e:
        print(f"Failed {title}: {e}")

def build_exercise_payload(name, state):
    if name not in EXERCISE_IDS: return None
    lift_data = state["main_lifts"].get(name)
    
    # Defaults for non-main lifts
    if not lift_data:
        return {"exercise_template_id": EXERCISE_IDS[name], "sets": [{"type": "normal", "reps": 10, "weight_kg": 0} for _ in range(3)]}

    category = lift_data.get("category", "primary")
    
    # HYPERTROPHY WEEK 1 LOGIC
    # Primary: 70% TM | 3 sets of 10 | 1 AMRAP target 12
    # Auxiliary: 65% TM | 3 sets of 12 | 1 AMRAP target 15
    if category == "primary":
        intensity, reps, target = 0.70, 10, 12
    else:
        intensity, reps, target = 0.65, 12, 15
    
    weight = round((lift_data["tm"] * intensity) / 2.5) * 2.5
    
    sets = []
    for _ in range(3): # 3 Normal Sets
        sets.append({"type": "normal", "reps": reps, "weight_kg": weight})
    sets.append({"type": "failure", "reps": target, "weight_kg": weight}) # 1 AMRAP Set

    return {
        "exercise_template_id": EXERCISE_IDS[name],
        "notes": f"Hypertrophy Week 1 | Target: {target} reps",
        "sets": sets
    }

def main():
    state = load_state()
    
    routines = [
        ("SbS Hyp Day 1 (W1)", ["Squat", "Sumo Deadlift", "Dips", "Chin-ups"]),
        ("SbS Hyp Day 2 (W1)", ["Bench Press", "OHP", "Bulgarian Split Squat", "Pull-ups"]),
        ("SbS Hyp Day 3 (W1)", ["Block Pulls", "Long Pause Bench", "Lunges", "DB OHP", "Barbell rows"])
    ]
    
    for title, ex_names in routines:
        payload = [build_exercise_payload(n, state) for n in ex_names]
        create_routine(title, [p for p in payload if p])

if __name__ == "__main__":
    main()
