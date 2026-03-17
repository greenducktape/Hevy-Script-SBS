import json
import os
import requests
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Configuration
STATE_FILE = "state.json"
HEVY_API_KEY = os.getenv("HEVY_API_KEY")
HEVY_BASE_URL = "https://api.hevyapp.com/v1"

# Mapping: Hevy Exercise Title OR exercise_template_id -> Internal Lift Name
LIFT_MAPPING = {
    "Squat (Barbell)": "Squat",
    "Bench Press (Barbell)": "Bench Press",
    "Deadlift (Sumo)": "Sumo Deadlift",
    "Overhead Press (Barbell)": "OHP",
    "Dips": "Dips",
    "Bulgarian Split Squat": "Bulgarian Split Squat",
    "Rack Pull": "Block Pulls",
    "Pause Bench Press": "Long Pause Bench",
    "Lunge (Barbell)": "Lunges",
    "Dumbbell Shoulder Press": "DB OHP"
}

def load_state():
    """Loads the training state from state.json."""
    if not os.path.exists(STATE_FILE):
        print(f"Error: {STATE_FILE} not found.")
        return None
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    """Saves the updated training state to state.json."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def get_multiplier(rep_difference):
    """Returns the Training Max multiplier based on the rep difference."""
    if rep_difference <= -2:
        return 0.95
    elif rep_difference == -1:
        return 0.98
    elif rep_difference == 0:
        return 1.00
    elif rep_difference == 1:
        return 1.005
    elif rep_difference == 2:
        return 1.01
    elif rep_difference == 3:
        return 1.015
    elif rep_difference == 4:
        return 1.02
    else:  # >= 5
        return 1.03

def calculate_new_tm(state, lift_name, actual_reps, target_reps):
    """Applies the SbS progression logic to calculate a new Training Max within the state object."""
    if lift_name not in state["main_lifts"]:
        print(f"   Error: Lift '{lift_name}' not found in state.")
        return state

    lift_data = state["main_lifts"][lift_name]
    current_tm = lift_data["tm"]
    rep_difference = actual_reps - target_reps
    multiplier = get_multiplier(rep_difference)
    
    new_tm = round(current_tm * multiplier, 2)
    state["main_lifts"][lift_name]["tm"] = new_tm

    print(f"   -> Updated {lift_name}: TM {current_tm} -> {new_tm} (Diff: {rep_difference}, Multiplier: {multiplier})")
    return state

def fetch_latest_workout():
    """Fetches the most recent workout from Hevy API."""
    if not HEVY_API_KEY:
        print("Error: HEVY_API_KEY not found in environment.")
        return None

    headers = {"api-key": HEVY_API_KEY, "Accept": "application/json"}
    params = {"page": 1, "pageSize": 1}
    
    try:
        response = requests.get(f"{HEVY_BASE_URL}/workouts", headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        workouts = data.get("workouts", [])
        return workouts[0] if workouts else None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from Hevy: {e}")
        return None

def list_exercise_templates():
    """Helper to list all available exercise titles and their IDs."""
    if not HEVY_API_KEY:
        print("Error: HEVY_API_KEY not found in environment.")
        return

    headers = {"api-key": HEVY_API_KEY, "Accept": "application/json"}
    
    try:
        print("Fetching exercise templates...")
        response = requests.get(f"{HEVY_BASE_URL}/exercise_templates", headers=headers)
        response.raise_for_status()
        templates = response.json()
        
        print(f"{'Title':<40} | {'ID':<10}")
        print("-" * 55)
        for t in templates:
            print(f"{t.get('title', 'Unknown'):<40} | {t.get('id', 'N/A'):<10}")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

def sync_with_hevy():
    """Syncs latest Hevy workout with SbS progression logic."""
    print("--- Hevy to SbS Sync ---")
    workout = fetch_latest_workout()
    
    if not workout:
        print("No workout found to sync.")
        return

    print(f"Found workout: {workout.get('title')} ({workout.get('start_time')})")
    
    state = load_state()
    if not state:
        return

    found_any = False
    for exercise in workout.get("exercises", []):
        title = exercise.get("title")
        template_id = exercise.get("exercise_template_id")
        
        # Match by Title OR ID
        lift_name = LIFT_MAPPING.get(title) or LIFT_MAPPING.get(template_id)
        
        if lift_name and lift_name in state["main_lifts"]:
            found_any = True
            sets = exercise.get("sets", [])
            if not sets:
                continue
                
            # SbS Logic: Look for the 'failure' set, otherwise use the last set
            failure_set = next((s for s in reversed(sets) if s.get("type") == "failure"), sets[-1])
            
            actual_reps = failure_set.get("reps", 0)
            target_reps = state["main_lifts"][lift_name]["target_reps"]
            
            print(f"Processing: {title} (Target: {target_reps}, Actual: {actual_reps})")
            state = calculate_new_tm(state, lift_name, actual_reps, target_reps)

    if found_any:
        save_state(state)
    else:
        print("No matching main lifts found in the latest workout.")
    print("------------------------")

if __name__ == "__main__":
    import sys
    if "--list-exercises" in sys.argv:
        list_exercise_templates()
    else:
        sync_with_hevy()
