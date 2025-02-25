#!/usr/bin/env python3
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re

# -------- CONFIGURATION --------
# Excel file paths
excel_hed = "../results/gedlib/PROTEINS/PROTEINS_HED_results.xlsx"
excel_ipfp = "../results/gedlib/PROTEINS/PROTEINS_IPFP_results.xlsx"
excel_simgnn = "../results/neural/PROTEINS/performance.xlsx"

# Output directory
output_folder = "../results/analysis/relative/plots"
os.makedirs(output_folder, exist_ok=True)

algorithm_colors = {"HED": "#c392ec", "IPFP": "#1a1a1a", "SimGNN": "#85d5c8"}

# -------- LOAD AND PROCESS DATA --------
# Load HED results
df_hed = pd.read_excel(excel_hed)
df_hed["Algorithm"] = "HED"
# Ensure graph IDs are strings and create "Graph Pair"
df_hed["graph1"] = df_hed["graph1"].astype(str)
df_hed["graph2"] = df_hed["graph2"].astype(str)
df_hed["Graph Pair"] = df_hed["graph1"] + "-" + df_hed["graph2"]
df_hed["runtime"] = pd.to_numeric(df_hed["runtime"], errors="coerce")

# Load IPFP results
df_ipfp = pd.read_excel(excel_ipfp)
df_ipfp.replace("", 0, inplace=True)
df_ipfp["Algorithm"] = "IPFP"
df_ipfp["graph1"] = df_ipfp["graph1"].astype(str)
df_ipfp["graph2"] = df_ipfp["graph2"].astype(str)
df_ipfp["Graph Pair"] = df_ipfp["graph1"] + "-" + df_ipfp["graph2"]
df_ipfp["runtime"] = pd.to_numeric(df_ipfp["runtime"], errors="coerce")

# Load SimGNN results; extract graph IDs from the "File" column.
df_simgnn = pd.read_excel(excel_simgnn)
df_simgnn["Algorithm"] = "SimGNN"
# Extract graph ids using regex (e.g., "pair_12_34.json")
df_simgnn[["graph1", "graph2"]] = df_simgnn["File"].str.extract(r'pair_(\d+)_(\d+)\.json')
df_simgnn["graph1"] = df_simgnn["graph1"].astype(str)
df_simgnn["graph2"] = df_simgnn["graph2"].astype(str)
df_simgnn["Graph Pair"] = df_simgnn["graph1"] + "-" + df_simgnn["graph2"]
# Rename runtime column to a common name and convert to numeric
df_simgnn.rename(columns={"Runtime (s)": "runtime"}, inplace=True)
df_simgnn["runtime"] = pd.to_numeric(df_simgnn["runtime"], errors="coerce")

# -------- SELECT 100 COMMON GRAPH PAIRS --------
# Find the intersection of graph pairs across the three datasets.
common_pairs = set(df_hed["Graph Pair"]) & set(df_ipfp["Graph Pair"]) & set(df_simgnn["Graph Pair"])
if len(common_pairs) < 100:
    raise ValueError(f"Only {len(common_pairs)} common pairs found; at least 100 required.")
# Randomly sample 100 common pairs.
selected_pairs = pd.Series(list(common_pairs)).sample(n=100, random_state=42).tolist()

# Filter each dataset to keep only the selected common pairs.
df_hed = df_hed[df_hed["Graph Pair"].isin(selected_pairs)]
df_ipfp = df_ipfp[df_ipfp["Graph Pair"].isin(selected_pairs)]
df_simgnn = df_simgnn[df_simgnn["Graph Pair"].isin(selected_pairs)]

# Combine the runtime data from the three algorithms.
df_runtime = pd.concat([
    df_hed[["Algorithm", "Graph Pair", "runtime"]],
    df_ipfp[["Algorithm", "Graph Pair", "runtime"]],
    df_simgnn[["Algorithm", "Graph Pair", "runtime"]]
], ignore_index=True)

# Some runtime values might be zero. To ensure a visible violin shape, add a small constant.
df_runtime["runtime"] = df_runtime["runtime"].replace(0, 0.001)

# -------- CREATE RUNTIME COMPARISON VIOLIN PLOT --------
sns.set_style("whitegrid")
plt.figure(figsize=(12, 8), dpi=200)

# Create the violin plot:
# - x-axis: Algorithm (categorical)
# - y-axis: runtime (seconds) on log scale
# - inner=None ensures no individual dots are drawn.
ax = sns.violinplot(
    data=df_runtime,
    x="Algorithm",
    y="runtime",
    palette=algorithm_colors,
    inner=None,
    width=1.0,    # Increase width to make violins larger
    cut=0,        # Do not extend violins past the extreme data points
    scale="area"
)

# Apply a log scale to the y-axis for better visualization of small runtimes.
plt.yscale("log")
plt.xlabel("Algorithm", fontsize=16, fontweight="bold")
plt.ylabel("Runtime (seconds) [log scale]", fontsize=16, fontweight="bold")
plt.title("Runtime Distribution Comparison Across Algorithms", fontsize=18, fontweight="bold")
plt.tight_layout()

plot_path = os.path.join(output_folder, "runtime_comparison_violin.png")
plt.savefig(plot_path, dpi=200, bbox_inches="tight")
plt.show()
print(f"Runtime violin plot saved at: {plot_path}")
