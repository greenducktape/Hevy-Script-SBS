import json
import os

STATE_FILE = "state.json"

# SBS 21-Week Program Data: (Intensity %, AMRAP Target)
SBS_PROGRAM = {
    "primary": {
        1: (0.70, 10), 2: (0.75, 8), 3: (0.80, 6), 4: (0.725, 9), 5: (0.775, 7), 6: (0.825, 5), 7: (0.50, "Deload"),
        8: (0.75, 8), 9: (0.80, 6), 10: (0.85, 4), 11: (0.775, 7), 12: (0.825, 5), 13: (0.875, 3), 14: (0.50, "Deload"),
        15: (0.80, 6), 16: (0.85, 4), 17: (0.90, 2), 18: (0.825, 5), 19: (0.875, 3), 20: (0.925, 2), 21: (1.00, 1)
    },
    "auxiliary": {
        1: (0.60, 14), 2: (0.65, 12), 3: (0.70, 10), 4: (0.625, 13), 5: (0.675, 11), 6: (0.725, 9), 7: (0.50, "Deload"),
        8: (0.65, 12), 9: (0.70, 10), 10: (0.75, 8), 11: (0.675, 11), 12: (0.725, 9), 13: (0.775, 7), 14: (0.50, "Deload"),
        15: (0.70, 10), 16: (0.75, 8), 17: (0.80, 6), 18: (0.725, 9), 19: (0.775, 7), 20: (0.825, 5), 21: (1.00, 1)
    }
}

def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def generate_projection():
    state = load_state()
    lifts = state["main_lifts"]
    
    output = "# 21-Week SbS Training Projection 📈\n\n"
    output += "> **Note:** These weights are calculated based on your *current* Training Maxes. If you beat your rep targets, your weights in later weeks will be higher than shown here.\n\n"
    
    for lift_name, data in lifts.items():
        category = data.get("category", "primary")
        tm = data["tm"]
        
        output += f"## {lift_name} (Current TM: {tm} kg)\n"
        output += "| Week | Intensity | Weight | Target Reps |\n"
        output += "| :--- | :--- | :--- | :--- |\n"
        
        for week in range(1, 22):
            intensity, target = SBS_PROGRAM[category].get(week, (0, 0))
            weight = round((tm * intensity) / 2.5) * 2.5
            
            target_display = target if isinstance(target, int) else target
            if target == 0: target_display = "N/A"
            
            output += f"| {week} | {intensity*100:.1f}% | **{weight} kg** | {target_display} |\n"
        
        output += "\n---\n"
    
    with open("PROJECTION.md", "w") as f:
        f.write(output)
    print("Successfully generated PROJECTION.md")

if __name__ == "__main__":
    generate_projection()
