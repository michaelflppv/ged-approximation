#!/usr/bin/env python3

import os
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# Set a modern, stylish theme
sns.set_theme(style="whitegrid", palette="muted")


def main():
    # Determine the directory of this script.
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define the path to the Excel file (adjust the relative path as needed)
    excel_path = "../results/neural/PROTEINS/performance.xlsx"

    if not os.path.exists(excel_path):
        print(f"Error: Excel file '{excel_path}' does not exist.")
        return

    # Load the Excel file.
    df = pd.read_excel(excel_path)

    # Create additional columns: Average Nodes and Average Density.
    if "Graph1 Nodes" in df.columns and "Graph2 Nodes" in df.columns:
        df["Avg_Nodes"] = (df["Graph1 Nodes"] + df["Graph2 Nodes"]) / 2
    else:
        print("Warning: Graph node count columns not found.")
        df["Avg_Nodes"] = np.nan

    if "Graph1 Density" in df.columns and "Graph2 Density" in df.columns:
        df["Avg_Density"] = (df["Graph1 Density"] + df["Graph2 Density"]) / 2
    else:
        print("Warning: Graph density columns not found.")
        df["Avg_Density"] = np.nan

    # Create a folder to save plots.
    plots_dir = "../results/analysis/SimGNN/PROTEINS/plots"
    os.makedirs(plots_dir, exist_ok=True)

    # 1. Performance Accuracy Analysis
    plt.figure(figsize=(8, 6))
    ax = sns.scatterplot(data=df, x="Ground Truth GED", y="Predicted GED", s=70, color="steelblue", edgecolor="w")
    # Plot diagonal y=x
    max_val = max(df["Ground Truth GED"].max(), df["Predicted GED"].max())
    plt.plot([0, max_val], [0, max_val], ls="--", c="red")
    plt.title("Performance Accuracy Analysis")
    plt.xlabel("Ground Truth GED")
    plt.ylabel("Predicted GED")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "performance_accuracy.png"))
    plt.close()

    # 2. Error Distribution Analysis (Absolute Error)
    plt.figure(figsize=(8, 6))
    sns.histplot(df["Absolute Error"], bins=30, kde=True, color="forestgreen")
    plt.title("Error Distribution Analysis (Absolute Error)")
    plt.xlabel("Absolute Error")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "error_distribution.png"))
    plt.close()

    # 3.1 Effect of Graph Size: Scatter Plot with Trendline
    plt.figure(figsize=(8, 6))
    sns.regplot(data=df, x="Avg_Nodes", y="Absolute Error", scatter_kws={'s': 50}, line_kws={"color": "red"})
    plt.title("Effect of Graph Size on Absolute Error")
    plt.xlabel("Average Number of Nodes in Pair")
    plt.ylabel("Absolute Error")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "effect_graph_size.png"))
    plt.close()

    # 3.2 Effect of Graph Density: Scatter Plot with Trendline
    plt.figure(figsize=(8, 6))
    sns.regplot(data=df, x="Avg_Density", y="Absolute Error", scatter_kws={'s': 50}, line_kws={"color": "red"})
    plt.title("Effect of Graph Density on Absolute Error")
    plt.xlabel("Average Graph Density")
    plt.ylabel("Absolute Error")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "effect_graph_density.png"))
    plt.close()

    # 4. Runtime vs Accuracy: Scatter Plot
    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=df, x="Runtime (s)", y="Absolute Error", s=70, color="mediumpurple", edgecolor="w")
    plt.title("Runtime vs Absolute Error")
    plt.xlabel("Runtime per Pair (s)")
    plt.ylabel("Absolute Error")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "runtime_vs_error.png"))
    plt.close()

    # 5. Identifying Worst-Case Scenarios: Box Plot
    # Bin the Ground Truth GED into 3 categories using quantiles.
    try:
        df["GED_Bin"] = pd.qcut(df["Ground Truth GED"], q=3, labels=["Small GED", "Medium GED", "Large GED"])
    except Exception as e:
        print("Warning: Could not bin Ground Truth GED:", e)
        df["GED_Bin"] = "Unknown"

    plt.figure(figsize=(8, 6))
    sns.boxplot(data=df, x="GED_Bin", y="Absolute Error", palette="Set2")
    plt.title("Absolute Error by Binned Ground Truth GED")
    plt.xlabel("Binned Ground Truth GED")
    plt.ylabel("Absolute Error")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "error_by_ged_bin.png"))
    plt.close()

    # 6. Overall Correlation Heatmap
    cols = ["Predicted GED", "Ground Truth GED", "Absolute Error",
            "Graph1 Nodes", "Graph2 Nodes", "Graph1 Density", "Graph2 Density",
            "Runtime (s)", "Memory Usage (MB)"]
    # Only use columns that exist in the dataframe.
    cols = [c for c in cols if c in df.columns]
    corr = df[cols].corr()
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", square=True)
    plt.title("Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "correlation_heatmap.png"))
    plt.close()

    # 7. Correlation between Memory Usage and Graph Sizes/Densities
    # Create average node count and density columns are already created.
    fig, ax = plt.subplots(1, 2, figsize=(14, 6))
    sns.regplot(data=df, x="Avg_Nodes", y="Memory Usage (MB)", ax=ax[0], scatter_kws={'s': 50},
                line_kws={"color": "red"})
    ax[0].set_title("Memory Usage vs Average Nodes")
    ax[0].set_xlabel("Average Number of Nodes")
    ax[0].set_ylabel("Memory Usage (MB)")

    sns.regplot(data=df, x="Avg_Density", y="Memory Usage (MB)", ax=ax[1], scatter_kws={'s': 50},
                line_kws={"color": "red"})
    ax[1].set_title("Memory Usage vs Average Density")
    ax[1].set_xlabel("Average Graph Density")
    ax[1].set_ylabel("Memory Usage (MB)")

    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "memory_vs_size_density.png"))
    plt.close()

    print("All plots saved in:", plots_dir)


if __name__ == "__main__":
    main()
