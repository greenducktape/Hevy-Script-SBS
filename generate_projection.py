import json
import os

STATE_FILE = "state.json"

# SBS Hypertrophy Program Data
SBS_PROGRAM = {
    "primary": {
        1: (0.70, 12), 2: (0.725, 11), 3: (0.75, 10), 4: (0.725, 11), 5: (0.75, 10), 6: (0.775, 9), 7: (0.50, "Deload"),
        8: (0.75, 10), 9: (0.775, 9), 10: (0.80, 8), 11: (0.775, 9), 12: (0.80, 8), 13: (0.825, 7), 14: (0.50, "Deload"),
        15: (0.80, 8), 16: (0.825, 7), 17: (0.85, 6), 18: (0.825, 7), 19: (0.85, 6), 20: (0.875, 5), 21: (0.50, "Deload")
    },
    "auxiliary": {
        1: (0.65, 15), 2: (0.675, 13), 3: (0.70, 12), 4: (0.675, 13), 5: (0.70, 12), 6: (0.725, 11), 7: (0.50, "Deload"),
        8: (0.70, 12), 9: (0.725, 11), 10: (0.75, 10), 11: (0.725, 11), 12: (0.75, 10), 13: (0.775, 9), 14: (0.50, "Deload"),
        15: (0.75, 10), 16: (0.775, 9), 17: (0.80, 8), 18: (0.775, 9), 19: (0.80, 8), 20: (0.825, 7), 21: (0.50, "Deload")
    }
}

def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def generate_projection():
    state = load_state()
    lifts = state["main_lifts"]
    
    output = "# 21-Week SbS Hypertrophy Projection 📈\n\n"
    output += "> **Note:** Calculated for the Hypertrophy RTF track.\n\n"
    
    for lift_name, data in lifts.items():
        category = data.get("category", "primary")
        tm = data["tm"]
        output += f"## {lift_name} (Current TM: {tm} kg)\n"
        output += "| Week | Intensity | Weight | AMRAP Target |\n"
        output += "| :--- | :--- | :--- | :--- |\n"
        
        for week in range(1, 22):
            intensity, target = SBS_PROGRAM[category].get(week, (0, 0))
            weight = round((tm * intensity) / 2.5) * 2.5
            output += f"| {week} | {intensity*100:.1f}% | **{weight} kg** | {target} |\n"
        output += "\n---\n"
    
    with open("PROJECTION.md", "w") as f: f.write(output)

if __name__ == "__main__":
    generate_projection()
