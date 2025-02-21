import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# -------- CONFIGURATION --------
# Excel file paths (replace with actual filenames)
excel_hed = "../../../results/gedlib/PROTEINS/PROTEINS_HED_results.xlsx"
excel_ipfp = "../../../results/gedlib/PROTEINS_IPFP_results.xlsx"
excel_simgnn = "../../../results/neural/PROTEINS/performance.xlsx"

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

# Extract graph1 and graph2 from "File" column in SimGNN
df_simgnn[["graph1", "graph2"]] = df_simgnn["File"].str.extract(r'pair_(\d+)_(\d+)\.json')

# Ensure graph IDs are treated as strings for uniformity
for df in [df_hed, df_ipfp, df_simgnn]:
    df["graph1"] = df["graph1"].astype(str)
    df["graph2"] = df["graph2"].astype(str)

# Standardize column names
df_hed["GED"] = df_hed["ged"]
df_ipfp["GED"] = df_ipfp["ged"]
df_simgnn["GED"] = df_simgnn["Predicted GED"]

# Create a unique identifier for each graph pair
for df in [df_hed, df_ipfp, df_simgnn]:
    df["Graph Pair"] = df["graph1"] + "-" + df["graph2"]

# -------- SELECT 100 COMMON GRAPH PAIRS --------
# Find the **common** graph pairs in all three datasets
common_pairs = set(df_hed["Graph Pair"]) & set(df_ipfp["Graph Pair"]) & set(df_simgnn["Graph Pair"])

# Filter out pairs where IPFP's estimated GED exceeds 100
valid_pairs = df_ipfp[df_ipfp["GED"] <= 100]["Graph Pair"]
common_pairs = list(common_pairs & set(valid_pairs))

# Randomly select **100 valid common pairs**
if len(common_pairs) >= 100:
    selected_pairs = pd.Series(common_pairs).sample(n=100, random_state=42)
else:
    raise ValueError(f"Only {len(common_pairs)} valid pairs found after filtering. Need at least 100.")

# Filter each dataset to only include these 100 pairs
df_hed = df_hed[df_hed["Graph Pair"].isin(selected_pairs)]
df_ipfp = df_ipfp[df_ipfp["Graph Pair"].isin(selected_pairs)]
df_simgnn = df_simgnn[df_simgnn["Graph Pair"].isin(selected_pairs)]

# Merge into a single DataFrame
df_combined = pd.concat([df_hed, df_ipfp, df_simgnn], ignore_index=True)

# -------- CREATE PLOT --------
# Set seaborn style
sns.set_style("whitegrid")

# Create Figure (max 5000x4000 pixels)
fig = plt.figure(figsize=(25, 20), dpi=200)  # (5000px / 200 dpi, 4000px / 200 dpi)

# Line Plot: GED estimations across algorithms
ax = sns.lineplot(
    data=df_combined,
    x="Graph Pair",
    y="GED",
    hue="Algorithm",
    marker="o",
    linewidth=3.5,
    palette=algorithm_colors
)

# Improve Aesthetics
plt.xticks(rotation=90, fontsize=18)  # Rotate x-axis labels for better readability
plt.yticks(fontsize=20)
plt.xlabel("Graph Pair", fontsize=28, fontweight="bold")  # Larger X-label
plt.ylabel("Estimated GED", fontsize=28, fontweight="bold")  # Larger Y-label
plt.title("Comparison of Estimated GED Across Algorithms", fontsize=32, fontweight="bold")

# Make Legend (Table of Contents) Bigger
plt.legend(
    title="Algorithm", fontsize=22, title_fontsize=26, loc="upper left", bbox_to_anchor=(1, 1)
)

# Tight Layout for Better Spacing
plt.tight_layout()

# Save Plot with Max Resolution of 5000x4000 pixels
plot_path = os.path.join(output_folder, "estimated_ged_comparison.png")
plt.savefig(plot_path, dpi=200, bbox_inches="tight")

# Show Plot
plt.show()

print(f"Plot saved at: {plot_path}")