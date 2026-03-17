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
    "Chin-ups": "29083183",  # Chin Up
    "Pull-ups": "1B2B1E7C",  # Pull Up
    "Barbell rows": "55E6546F" # Bent Over Row (Barbell)
}

def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def create_routine(title, exercises_data):
    """Sends a POST request to Hevy to create a routine."""
    if not HEVY_API_KEY:
        print("Error: HEVY_API_KEY not found.")
        return

    headers = {
        "api-key": HEVY_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "routine": {
            "title": title,
            "folder_id": None,
            "exercises": exercises_data
        }
    }

    try:
        response = requests.post(f"{HEVY_BASE_URL}/routines", headers=headers, json=payload)
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
        response.raise_for_status()
        print(f"Successfully created routine: {title}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to create routine '{title}': {e}")

def build_exercise_payload(name, state, sets_count=5):
    """Builds the exercise payload for Hevy with calculated weights for Week 1."""
    if name not in EXERCISE_IDS:
        print(f"Warning: ID for {name} not found.")
        return None

    lift_data = state["main_lifts"].get(name)
    if not lift_data:
        # For exercises without a TM (like Chin-ups/Pull-ups)
        return {
            "exercise_template_id": EXERCISE_IDS[name],
            "sets": [{"type": "normal", "reps": 10, "weight_kg": 0} for _ in range(sets_count)]
        }

    # SbS Week 1: Primary 70%, Auxiliary 60%
    category = lift_data.get("category", "primary")
    intensity = 0.70 if category == "primary" else 0.60
    target_reps = 10 if category == "primary" else 14
    
    # Calculate starting weight (rounded to nearest 2.5kg)
    weight = round((lift_data["tm"] * intensity) / 2.5) * 2.5

    sets = []
    # 4 Normal Sets
    for _ in range(sets_count - 1):
        sets.append({
            "type": "normal",
            "reps": 5 if category == "primary" else 7, # Default SbS sets
            "weight_kg": weight
        })
    # 1 Failure (AMRAP) Set
    sets.append({
        "type": "failure",
        "reps": target_reps,
        "weight_kg": weight
    })

    return {
        "exercise_template_id": EXERCISE_IDS[name],
        "notes": f"SbS Week 1 | Target: {target_reps} reps",
        "sets": sets
    }

def main():
    state = load_state()
    
    # Day 1: Squat, Sumo Deadlift, Dips, Chin-ups
    day1_exercises = [
        build_exercise_payload("Squat", state),
        build_exercise_payload("Sumo Deadlift", state),
        build_exercise_payload("Dips", state),
        build_exercise_payload("Chin-ups", state)
    ]
    create_routine("SbS Day 1 (Week 1)", [ex for ex in day1_exercises if ex])

    # Day 2: Bench Press, OHP, Bulgarian Split Squat, Pull-ups
    day2_exercises = [
        build_exercise_payload("Bench Press", state),
        build_exercise_payload("OHP", state),
        build_exercise_payload("Bulgarian Split Squat", state),
        build_exercise_payload("Pull-ups", state)
    ]
    create_routine("SbS Day 2 (Week 1)", [ex for ex in day2_exercises if ex])

    # Day 3: Block Pulls, Long Pause Bench, Lunges, DB OHP, Barbell rows
    day3_exercises = [
        build_exercise_payload("Block Pulls", state),
        build_exercise_payload("Long Pause Bench", state),
        build_exercise_payload("Lunges", state),
        build_exercise_payload("DB OHP", state),
        build_exercise_payload("Barbell rows", state)
    ]
    create_routine("SbS Day 3 (Week 1)", [ex for ex in day3_exercises if ex])

if __name__ == "__main__":
    main()
