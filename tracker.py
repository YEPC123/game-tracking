import csv
import datetime
import json
import os
import matplotlib.pyplot as plt
import pandas as pd
import requests

GAMES_TO_TRACK = {
    "Kizuna": 79285429406839,
    "Gakuran": 128736949265057,
    "Ishin": 95132192110941,
}

CSV_FILENAME = "player_comparison_log.csv"
UPDATES_FILENAME = "updates.json"
CHART_FILENAME = "player_chart.png"


def get_universe_id(place_id):
  url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
  try:
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
      return response.json().get("universeId")
  except Exception:
    pass
  return None


def fetch_player_counts():
  universe_map = {}
  for name, place_id in GAMES_TO_TRACK.items():
    u_id = get_universe_id(place_id)
    if u_id:
      universe_map[name] = u_id

  if not universe_map:
    return {}

  url = (
      "https://games.roblox.com/v1/games?universeIds="
      f"{','.join(map(str, universe_map.values()))}"
  )
  try:
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
      data = response.json().get("data", [])
      counts = {}
      for game in data:
        for name, u_id in universe_map.items():
          if game["id"] == u_id:
            counts[name] = game.get("playing", 0)
      return counts
  except Exception:
    pass
  return {}


def log_data():
  file_exists = os.path.exists(CSV_FILENAME)
  with open(CSV_FILENAME, mode="a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    if not file_exists:
      header = ["Timestamp"] + list(GAMES_TO_TRACK.keys())
      writer.writerow(header)

  timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  counts = fetch_player_counts()

  row = [timestamp]
  for name in GAMES_TO_TRACK.keys():
    row.append(counts.get(name, 0))

  with open(CSV_FILENAME, mode="a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(row)


def generate_chart_with_updates():
  if not os.path.exists(CSV_FILENAME):
    return

  df = pd.read_csv(CSV_FILENAME)
  df["Timestamp"] = pd.to_datetime(df["Timestamp"])

  plt.figure(figsize=(12, 6))

  # Plot player count lines for each game
  colors = ["#5B9BF5", "#F5A33B", "#4CC38A"]
  for i, game in enumerate(GAMES_TO_TRACK.keys()):
    plt.plot(
        df["Timestamp"],
        df[game],
        label=game,
        marker="o",
        linewidth=2,
        color=colors[i % len(colors)],
    )

  # Load and plot updates if updates.json exists
  if os.path.exists(UPDATES_FILENAME):
    try:
      with open(UPDATES_FILENAME, "r", encoding="utf-8") as f:
        updates = json.load(f)
        for update in updates:
          update_date = pd.to_datetime(update["date"])
          plt.axvline(
              x=update_date,
              color="red",
              linestyle="--",
              alpha=0.6,
              linewidth=1.5,
          )
          plt.text(
              update_date,
              plt.ylim()[1] * 0.9,
              f"  {update['game']}: {update['description']}",
              rotation=90,
              verticalalignment="top",
              fontsize=8,
              color="darkred",
          )
    except Exception:
      pass

  plt.title("Roblox Player Counts Over Time & Game Updates")
  plt.xlabel("Date & Time")
  plt.ylabel("Active Players (CCU)")
  plt.legend()
  plt.grid(True, linestyle="--", alpha=0.5)
  plt.tight_layout()

  plt.savefig(CHART_FILENAME, dpi=300)
  plt.close()


if __name__ == "__main__":
  log_data()
  generate_chart_with_updates()
