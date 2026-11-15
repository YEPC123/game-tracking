"""Build ccu_report.png from ccu_log.csv. Run locally after `git pull`."""
import json
import os

import matplotlib.pyplot as plt
import pandas as pd

CSV_PATH = "ccu_log.csv"
UPDATES_PATH = "updates.json"
OUT_PATH = "ccu_report.png"
BASELINE = "Kizuna"      # the game you are comparing against the others
MIN_SAMPLES_PER_DAY = 20  # drop partial days from daily averages

df = pd.read_csv(CSV_PATH)
df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
wide = df.pivot_table(index="timestamp_utc", columns="game", values="playing").sort_index()
games = list(wide.columns)
many = len(wide) > 60

fig, axes = plt.subplots(3, 1, figsize=(12, 14))

# 1) Raw CCU, log scale so a 1k game and a 12k game are both readable
ax = axes[0]
for g in games:
    ax.plot(wide.index, wide[g], label=g, linewidth=1.6, marker=None if many else "o")
ax.set_yscale("log")
ax.set_title("Concurrent players (log scale)")
ax.set_ylabel("CCU")
ax.grid(True, which="both", linestyle="--", alpha=0.4)

# Update markers: only those inside the data window
if os.path.exists(UPDATES_PATH):
    lo, hi = wide.index.min(), wide.index.max()
    with open(UPDATES_PATH, encoding="utf-8") as f:
        for u in json.load(f):
            d = pd.to_datetime(u["date"], utc=True)
            if lo - pd.Timedelta(days=1) <= d <= hi:
                ax.axvline(d, color="red", linestyle="--", alpha=0.6)
                ax.text(d, 0.98, f" {u['game']}: {u['description']}", rotation=90,
                        va="top", fontsize=8, color="darkred",
                        transform=ax.get_xaxis_transform())
ax.legend()

# 2) Baseline as % of each other game, using daily means of full days only
ax = axes[1]
counts = wide.resample("D").count()
daily = wide.resample("D").mean().where(counts >= MIN_SAMPLES_PER_DAY)
plotted = False
if BASELINE in daily:
    for g in games:
        if g == BASELINE:
            continue
        ratio = (daily[BASELINE] / daily[g] * 100).dropna()
        if len(ratio):
            ax.plot(ratio.index, ratio, marker="o", label=f"{BASELINE} as % of {g}")
            plotted = True
ax.set_title(f"{BASELINE} relative to the other games (daily mean, full days only)")
ax.set_ylabel("%")
ax.grid(True, linestyle="--", alpha=0.4)
if plotted:
    ax.legend()
else:
    ax.text(0.5, 0.5, "Needs at least one full day of samples", ha="center",
            va="center", transform=ax.transAxes)

# 3) Time-of-day shape: when do players actually show up? (UTC)
ax = axes[2]
hourly = wide.groupby(wide.index.hour).mean()
norm = hourly / hourly.mean()
for g in games:
    ax.plot(norm.index, norm[g], marker="o", label=g)
ax.set_title("Typical day shape (UTC), each game relative to its own average")
ax.set_xlabel("Hour of day (UTC)")
ax.set_ylabel("x daily average")
ax.set_xticks(range(0, 24, 2))
ax.grid(True, linestyle="--", alpha=0.4)
ax.legend()

fig.tight_layout()
fig.savefig(OUT_PATH, dpi=150)
print(f"Wrote {OUT_PATH} from {len(df)} rows")
