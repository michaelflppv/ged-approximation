import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# -------- CONFIGURATIONS --------
# Input Excel files
heuristic_excel_file = "heuristic_lower_bounds.xlsx"  # File with heuristic estimates
exact_excel_file_1 = "../results/exact_ged/PROTEINS/exact_ged.xlsx"  # File with exact GED values
exact_excel_file_2 = "../results/exact_ged/PROTEINS/exact_ged_2.xlsx"  # File with exact GED values

# Output directory for plots
output_folder = "plots"
os.makedirs(output_folder, exist_ok=True)

# Define Custom Colors for Heuristics (HEX Codes)
custom_colors = ["#c392ec", "#1a1a1a", "#85d5c8", "#cbe957", "#723eff", "#03624c"]

# -------- LOAD DATA --------
# Read the heuristics Excel file
df_heuristics = pd.read_excel(heuristic_excel_file)

# Ensure required columns exist in heuristics file
required_heuristic_cols = {"graph_id1", "graph_id2", "Heuristic", "Lower Bound"}
if not required_heuristic_cols.issubset(df_heuristics.columns):
    raise ValueError(f"Heuristic file must contain columns: {required_heuristic_cols}")

# Filter rows where "Dataset" is "PROTEINS"
df_heuristics = df_heuristics[df_heuristics["Dataset"] == "PROTEINS"]

# Create a common "Graph Pair" column for heuristics (e.g., "12-34")
df_heuristics["Graph Pair"] = df_heuristics["graph_id1"].astype(str) + "-" + df_heuristics["graph_id2"].astype(str)

# Read the exact GED Excel file
df_exact_1 = pd.read_excel(exact_excel_file_1)
df_exact_2 = pd.read_excel(exact_excel_file_2)

# Merge the dataframes
df_exact_combined = pd.concat([df_exact_1, df_exact_2], ignore_index=True)
# Drop duplicates if any
df_exact_combined.drop_duplicates(inplace=True)

# Ensure required columns exist in exact GED file
required_exact_cols = {"graph_id_1", "graph_id_2", "min_ged"}
if not required_exact_cols.issubset(df_exact_combined.columns):
    raise ValueError(f"Exact GED file must contain columns: {required_exact_cols}")

# Convert "min_ged" to numeric (set errors to NaN) and filter out non-numeric ("N/A") rows
df_exact_combined["min_ged_numeric"] = pd.to_numeric(df_exact_combined["min_ged"], errors="coerce")
df_exact = df_exact_combined.dropna(subset=["min_ged_numeric"])

# Create a common "Graph Pair" column for exact GED (note: column names differ slightly)
df_exact["Graph Pair"] = df_exact["graph_id_1"].astype(str) + "-" + df_exact["graph_id_2"].astype(str)

# -------- SELECT COMMON PAIRS --------
# Find common pairs between the two data sources
common_pairs = set(df_heuristics["Graph Pair"]).intersection(set(df_exact["Graph Pair"]))

# Filter both dataframes to only include these common pairs
df_heuristics_common = df_heuristics[df_heuristics["Graph Pair"].isin(common_pairs)]
df_exact_common = df_exact[df_exact["Graph Pair"].isin(common_pairs)]

# Sort the common pairs based on "min_ged_numeric"
df_exact_common_sorted = df_exact_common.sort_values("min_ged_numeric")
common_order = df_exact_common_sorted["Graph Pair"].tolist()

df_heuristics_common["Graph Pair"] = pd.Categorical(df_heuristics_common["Graph Pair"],
                                                    categories=common_order,
                                                    ordered=True)
df_exact_common["Graph Pair"] = pd.Categorical(df_exact_common["Graph Pair"],
                                               categories=common_order,
                                               ordered=True)

# -------- CREATE PLOT --------
sns.set_style("whitegrid")
sns.set_palette(custom_colors)

# Create Figure with adjusted size (max 5000x4000 pixels)
fig = plt.figure(figsize=(25, 20), dpi=200)

# Line Plot: Plot lower bound estimates across different heuristics
ax = sns.lineplot(
    data=df_heuristics_common,
    x="Graph Pair",
    y="Lower Bound",
    hue="Heuristic",
    marker="o",
    linewidth=3.5
)

# Plot the exact GED line in red.
ax.plot(
    df_exact_common_sorted["Graph Pair"],
    df_exact_common_sorted["min_ged_numeric"],
    marker="o",
    markersize=10,
    linewidth=3.5,
    color="red",
    label="Exact GED"
)

# Improve Aesthetics
plt.xticks(rotation=90, fontsize=18)  # Rotate x-axis labels for readability
plt.yticks(fontsize=20)
plt.xlabel("Graph Pair", fontsize=40, fontweight="bold")
plt.ylabel("Lower Bound Estimation", fontsize=40, fontweight="bold")
plt.title("Comparison of Lower Bound Estimations Across Heuristics", fontsize=40, fontweight="bold")

# Increase Legend size and position it appropriately
plt.legend(title="Heuristic", fontsize=22, title_fontsize=26, loc="upper left", bbox_to_anchor=(1, 1))

plt.tight_layout()

# Save Plot with max resolution of 5000x4000 pixels
plot_path = os.path.join(output_folder, "lower_bound_comparison.png")
plt.savefig(plot_path, dpi=200, bbox_inches="tight")
plt.show()

print(f"Plot saved at: {plot_path}")