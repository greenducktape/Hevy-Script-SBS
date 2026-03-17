# Hevy to SbS Sync 🏋️‍♂️🤖

![Sync Status](https://github.com/greenducktape/Hevy-Script-SBS/actions/workflows/sync_hevy.yml/badge.svg)

This project automatically syncs workout data from the **Hevy App** and calculates new **Training Maxes** based on the **Stronger by Science (SbS)** Reps to Failure progression logic.

## 📊 Current Training State
The "source of truth" for your current Training Maxes is stored in [state.json](./state.json).

## 🚀 How to monitor
1. **Live Logs:** Go to the [Actions Tab](https://github.com/greenducktape/Hevy-Script-SBS/actions) to see the history of syncs.
2. **Manual Sync:** If you just finished a workout and don't want to wait for the nightly sync, go to the Actions tab, select "Sync Hevy Workout Data," and click **Run workflow**.

## 🛠 Setup Reminder
Ensure you have added your `HEVY_API_KEY` to the **Secrets** section of this repository.

---
*Created by Gemini CLI*
