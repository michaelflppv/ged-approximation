import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# -------- CONFIGURATIONS --------
# Input Excel file
excel_file = "heuristic_lower_bounds.xlsx"  # Replace with your actual file
sheet_name = "Sheet1"  # Adjust if necessary

# Output directory
output_folder = "plots"
os.makedirs(output_folder, exist_ok=True)

# Define Custom Colors for Heuristics (HEX Codes)
custom_colors = ["#c392ec", "#1a1a1a", "#85d5c8", "#cbe957", "#723eff", "#03624c"]

# -------- LOAD DATA --------
# Read Excel file
df = pd.read_excel(excel_file, sheet_name=sheet_name)

# Ensure required columns exist
required_columns = {"graph_id1", "graph_id2", "Heuristic", "Lower Bound"}
if not required_columns.issubset(df.columns):
    raise ValueError(f"Excel file must contain columns: {required_columns}")

# Combine `graph_id1` and `graph_id2` to form unique graph pair identifiers
df["Graph Pair"] = df["graph_id1"].astype(str) + "-" + df["graph_id2"].astype(str)

# Select the first 100 rows
df = df.head(100)

# -------- CREATE PLOT --------
# Set seaborn style
sns.set_style("whitegrid")
sns.set_palette(custom_colors)

# Create Figure with adjusted size (max 5000x4000 pixels)
fig = plt.figure(figsize=(25, 20), dpi=200)  # (5000px / 200 dpi, 4000px / 200 dpi)

# Line Plot: Lower Bound Estimations across Different Heuristics
ax = sns.lineplot(
    data=df, x="Graph Pair", y="Lower Bound", hue="Heuristic", marker="o", linewidth=3.5
)

# Improve Aesthetics
plt.xticks(rotation=90, fontsize=18)  # Rotate x-axis labels for readability
plt.yticks(fontsize=20)
plt.xlabel("Graph Pair", fontsize=28, fontweight="bold")  # Larger X-label
plt.ylabel("Lower Bound Estimation", fontsize=28, fontweight="bold")  # Larger Y-label
plt.title("Comparison of Lower Bound Estimations Across Heuristics", fontsize=32, fontweight="bold")

# Make Legend (Table of Contents) Bigger
plt.legend(
    title="Heuristic", fontsize=22, title_fontsize=26, loc="upper left", bbox_to_anchor=(1, 1)
)

# Tight Layout for Better Spacing
plt.tight_layout()

# Save Plot with Max Resolution of 5000x4000 pixels
plot_path = os.path.join(output_folder, "lower_bound_comparison.png")
plt.savefig(plot_path, dpi=200, bbox_inches="tight")

# Show Plot
plt.show()

print(f"Plot saved at: {plot_path}")
