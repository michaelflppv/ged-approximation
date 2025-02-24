import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

def visualize_simgnn_excel(input_excel_path, output_plots_dir):
    # Ensure output directory exists
    os.makedirs(output_plots_dir, exist_ok=True)

    # Read the data
    df = pd.read_excel(input_excel_path)

    # Scatter plot comparing Ground Truth GED vs Predicted GED
    plt.figure(figsize=(6, 6))
    plt.scatter(df["Ground Truth GED"], df["Predicted GED"], alpha=0.5, label="Predicted vs Ground Truth")
    min_val = min(df["Ground Truth GED"].min(), df["Predicted GED"].min())
    max_val = max(df["Ground Truth GED"].max(), df["Predicted GED"].max())
    plt.plot([min_val, max_val], [min_val, max_val], 'r--', label="Perfect Match")
    plt.xlabel("Ground Truth GED")
    plt.ylabel("Predicted GED")
    plt.title("SimGNN Performance Scatter Plot")
    plt.legend()
    plt.savefig(os.path.join(output_plots_dir, "simgnn_scatter.png"))
    plt.close()

    # Histogram of Absolute Error
    plt.figure(figsize=(6, 4))
    plt.hist(df["Absolute Error"], bins=20, color='blue', alpha=0.7)
    plt.xlabel("Absolute Error")
    plt.ylabel("Frequency")
    plt.title("Error Distribution")
    plt.savefig(os.path.join(output_plots_dir, "simgnn_error_hist.png"))
    plt.close()

    # Histogram of Runtime (s)
    plt.figure(figsize=(6, 4))
    plt.hist(df["Runtime (s)"], bins=20, color='green', alpha=0.7)
    plt.xlabel("Runtime (s)")
    plt.ylabel("Frequency")
    plt.title("Runtime Distribution")
    plt.savefig(os.path.join(output_plots_dir, "simgnn_runtime_hist.png"))
    plt.close()

    print(f"Plots saved in {output_plots_dir}")

def visualize_simgnn_excel_detailed(input_excel_path, output_plots_dir):
    os.makedirs(output_plots_dir, exist_ok=True)
    df = pd.read_excel(input_excel_path)

    # 1) Correlation matrix heatmap
    plt.figure(figsize=(8, 6))
    corr_cols = ["Predicted GED", "Ground Truth GED", "Absolute Error",
                 "Squared Error", "Runtime (s)", "Memory Usage (MB)",
                 "Graph1 Nodes", "Graph2 Nodes", "Graph1 Density", "Graph2 Density"]
    corr_data = df[corr_cols].select_dtypes(include=[np.number]).dropna()
    sns.heatmap(corr_data.corr(), annot=True, cmap="YlGnBu", fmt=".2f")
    plt.title("Correlation Matrix")
    plt.tight_layout()
    plt.savefig(os.path.join(output_plots_dir, "simgnn_corr_matrix.png"))
    plt.close()

    # 2) Box plot of Memory Usage (MB) grouped by Absolute Error range
    plt.figure(figsize=(6, 4))
    df["Error Range"] = pd.cut(df["Absolute Error"], bins=[-0.01, 0.5, 1.0, 2.0, 1000],
                               labels=["0-0.5", "0.5-1.0", "1.0-2.0", ">2.0"])
    sns.boxplot(x="Error Range", y="Memory Usage (MB)", data=df, palette="Set2")
    plt.title("Memory Usage by Error Range")
    plt.savefig(os.path.join(output_plots_dir, "simgnn_memory_box.png"))
    plt.close()

    # 3) Bar plot of Graph1 Density vs. Graph2 Density
    plt.figure(figsize=(6, 4))
    idx = np.arange(len(df))
    width = 0.3
    plt.bar(idx - width/2, df["Graph1 Density"], width, label="Graph1")
    plt.bar(idx + width/2, df["Graph2 Density"], width, label="Graph2")
    plt.title("Graph Density Comparison")
    plt.xlabel("Pair Index")
    plt.ylabel("Density")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_plots_dir, "simgnn_density_bar.png"))
    plt.close()

    print(f"Additional plots saved in {output_plots_dir}")

if __name__ == "__main__":
    # Provide the path to the Excel file and the directory where plots should be saved.
    input_path = "../results/neural/PROTEINS/performance.xlsx"
    output_dir = "../results/analysis/SimGNN/PROTEINS/plots"
    visualize_simgnn_excel(input_path, output_dir)
    visualize_simgnn_excel_detailed(input_path, output_dir)