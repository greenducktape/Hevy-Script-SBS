import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
HEVY_API_KEY = os.getenv("HEVY_API_KEY")
HEVY_BASE_URL = "https://api.hevyapp.com/v1"
STATE_FILE = "state.json"

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

SBS_PROGRAM = {
    "primary": {1: (0.70, 10, 12)},
    "auxiliary": {1: (0.65, 12, 15)}
}

def load_state():
    with open(STATE_FILE, "r") as f: return json.load(f)

def create_routine(title, exercises_data):
    headers = {"api-key": HEVY_API_KEY, "Content-Type": "application/json"}
    payload = {"routine": {"title": title, "exercises": exercises_data}}
    requests.post(f"{HEVY_BASE_URL}/routines", headers=headers, json=payload)

def build_exercise_payload(name, state):
    if name not in EXERCISE_IDS: return None
    lift_data = state["main_lifts"].get(name)
    if not lift_data: return {"exercise_template_id": EXERCISE_IDS[name], "sets": [{"type": "normal", "reps": 10, "weight_kg": 0} for _ in range(4)]}
    
    intensity, norm, target = SBS_PROGRAM[lift_data["category"]][1]
    weight = round((lift_data["tm"] * intensity) / 2.5) * 2.5
    
    sets = [{"type": "normal", "reps": norm, "weight_kg": weight} for _ in range(3)]
    sets.append({"type": "failure", "reps": target, "weight_kg": weight})
    return {"exercise_template_id": EXERCISE_IDS[name], "notes": f"W1: 3x{norm}, 1x{target}+", "sets": sets}

def main():
    state = load_state()
    routines = [
        ("SbS Hyp Day 1", ["Squat", "Sumo Deadlift", "Dips", "Chin-ups"]),
        ("SbS Hyp Day 2", ["Bench Press", "OHP", "Bulgarian Split Squat", "Pull-ups"]),
        ("SbS Hyp Day 3", ["Block Pulls", "Long Pause Bench", "Lunges", "DB OHP", "Barbell rows"])
    ]
    for title, ex_names in routines:
        payload = [build_exercise_payload(n, state) for n in ex_names]
        create_routine(f"{title} (W1)", [p for p in payload if p])

if __name__ == "__main__":
    main()
