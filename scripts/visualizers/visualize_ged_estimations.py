import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# -------- CONFIGURATION --------
# Excel file paths (replace with actual filenames)
excel_hed = "../results/gedlib/PROTEINS/PROTEINS_HED_results.xlsx"
excel_ipfp = "../results/gedlib/PROTEINS/PROTEINS_IPFP_results.xlsx"
excel_simgnn = "../results/neural/PROTEINS/performance.xlsx"
exact_excel = "../results/gedlib/PROTEINS/PROTEINS_STAR_results.xlsx"

# Output directory
output_folder = "../results/analysis/relative/plots"
os.makedirs(output_folder, exist_ok=True)

# Define Custom Colors for Algorithms
algorithm_colors = {"HED": "#c392ec", "IPFP": "#1a1a1a", "SimGNN": "#85d5c8", "Exact GED": "red"}

# -------- LOAD AND PROCESS DATA --------
df_hed = pd.read_excel(excel_hed)
df_hed["Algorithm"] = "HED"

df_ipfp = pd.read_excel(excel_ipfp)
df_ipfp.replace("", 0, inplace=True)
df_ipfp["Algorithm"] = "IPFP"

df_simgnn = pd.read_excel(excel_simgnn)
df_simgnn["Algorithm"] = "SimGNN"
df_simgnn[["graph1", "graph2"]] = df_simgnn["File"].str.extract(r'pair_(\d+)_(\d+)\.json')

for df in [df_hed, df_ipfp, df_simgnn]:
    df["graph1"] = df["graph1"].astype(str)
    df["graph2"] = df["graph2"].astype(str)

df_hed["GED"] = df_hed["ged"]
df_ipfp["GED"] = df_ipfp["ged"]
df_simgnn["GED"] = df_simgnn["Predicted GED"]

for df in [df_hed, df_ipfp, df_simgnn]:
    df["Graph Pair"] = df["graph1"] + "-" + df["graph2"]

df_ipfp_filtered = df_ipfp[df_ipfp["GED"] <= 25]
df_simgnn_filtered = df_simgnn[df_simgnn["GED"] <= 20]

df_exact_combined = pd.read_excel(exact_excel)
df_exact_combined.drop_duplicates(inplace=True)
df_exact_combined["min_ged_numeric"] = pd.to_numeric(df_exact_combined["ged"], errors="coerce")
df_exact = df_exact_combined.dropna(subset=["min_ged_numeric"])
df_exact["Graph Pair"] = df_exact["graph1"].astype(str) + "-" + df_exact["graph2"].astype(str)

common_pairs = set(df_hed["Graph Pair"]) & set(df_ipfp_filtered["Graph Pair"]) & set(df_simgnn_filtered["Graph Pair"]) & set(df_exact["Graph Pair"])

if len(common_pairs) == 0:
    raise ValueError("No common graph pairs found across all datasets.")

common_pairs = list(common_pairs)[:1000]

df_hed = df_hed[df_hed["Graph Pair"].isin(common_pairs)]
df_ipfp = df_ipfp_filtered[df_ipfp_filtered["Graph Pair"].isin(common_pairs)]
df_simgnn = df_simgnn_filtered[df_simgnn_filtered["Graph Pair"].isin(common_pairs)]
df_exact = df_exact[df_exact["Graph Pair"].isin(common_pairs)]

df_ipfp_renamed = df_ipfp[["Graph Pair", "GED"]].rename(columns={"GED": "ipfp_ged"})
df_exact_sorted = df_exact[["Graph Pair", "min_ged_numeric"]].merge(
    df_ipfp_renamed, on="Graph Pair", how="inner"
)
df_exact_sorted = df_exact_sorted.sort_values(["min_ged_numeric", "ipfp_ged"])
ordered_pairs = df_exact_sorted["Graph Pair"].tolist()

df_combined = pd.concat([df_hed, df_ipfp, df_simgnn], ignore_index=True)
df_combined["Graph Pair"] = pd.Categorical(df_combined["Graph Pair"], categories=ordered_pairs, ordered=True)
df_combined = df_combined.sort_values("Graph Pair")

# -------- FIT POLYNOMIAL CURVES --------
degree = 4  # Degree of polynomial fit

fig, ax = plt.subplots(figsize=(25, 20), dpi=200)

# Enable grid
ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.6)

# Fit and plot polynomial curves for each algorithm
for algo in df_combined["Algorithm"].unique():
    df_algo = df_combined[df_combined["Algorithm"] == algo].copy()

    # Convert categorical Graph Pair index to numeric for polyfit
    x_numeric = np.arange(len(df_algo))
    y_values = df_algo["GED"].values

    # Fit polynomial and generate smooth line
    coeffs = np.polyfit(x_numeric, y_values, degree)
    p = np.poly1d(coeffs)
    x_smooth = np.linspace(x_numeric.min(), x_numeric.max(), 300)
    y_smooth = p(x_smooth)

    ax.plot(x_smooth, y_smooth, label=algo, color=algorithm_colors[algo], linewidth=4.5)

# Fit and plot polynomial curve for Exact GED
x_exact_numeric = np.arange(len(df_exact_sorted["Graph Pair"]))
y_exact_values = df_exact_sorted["min_ged_numeric"].values

# Fit polynomial for exact GED
coeffs_exact = np.polyfit(x_exact_numeric, y_exact_values, degree)
p_exact = np.poly1d(coeffs_exact)
x_exact_smooth = np.linspace(x_exact_numeric.min(), x_exact_numeric.max(), 300)
y_exact_smooth = p_exact(x_exact_smooth)

ax.plot(x_exact_smooth, y_exact_smooth, label="Exact GED", color="red", linewidth=4.5)

# Formatting
plt.xticks(np.linspace(0, len(ordered_pairs)-1, num=10), rotation=45, fontsize=18)
plt.yticks(fontsize=20)
plt.xlabel("Graph Pair (Index)", fontsize=40, fontweight="bold")
plt.ylabel("Graph Edit Distance (GED) Score", fontsize=40, fontweight="bold")
plt.title("Graph Edit Distance (GED) Predictions vs. Exact Computation", fontsize=40, fontweight="bold")
plt.legend(title="Algorithm", fontsize=24, title_fontsize=28, loc="upper left", bbox_to_anchor=(1, 1))
plt.tight_layout()

plot_path_ged = os.path.join(output_folder, "polyfit_ged_comparison.png")
plt.savefig(plot_path_ged, dpi=200, bbox_inches="tight")
plt.show()
print(f"Polynomial fit GED comparison plot saved at: {plot_path_ged}")
