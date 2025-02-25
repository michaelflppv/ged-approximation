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

# Load HED and IPFP data
df_hed = pd.read_excel(excel_hed, usecols=["graph1", "graph2", "runtime", "ged"])
df_ipfp = pd.read_excel(excel_ipfp, usecols=["graph1", "graph2", "runtime", "ged"])

# Load SimGNN data (No 'graph1', 'graph2', but has 'File' in "pair_id1_id2.json" format)
df_simgnn = pd.read_excel(excel_simgnn, usecols=["File", "Runtime (s)", "Predicted GED"])
df_simgnn["graph1"] = df_simgnn["File"].apply(lambda x: int(re.findall(r"_(\d+)_", x)[0]))
df_simgnn["graph2"] = df_simgnn["File"].apply(lambda x: int(re.findall(r"_(\d+).json", x)[0]))
df_simgnn.rename(columns={"Runtime (s)": "runtime", "Predicted GED": "ged"}, inplace=True)
df_simgnn.drop(columns=["File"], inplace=True)

# Load Exact GED values from STAR algorithm
df_star = pd.read_excel(excel_star, usecols=["graph1", "graph2", "ged"])
df_star.rename(columns={"ged": "exact_ged"}, inplace=True)

# Merge datasets to find common graph pairs
df_hed["pair"] = list(zip(df_hed["graph1"], df_hed["graph2"]))
df_ipfp["pair"] = list(zip(df_ipfp["graph1"], df_ipfp["graph2"]))
df_simgnn["pair"] = list(zip(df_simgnn["graph1"], df_simgnn["graph2"]))
df_star["pair"] = list(zip(df_star["graph1"], df_star["graph2"]))

common_pairs = set(df_hed["pair"]) & set(df_ipfp["pair"]) & set(df_simgnn["pair"]) & set(df_star["pair"])

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
df_ipfp["accuracy"] = abs(1 - abs(df_ipfp["ged"] - df_ipfp["exact_ged"]) / df_ipfp["exact_ged"])
df_simgnn["accuracy"] = 1 - abs(df_simgnn["ged"] - df_simgnn["exact_ged"]) / df_simgnn["exact_ged"]

# Clip accuracy values to avoid weird outliers
df_hed["accuracy"] = df_hed["accuracy"].clip(0, 1)
df_ipfp["accuracy"] = df_ipfp["accuracy"].clip(0, 1)
df_simgnn["accuracy"] = df_simgnn["accuracy"].clip(0, 1)

# 🔹 Ensure all three datasets have the same set of graph pairs for alignment
merged_df = df_hed[["pair", "runtime", "accuracy"]].rename(columns={"runtime": "hed_runtime", "accuracy": "hed_accuracy"})
merged_df = merged_df.merge(df_ipfp[["pair", "runtime", "accuracy"]].rename(columns={"runtime": "ipfp_runtime", "accuracy": "ipfp_accuracy"}), on="pair", how="inner")
merged_df = merged_df.merge(df_simgnn[["pair", "runtime", "accuracy"]].rename(columns={"runtime": "simgnn_runtime", "accuracy": "simgnn_accuracy"}), on="pair", how="inner")

# 🔹 Sort data by runtime (ensuring monotonic increase)
merged_df = merged_df.sort_values(by="hed_runtime")
merged_df["hed_runtime"] = np.sort(merged_df["hed_runtime"])
merged_df["ipfp_runtime"] = np.sort(merged_df["ipfp_runtime"])
merged_df["simgnn_runtime"] = np.sort(merged_df["simgnn_runtime"])

# Create separate plots for each algorithm
fig, axes = plt.subplots(3, 1, figsize=(12, 12), sharex=True)

for ax, (runtime_col, accuracy_col, algorithm, color) in zip(axes,
    [("hed_runtime", "hed_accuracy", "HED", "blue"),
     ("ipfp_runtime", "ipfp_accuracy", "IPFP", "orange"),
     ("simgnn_runtime", "simgnn_accuracy", "SimGNN", "green")]):

    # Apply Gaussian smoothing for smooth curves (increased sigma for stability)
    smoothed_runtime = gaussian_filter1d(merged_df[runtime_col], sigma=8)  # 🔹 Smoother curves
    smoothed_accuracy = gaussian_filter1d(merged_df[accuracy_col], sigma=8)

    # Prevent weird loops by forcing monotonic runtime increase
    smoothed_runtime = np.sort(smoothed_runtime)

    # Plot the smoothed data
    ax.plot(smoothed_runtime, smoothed_accuracy, label=algorithm, color=color, linewidth=2)
    ax.set_xscale("log")  # Log scale for runtime
    ax.set_ylim(0, 1)  # Accuracy is between 0 and 1
    ax.set_ylabel("Accuracy", fontsize=14)
    ax.set_title(f"Runtime vs. Accuracy for {algorithm}", fontsize=16)
    ax.grid(True, which="both", linestyle="--", linewidth=0.5)  # ✅ Grid restored
    ax.legend()  # ✅ Legend restored

# 🔹 Apply runtime limits outside the loop
axes[-1].set_xlabel("Runtime (seconds, log scale)", fontsize=14)
for ax in axes:
    ax.set_xlim(2 * (10 ** -3), 3 * (10 ** -3))  # ✅ Keeps all subplots within visible range

# Show the plots
plt.tight_layout()
plt.show()
