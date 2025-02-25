import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import re
from scipy.ndimage import gaussian_filter1d

# File paths
excel_hed = "../results/gedlib/PROTEINS/PROTEINS_HED_results.xlsx"
excel_ipfp = "../results/gedlib/PROTEINS/PROTEINS_IPFP_results.xlsx"
excel_simgnn = "../results/neural/PROTEINS/performance.xlsx"

# Load HED and IPFP data (Both contain 'graph1', 'graph2', 'runtime')
df_hed = pd.read_excel(excel_hed, usecols=["graph1", "graph2", "runtime"])
df_ipfp = pd.read_excel(excel_ipfp, usecols=["graph1", "graph2", "runtime"])

# Load SimGNN data (No 'graph1', 'graph2', but has 'File' in "pair_id1_id2.json" format)
df_simgnn = pd.read_excel(excel_simgnn, usecols=["File", "Runtime (s)"])

# Extract graph IDs from SimGNN's "File" column
df_simgnn["graph1"] = df_simgnn["File"].apply(lambda x: int(re.findall(r"_(\d+)_", x)[0]))
df_simgnn["graph2"] = df_simgnn["File"].apply(lambda x: int(re.findall(r"_(\d+).json", x)[0]))
df_simgnn.rename(columns={"Runtime (s)": "runtime"}, inplace=True)
df_simgnn.drop(columns=["File"], inplace=True)

# Merge datasets to find common 1000 graph pairs
df_hed["pair"] = list(zip(df_hed["graph1"], df_hed["graph2"]))
df_ipfp["pair"] = list(zip(df_ipfp["graph1"], df_ipfp["graph2"]))
df_simgnn["pair"] = list(zip(df_simgnn["graph1"], df_simgnn["graph2"]))

common_pairs = set(df_hed["pair"]) & set(df_ipfp["pair"]) & set(df_simgnn["pair"])
common_pairs = list(common_pairs)[:1000]  # Select 1000 common pairs

# Filter data to only include these pairs
df_hed = df_hed[df_hed["pair"].isin(common_pairs)]
df_ipfp = df_ipfp[df_ipfp["pair"].isin(common_pairs)]
df_simgnn = df_simgnn[df_simgnn["pair"].isin(common_pairs)]

# Add algorithm labels
df_hed["Algorithm"] = "HED"
df_ipfp["Algorithm"] = "IPFP"
df_simgnn["Algorithm"] = "SimGNN"

# Combine datasets
df_combined = pd.concat([df_hed[["Algorithm", "runtime", "pair"]],
                         df_ipfp[["Algorithm", "runtime", "pair"]],
                         df_simgnn[["Algorithm", "runtime", "pair"]]])

# Adjust zero-runtime values for visualization (prevent runtime=0 from disappearing in log scale)
df_combined["runtime"] = df_combined["runtime"].replace(0, np.min(df_combined["runtime"][df_combined["runtime"] > 0]) / 2)

# Sort by graph pairs for better continuity in the plot
df_combined = df_combined.sort_values(by="pair")

# Generate smooth line plot
plt.figure(figsize=(12, 6))

for algorithm, color in zip(["HED", "IPFP", "SimGNN"], ["blue", "orange", "green"]):
    subset = df_combined[df_combined["Algorithm"] == algorithm].copy()
    subset["index"] = range(len(subset))  # Use an index for x-axis to keep continuity

    # Apply Gaussian smoothing to prevent sharp corners
    smoothed_runtime = gaussian_filter1d(subset["runtime"], sigma=5)

    plt.plot(subset["index"], smoothed_runtime, label=algorithm, color=color, linewidth=2)

# Formatting
plt.yscale("log")  # Log scale for better visibility of differences
plt.xlabel("Graph Pair Index (Sorted)", fontsize=14)
plt.ylabel("Runtime (seconds)", fontsize=14)
plt.title("Smoothed Runtime Comparison Across Algorithms", fontsize=16)
plt.legend(title="Algorithm", fontsize=12)
plt.grid(True, which="both", linestyle="--", linewidth=0.5)

# Show plot
plt.show()
