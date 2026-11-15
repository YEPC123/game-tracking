import csv
import datetime
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt

# 1. Define the 3 games (these are Place IDs, and the script will resolve them automatically)
GAMES_TO_TRACK = {
    "Kizuna": 79285429406839,
    "Gakuran": 128736949265057,
    "Ishin": 95132192110941
}

CSV_FILENAME = "player_comparison_log.csv"

def get_universe_id(place_id):
    """Dynamically converts a Roblox Place ID to its corresponding Universe ID."""
    url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("universeId")
    except Exception as e:
        print(f"Error resolving Place ID {place_id}: {e}")
    return None

def fetch_player_counts():
    # Resolve Place IDs to Universe IDs first
    universe_map = {}
    for name, place_id in GAMES_TO_TRACK.items():
        u_id = get_universe_id(place_id)
        if u_id:
            universe_map[name] = u_id
        else:
            print(f"Could not resolve Universe ID for {name} (Place ID: {place_id})")

    if not universe_map:
        return {}

    universe_ids = list(universe_map.values())
    url = f"https://games.roblox.com/v1/games?universeIds={','.join(map(str, universe_ids))}"
    
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
    except Exception as e:
        print(f"Error fetching player counts: {e}")
    return {}

def log_and_visualize():
    file_exists = os.path.exists(CSV_FILENAME)
    with open(CSV_FILENAME, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            header = ["Timestamp"] + list(GAMES_TO_TRACK.keys())
            writer.writerow(header)
            
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    counts = fetch_player_counts()
    
    row = [timestamp]
    for name in GAMES_TO_TRACK.keys():
        row.append(counts.get(name, 0))
        
    with open(CSV_FILENAME, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(row)
        
    print(f"[{timestamp}] Successfully fetched and logged player counts!")

# Run the snapshot fetch
log_and_visualize()

# Load the CSV and plot the current comparison
df = pd.read_csv(CSV_FILENAME)
print("\n--- Logged Data History ---")
display(df)

# Plotting the latest snapshot comparison
latest_data = df.iloc[-1]
games = list(GAMES_TO_TRACK.keys())
players = [latest_data[game] for game in games]

max_p = max(players) if max(players) > 0 else 1

plt.figure(figsize=(8, 5))
plt.bar(games, players, color=['#5B9BF5', '#F5A33B', '#4CC38A'])
plt.title("Live Player Count Comparison Snapshot")
plt.xlabel("Games")
plt.ylabel("Active Players (CCU)")
plt.grid(axis='y', linestyle='--', alpha=0.7)
for i, v in enumerate(players):
    plt.text(i, v + (max_p * 0.01), f"{v:,}", ha='center', fontweight='bold')

plt.show()
