import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# -------- CONFIGURATION --------
# Excel file paths (replace with actual filenames)
excel_hed = "../results/gedlib/PROTEINS/PROTEINS_HED_results.xlsx"
excel_ipfp = "../results/gedlib/PROTEINS/PROTEINS_IPFP_results.xlsx"
excel_simgnn = "../results/neural/PROTEINS/performance.xlsx"
exact_excel_file_1 = "../results/exact_ged/PROTEINS/exact_ged.xlsx"
exact_excel_file_2 = "../results/exact_ged/PROTEINS/exact_ged_2.xlsx"

# Output directory
output_folder = "../results/analysis/relative/plots"
os.makedirs(output_folder, exist_ok=True)

# Define Custom Colors for Algorithms
algorithm_colors = {"HED": "#c392ec", "IPFP": "#1a1a1a", "SimGNN": "#85d5c8"}

# -------- LOAD AND PROCESS DATA --------
# Load HED results
df_hed = pd.read_excel(excel_hed)
df_hed["Algorithm"] = "HED"

# Load IPFP results and replace <unset> values with 0
df_ipfp = pd.read_excel(excel_ipfp)
df_ipfp.replace("", 0, inplace=True)
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
df_hed["GED"] = df_hed["ged"]
df_ipfp["GED"] = df_ipfp["ged"]
df_simgnn["GED"] = df_simgnn["Predicted GED"]

# Create a unique identifier for each graph pair for algorithm predictions
for df in [df_hed, df_ipfp, df_simgnn]:
    df["Graph Pair"] = df["graph1"] + "-" + df["graph2"]

# -------- REMOVE PAIRS WHERE IPFP's GED > 120 (For GED Comparison Plot) --------
df_ipfp_filtered = df_ipfp[df_ipfp["GED"] <= 120]

# -------- LOAD EXACT GED DATA --------
df_exact_1 = pd.read_excel(exact_excel_file_1)
df_exact_2 = pd.read_excel(exact_excel_file_2)

df_exact_combined = pd.concat([df_exact_1, df_exact_2], ignore_index=True)
df_exact_combined.drop_duplicates(inplace=True)
df_exact_combined["min_ged_numeric"] = pd.to_numeric(df_exact_combined["min_ged"], errors="coerce")
df_exact = df_exact_combined.dropna(subset=["min_ged_numeric"])
df_exact["Graph Pair"] = df_exact["graph_id_1"].astype(str) + "-" + df_exact["graph_id_2"].astype(str)

# -------- SELECT COMMON GRAPH PAIRS (For GED Comparison) --------
common_pairs = set(df_hed["Graph Pair"]) & set(df_ipfp_filtered["Graph Pair"]) & set(df_simgnn["Graph Pair"]) & set(df_exact["Graph Pair"])

if len(common_pairs) == 0:
    raise ValueError("No common graph pairs found across all datasets.")

selected_pairs = list(common_pairs)

# Filter datasets to keep only common graph pairs
df_hed = df_hed[df_hed["Graph Pair"].isin(selected_pairs)]
df_ipfp = df_ipfp_filtered[df_ipfp_filtered["Graph Pair"].isin(selected_pairs)]
df_simgnn = df_simgnn[df_simgnn["Graph Pair"].isin(selected_pairs)]
df_exact = df_exact[df_exact["Graph Pair"].isin(selected_pairs)]

# Sort the exact GED data by min_ged_numeric and order graph pairs accordingly
df_exact_sorted = df_exact.sort_values("min_ged_numeric")
ordered_pairs = df_exact_sorted["Graph Pair"].tolist()

# Combine algorithm datasets and order by Graph Pair
df_combined = pd.concat([df_hed, df_ipfp, df_simgnn], ignore_index=True)
df_combined["Graph Pair"] = pd.Categorical(df_combined["Graph Pair"], categories=ordered_pairs, ordered=True)
df_combined = df_combined.sort_values("Graph Pair")

# -------- CREATE GED COMPARISON PLOT --------
sns.set_style("whitegrid")
fig = plt.figure(figsize=(25, 20), dpi=200)

# Plot algorithm predictions (with thicker lines)
ax = sns.lineplot(
    data=df_combined,
    x="Graph Pair",
    y="GED",
    hue="Algorithm",
    marker="o",
    linewidth=4.5,
    palette=algorithm_colors
)

# Overlay the exact GED line in red
ax.plot(
    df_exact_sorted["Graph Pair"],
    df_exact_sorted["min_ged_numeric"],
    marker="o",
    markersize=10,
    linewidth=4.5,
    color="red",
    label="Exact GED"
)

plt.xticks(rotation=45, fontsize=18)  # Rotate x-axis labels at 45° for clarity
plt.yticks(fontsize=20)
plt.xlabel("Graph Pair", fontsize=40, fontweight="bold")
plt.ylabel("Graph Edit Distance (GED) Score", fontsize=40, fontweight="bold")
plt.title("Graph Edit Distance (GED) Predictions vs. Exact Computation", fontsize=40, fontweight="bold")
plt.legend(title="Algorithm", fontsize=24, title_fontsize=28, loc="upper left", bbox_to_anchor=(1, 1))
plt.tight_layout()

plot_path_ged = os.path.join(output_folder, "estimated_ged_comparison.png")
plt.savefig(plot_path_ged, dpi=200, bbox_inches="tight")
plt.show()
print(f"GED comparison plot saved at: {plot_path_ged}")

# -------- SELECT COMMON GRAPH PAIRS (For Runtime Comparison) --------
# For runtime, we consider only algorithm datasets (exact GED is excluded).
# For instance, limit HED runtimes to <= 2 seconds.
df_hed_filtered_runtime = df_hed[df_hed["runtime"] <= 2]

common_pairs_runtime = set(df_hed_filtered_runtime["Graph Pair"]) & set(df_ipfp["Graph Pair"]) & set(df_simgnn["Graph Pair"])

if len(common_pairs_runtime) == 0:
    raise ValueError("No common graph pairs found across algorithm datasets for runtime comparison.")

selected_pairs_runtime = sorted(list(common_pairs_runtime))

# Filter each dataset for runtime comparison
df_hed_rt = df_hed_filtered_runtime[df_hed_filtered_runtime["Graph Pair"].isin(selected_pairs_runtime)]
df_ipfp_rt = df_ipfp[df_ipfp["Graph Pair"].isin(selected_pairs_runtime)]
df_simgnn_rt = df_simgnn[df_simgnn["Graph Pair"].isin(selected_pairs_runtime)]
df_simgnn_rt.rename(columns={"Runtime (s)": "runtime"}, inplace=True)

df_runtime_combined = pd.concat([df_hed_rt, df_ipfp_rt, df_simgnn_rt], ignore_index=True)
df_runtime_combined["Graph Pair"] = pd.Categorical(df_runtime_combined["Graph Pair"], categories=selected_pairs_runtime, ordered=True)
df_runtime_combined = df_runtime_combined.sort_values("Graph Pair")

# -------- CREATE RUNTIME COMPARISON VIOLIN PLOT --------
fig, ax_v = plt.subplots(figsize=(25, 20), dpi=200)

# Create a violin plot for runtime distributions across algorithms.
sns.violinplot(
    data=df_runtime_combined,
    x="Algorithm",
    y="runtime",
    palette=algorithm_colors,
    inner="quartiles",
    cut=0,
    scale="width",
    ax=ax_v
)

# Overlay individual data points using a swarmplot for clarity.
sns.swarmplot(
    data=df_runtime_combined,
    x="Algorithm",
    y="runtime",
    color="k",
    alpha=0.6,
    ax=ax_v
)

# Apply log scale to the y-axis
ax_v.set_yscale("log")
ax_v.grid(True, which="both", linestyle="--", linewidth=0.5, color="lightgray")

plt.xlabel("Algorithm", fontsize=40, fontweight="bold")
plt.ylabel("Runtime (seconds) [log scale]", fontsize=40, fontweight="bold")
plt.title("Runtime Distribution Comparison Across Algorithms", fontsize=40, fontweight="bold")
plt.xticks(fontsize=18)
plt.yticks(fontsize=20)
plt.tight_layout()

plot_path_runtime = os.path.join(output_folder, "runtime_comparison_violin.png")
plt.savefig(plot_path_runtime, dpi=200, bbox_inches="tight")
plt.show()
print(f"Runtime comparison violin plot saved at: {plot_path_runtime}")
