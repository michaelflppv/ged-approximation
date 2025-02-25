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
excel_star = "../results/gedlib/PROTEINS/PROTEINS_STAR_results.xlsx"  # Exact GED values

# Load HED and IPFP data (Both contain 'graph1', 'graph2', 'runtime')
df_hed = pd.read_excel(excel_hed, usecols=["graph1", "graph2", "runtime", "ged"])
df_ipfp = pd.read_excel(excel_ipfp, usecols=["graph1", "graph2", "runtime", "ged"])

# Load SimGNN data (No 'graph1', 'graph2', but has 'File' in "pair_id1_id2.json" format)
df_simgnn = pd.read_excel(excel_simgnn, usecols=["File", "Runtime (s)", "Predicted GED"])
df_simgnn["graph1"] = df_simgnn["File"].apply(lambda x: int(re.findall(r"_(\d+)_", x)[0]))
df_simgnn["graph2"] = df_simgnn["File"].apply(lambda x: int(re.findall(r"_(\d+).json", x)[0]))
df_simgnn.rename(columns={"Runtime (s)": "runtime"}, inplace=True)
df_simgnn.rename(columns={"Predicted GED": "ged"}, inplace=True)
df_simgnn.drop(columns=["File"], inplace=True)

# Load Exact GED values from STAR algorithm
df_star = pd.read_excel(excel_star, usecols=["graph1", "graph2", "ged"])
df_star.rename(columns={"ged": "exact_ged"}, inplace=True)

# Merge datasets to find common 1000 graph pairs
df_hed["pair"] = list(zip(df_hed["graph1"], df_hed["graph2"]))
df_ipfp["pair"] = list(zip(df_ipfp["graph1"], df_ipfp["graph2"]))
df_simgnn["pair"] = list(zip(df_simgnn["graph1"], df_simgnn["graph2"]))
df_star["pair"] = list(zip(df_star["graph1"], df_star["graph2"]))

common_pairs = set(df_hed["pair"]) & set(df_ipfp["pair"]) & set(df_simgnn["pair"]) & set(df_star["pair"])
common_pairs = list(common_pairs)[:1000]  # Select 1000 common pairs

# Filter data to only include these pairs
df_hed = df_hed[df_hed["pair"].isin(common_pairs)]
df_ipfp = df_ipfp[df_ipfp["pair"].isin(common_pairs)]
df_simgnn = df_simgnn[df_simgnn["pair"].isin(common_pairs)]
df_star = df_star[df_star["pair"].isin(common_pairs)]

# Merge exact GED values from STAR algorithm
df_hed = df_hed.merge(df_star[["pair", "exact_ged"]], on="pair")
df_ipfp = df_ipfp.merge(df_star[["pair", "exact_ged"]], on="pair")
df_simgnn = df_simgnn.merge(df_star[["pair", "exact_ged"]], on="pair")

# Compute accuracy: 1 - |approximate GED - exact GED| / exact GED
df_hed["accuracy"] = 1 - abs(df_hed["ged"] - df_hed["exact_ged"]) / df_hed["exact_ged"]
df_ipfp["accuracy"] = 1 - abs(df_ipfp["ged"] - df_ipfp["exact_ged"]) / df_ipfp["exact_ged"]
df_simgnn["accuracy"] = 1 - abs(df_simgnn["ged"] - df_simgnn["exact_ged"]) / df_simgnn["exact_ged"]

# Prevent division errors or negative values
df_hed["accuracy"] = df_hed["accuracy"].clip(0, 1)
df_ipfp["accuracy"] = df_ipfp["accuracy"].clip(0, 1)
df_simgnn["accuracy"] = df_simgnn["accuracy"].clip(0, 1)

# Sorting for smooth plotting
df_hed = df_hed.sort_values(by="runtime")
df_ipfp = df_ipfp.sort_values(by="runtime")
df_simgnn = df_simgnn.sort_values(by="runtime")

# Create separate plots for each algorithm
fig, axes = plt.subplots(3, 1, figsize=(12, 12), sharex=True)

for ax, (df, algorithm, color) in zip(axes,
                                      [(df_hed, "HED", "blue"),
                                       (df_ipfp, "IPFP", "orange"),
                                       (df_simgnn, "SimGNN", "green")]):

    # Apply Gaussian smoothing for smooth curves
    smoothed_runtime = gaussian_filter1d(df["runtime"], sigma=5)
    smoothed_accuracy = gaussian_filter1d(df["accuracy"], sigma=5)

    ax.plot(smoothed_runtime, smoothed_accuracy, label=algorithm, color=color, linewidth=2)
    ax.set_xscale("log")  # Log scale for runtime
    ax.set_ylim(0, 1)  # Accuracy is between 0 and 1
    ax.set_ylabel("Accuracy", fontsize=14)
    ax.set_title(f"Runtime vs. Accuracy for {algorithm}", fontsize=16)
    ax.grid(True, which="both", linestyle="--", linewidth=0.5)
    ax.legend()

# Common x-axis label
axes[-1].set_xlabel("Runtime (seconds, log scale)", fontsize=14)

# Show the plots
plt.tight_layout()
plt.show()
