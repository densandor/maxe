import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

csv_path = Path(__file__).parent.parent / "logs/L1Log.csv"

# load CSV without headers (first column is milliseconds steps)
df = pd.read_csv(csv_path, header=None)

# name the first three columns (time_ms, ask, bid); additional columns are kept if present
df = df.rename(columns={0: "time_ms", 1: "bid", 2: "ask"})

# convert to numeric and drop rows with missing/invalid values
df["time_ms"] = pd.to_numeric(df["time_ms"], errors="coerce")
df["bid"] = pd.to_numeric(df["bid"], errors="coerce")
df["ask"] = pd.to_numeric(df["ask"], errors="coerce")
df = df.dropna(subset=["time_ms", "bid", "ask"])

spread = df["ask"] - df["bid"]

# plot (time in milliseconds)
plt.figure(figsize=(12, 6))
plt.plot(df["time_ms"], spread, label="Spread")
plt.xlabel("Time (ms)")
plt.ylabel("Price")
plt.title("Spread (Ask - Bid)")
plt.legend()
plt.grid(True)
plt.show()
