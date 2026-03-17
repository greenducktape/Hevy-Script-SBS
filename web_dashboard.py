from flask import Flask, render_template_string
from sbs_logic import SBS_PROGRAM, load_state

app = Flask(__name__)

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hevy → SbS Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; background: #f6f8fa; color: #1f2328; }
    .card { background: white; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
    table { border-collapse: collapse; width: 100%; }
    th, td { border-bottom: 1px solid #d0d7de; padding: 0.5rem; text-align: left; }
    .ok { color: #1a7f37; font-weight: 700; }
    .warn { color: #9a6700; font-weight: 700; }
    .small { color: #57606a; font-size: 0.9rem; }
    a { color: #0969da; text-decoration: none; }
  </style>
</head>
<body>
  <h1>Hevy → Stronger by Science Dashboard</h1>

  <div class="card">
    <h2>Current Program Status</h2>
    <p><strong>Week:</strong> {{ state.current_week }} / 21</p>
    <p><strong>Workouts processed this week:</strong> {{ processed }} / {{ state.workouts_per_week }}</p>
    <p class="small">This page reads from your local <code>state.json</code> and checks if each lift's stored target reps matches the expected target for the current week.</p>
  </div>

  <div class="card">
    <h2>Week Validation</h2>
    <table>
      <thead>
        <tr>
          <th>Lift</th>
          <th>Category</th>
          <th>Stored Target Reps</th>
          <th>Expected Target (Week {{ state.current_week }})</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
      {% for row in validation_rows %}
        <tr>
          <td>{{ row.name }}</td>
          <td>{{ row.category }}</td>
          <td>{{ row.stored_target }}</td>
          <td>{{ row.expected_target }}</td>
          <td class="{{ 'ok' if row.is_ok else 'warn' }}">{{ 'OK' if row.is_ok else 'CHECK' }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>Quick Links</h2>
    <ul>
      <li><a href="/week/{{ state.current_week }}">View week {{ state.current_week }} loading plan</a></li>
      {% if state.current_week < 21 %}
      <li><a href="/week/{{ state.current_week + 1 }}">Preview next week (week {{ state.current_week + 1 }})</a></li>
      {% endif %}
    </ul>
  </div>
</body>
</html>
"""

WEEK_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Week {{ week }} Plan</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; background: #f6f8fa; color: #1f2328; }
    .card { background: white; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
    table { border-collapse: collapse; width: 100%; }
    th, td { border-bottom: 1px solid #d0d7de; padding: 0.5rem; text-align: left; }
    a { color: #0969da; text-decoration: none; }
  </style>
</head>
<body>
  <h1>Week {{ week }} Plan</h1>
  <p><a href="/">← Back to dashboard</a></p>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th>Lift</th>
          <th>Category</th>
          <th>TM (kg)</th>
          <th>Intensity</th>
          <th>Working Weight (kg)</th>
          <th>Normal Sets</th>
          <th>AMRAP Target</th>
        </tr>
      </thead>
      <tbody>
      {% for row in rows %}
        <tr>
          <td>{{ row.name }}</td>
          <td>{{ row.category }}</td>
          <td>{{ row.tm }}</td>
          <td>{{ row.intensity }}</td>
          <td>{{ row.weight }}</td>
          <td>3x{{ row.normal_sets }}</td>
          <td>{{ row.target }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


@app.route("/")
def dashboard():
    state = load_state()
    week = state["current_week"]
    rows = []

    for name, lift in state["main_lifts"].items():
        category = lift.get("category", "primary")
        _, _, expected_target = SBS_PROGRAM[category].get(week, (0, 0, 0))
        stored_target = lift.get("target_reps")
        rows.append(
            {
                "name": name,
                "category": category,
                "stored_target": stored_target,
                "expected_target": expected_target,
                "is_ok": stored_target == expected_target,
            }
        )

    return render_template_string(
        TEMPLATE,
        state=state,
        processed=len(state.get("processed_workouts_this_week", [])),
        validation_rows=sorted(rows, key=lambda r: r["name"]),
    )


@app.route("/week/<int:week>")
def week_plan(week: int):
    state = load_state()
    rows = []

    for name, lift in state["main_lifts"].items():
        category = lift.get("category", "primary")
        intensity, normal_sets, target = SBS_PROGRAM[category].get(week, (0, 0, 0))
        tm = lift.get("tm", 0)
        weight = round((tm * intensity) / 2.5) * 2.5
        rows.append(
            {
                "name": name,
                "category": category,
                "tm": tm,
                "intensity": f"{intensity * 100:.1f}%",
                "weight": weight,
                "normal_sets": normal_sets,
                "target": target,
            }
        )

    return render_template_string(WEEK_TEMPLATE, week=week, rows=sorted(rows, key=lambda r: r["name"]))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
