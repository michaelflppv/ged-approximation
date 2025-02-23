import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# -------- CONFIGURATION --------
# Excel file paths (replace with actual filenames)
excel_hed    = "../../../results/gedlib/PROTEINS/PROTEINS_HED_results.xlsx"
excel_ipfp   = "../../../results/gedlib/PROTEINS_IPFP_results.xlsx"
excel_simgnn = "../../../results/neural/PROTEINS/performance.xlsx"
excel_exact  = "../../../results/exact_ged/PROTEINS/exact_ged.xlsx"

# Output directory
output_folder = "plots"
os.makedirs(output_folder, exist_ok=True)

# Define Custom Colors for Algorithms
algorithm_colors = {"HED": "#c392ec", "IPFP": "#1a1a1a", "SimGNN": "#85d5c8"}

# -------- LOAD AND PROCESS DATA --------
# Load HED results
df_hed = pd.read_excel(excel_hed)
df_hed["Algorithm"] = "HED"

# Load IPFP results
df_ipfp = pd.read_excel(excel_ipfp)
df_ipfp["Algorithm"] = "IPFP"

# Load SimGNN results and extract graph pairs
df_simgnn = pd.read_excel(excel_simgnn)
df_simgnn["Algorithm"] = "SimGNN"
df_simgnn[["graph1", "graph2"]] = df_simgnn["File"].str.extract(r'pair_(\d+)_(\d+)\.json')

# Ensure graph IDs are treated as strings for uniformity
for df in [df_hed, df_ipfp, df_simgnn]:
    df["graph1"] = df["graph1"].astype(str)
    df["graph2"] = df["graph2"].astype(str)

# Standardize column names for predicted GED
df_hed["GED"]    = df_hed["ged"]
df_ipfp["GED"]   = df_ipfp["ged"]
df_simgnn["GED"] = df_simgnn["Predicted GED"]

# Create a unique identifier for each graph pair for algorithm predictions
for df in [df_hed, df_ipfp, df_simgnn]:
    df["Graph Pair"] = df["graph1"] + "-" + df["graph2"]

# -------- LOAD EXACT GED DATA --------
df_exact = pd.read_excel(excel_exact)
# Ensure required columns exist
required_exact_cols = {"graph_id_1", "graph_id_2", "min_ged"}
if not required_exact_cols.issubset(df_exact.columns):
    raise ValueError(f"Exact GED file must contain columns: {required_exact_cols}")
# Convert "min_ged" to numeric and drop rows with N/A
df_exact["min_ged_numeric"] = pd.to_numeric(df_exact["min_ged"], errors="coerce")
df_exact = df_exact.dropna(subset=["min_ged_numeric"])
# Create a unique identifier for each graph pair in the exact GED file
df_exact["Graph Pair"] = df_exact["graph_id_1"].astype(str) + "-" + df_exact["graph_id_2"].astype(str)

# -------- SELECT COMMON GRAPH PAIRS (for GED comparison) --------
# Find common pairs among all three algorithm datasets and the exact GED file
common_pairs = (set(df_hed["Graph Pair"]) &
                set(df_ipfp["Graph Pair"]) &
                set(df_simgnn["Graph Pair"]) &
                set(df_exact["Graph Pair"]))

if len(common_pairs) == 0:
    raise ValueError("No common graph pairs found across all datasets.")

# Use all common pairs (instead of selecting 100)
selected_pairs = list(common_pairs)

# Filter each dataset to only include these common pairs
df_hed    = df_hed[df_hed["Graph Pair"].isin(selected_pairs)]
df_ipfp   = df_ipfp[df_ipfp["Graph Pair"].isin(selected_pairs)]
df_simgnn = df_simgnn[df_simgnn["Graph Pair"].isin(selected_pairs)]
df_exact  = df_exact[df_exact["Graph Pair"].isin(selected_pairs)]

# Sort the exact GED data by min_ged_numeric and order the graph pairs accordingly
df_exact_sorted = df_exact.sort_values("min_ged_numeric")
ordered_pairs = df_exact_sorted["Graph Pair"].tolist()

# Ensure the combined DataFrame follows the sorted order
df_combined = pd.concat([df_hed, df_ipfp, df_simgnn], ignore_index=True)
df_combined["Graph Pair"] = pd.Categorical(df_combined["Graph Pair"], categories=ordered_pairs, ordered=True)
df_combined = df_combined.sort_values("Graph Pair")

# -------- CREATE GED COMPARISON PLOT --------
sns.set_style("whitegrid")
fig = plt.figure(figsize=(25, 20), dpi=200)

# Line Plot: Plot GED estimates across algorithms
ax = sns.lineplot(
    data=df_combined,
    x="Graph Pair",
    y="GED",
    hue="Algorithm",
    marker="o",
    linewidth=3.5,
    palette=algorithm_colors
)

# Plot the exact GED line in red.
ax.plot(
    df_exact_sorted["Graph Pair"],
    df_exact_sorted["min_ged_numeric"],
    marker="o",
    markersize=10,
    linewidth=3.5,
    color="red",
    label="Exact GED"
)

plt.xticks(rotation=90, fontsize=18)
plt.yticks(fontsize=20)
plt.xlabel("Graph Pair", fontsize=40, fontweight="bold")
plt.ylabel("Estimated GED", fontsize=40, fontweight="bold")
plt.title("Comparison of Predicted GED Across Algorithms", fontsize=40, fontweight="bold")
plt.legend(title="Algorithm", fontsize=22, title_fontsize=26, loc="upper left", bbox_to_anchor=(1, 1))
plt.tight_layout()

plot_path_ged = os.path.join(output_folder, "estimated_ged_comparison.png")
plt.savefig(plot_path_ged, dpi=200, bbox_inches="tight")
plt.show()
print(f"GED comparison plot saved at: {plot_path_ged}")

# -------- SELECT COMMON GRAPH PAIRS (for Runtime Comparison) --------
# For runtime, consider only the three algorithm datasets (exclude exact GED)
common_pairs_runtime = (set(df_hed["Graph Pair"]) &
                          set(df_ipfp["Graph Pair"]) &
                          set(df_simgnn["Graph Pair"]))

if len(common_pairs_runtime) == 0:
    raise ValueError("No common graph pairs found across algorithm datasets for runtime comparison.")

# Use all common pairs among algorithms
selected_pairs_runtime = sorted(list(common_pairs_runtime))

# Filter each algorithm DataFrame for runtime comparison
df_hed_rt    = df_hed[df_hed["Graph Pair"].isin(selected_pairs_runtime)]
df_ipfp_rt   = df_ipfp[df_ipfp["Graph Pair"].isin(selected_pairs_runtime)]
df_simgnn_rt = df_simgnn[df_simgnn["Graph Pair"].isin(selected_pairs_runtime)]

# Combine runtime data into a single DataFrame and order by Graph Pair
df_runtime_combined = pd.concat([df_hed_rt, df_ipfp_rt, df_simgnn_rt], ignore_index=True)
df_runtime_combined["Graph Pair"] = pd.Categorical(df_runtime_combined["Graph Pair"], categories=selected_pairs_runtime, ordered=True)
df_runtime_combined = df_runtime_combined.sort_values("Graph Pair")

# -------- CREATE RUNTIME COMPARISON PLOT --------
fig = plt.figure(figsize=(25, 20), dpi=200)
ax_rt = sns.lineplot(
    data=df_runtime_combined,
    x="Graph Pair",
    y="runtime",
    hue="Algorithm",
    marker="o",
    linewidth=3.5,
    palette=algorithm_colors
)

plt.xticks(rotation=90, fontsize=18)
plt.yticks(fontsize=20)
plt.xlabel("Graph Pair", fontsize=40, fontweight="bold")
plt.ylabel("Runtime (seconds)", fontsize=40, fontweight="bold")
plt.title("Runtime Comparison Across Algorithms", fontsize=40, fontweight="bold")
plt.legend(title="Algorithm", fontsize=22, title_fontsize=26, loc="upper left", bbox_to_anchor=(1, 1))
plt.tight_layout()

plot_path_runtime = os.path.join(output_folder, "runtime_comparison.png")
plt.savefig(plot_path_runtime, dpi=200, bbox_inches="tight")
plt.show()
print(f"Runtime comparison plot saved at: {plot_path_runtime}")
