# Web Interface (Local Dashboard)

You can run a simple local dashboard to verify that your SbS weeks are progressing correctly.

## What it gives you

- Current week status from `state.json`
- Validation check per lift (`target_reps` vs expected week target)
- Per-week plan preview page with intensity, working weight, normal sets, and AMRAP target

## Run it locally

1. Install dependencies:

```bash
pip install flask
```

2. Start the dashboard:

```bash
python web_dashboard.py
```

3. Open:

```text
http://localhost:8000
```

## Do you need a domain?

- **No**, not for personal use. You can run this locally and open it only when needed.
- If you want to access it from anywhere, deploy to a host (Render/Fly.io/Railway) and then optionally buy a domain.

## Recommended next step

If you want this live 24/7 with no manual steps, deploy this repo to a small cloud service and use environment variables for your Hevy API key.
