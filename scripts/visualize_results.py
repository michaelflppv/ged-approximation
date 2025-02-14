import pandas as pd
import matplotlib.pyplot as plt
import os

# Paths
ANALYSIS_CSV = "results/summary_analysis.csv"
PLOTS_DIR = "results/plots/"

# Ensure the directory exists
os.makedirs(PLOTS_DIR, exist_ok=True)

def plot_scatter(df, dataset):
    """Scatter plot of Exact GED vs. Approximate GED."""
    plt.figure(figsize=(6, 6))
    plt.scatter(df["ged_gedlib"], df["ged_simgnn"], alpha=0.5, label="SimGNN Approx.")
    plt.plot([df["ged_gedlib"].min(), df["ged_gedlib"].max()],
             [df["ged_gedlib"].min(), df["ged_gedlib"].max()], 'r--', label="Perfect Match")
    plt.xlabel("Exact GED (GEDLIB)")
    plt.ylabel("Approximate GED (SimGNN)")
    plt.title(f"GED Approximation - {dataset}")
    plt.legend()
    plt.savefig(os.path.join(PLOTS_DIR, f"{dataset}_scatter.png"))
    plt.close()

def plot_error_distribution(df, dataset):
    """Histogram of approximation errors."""
    plt.figure(figsize=(6, 4))
    plt.hist(df["approximation_error"], bins=20, color='blue', alpha=0.7)
    plt.xlabel("Approximation Error")
    plt.ylabel("Frequency")
    plt.title(f"Approximation Error Distribution - {dataset}")
    plt.savefig(os.path.join(PLOTS_DIR, f"{dataset}_error_histogram.png"))
    plt.close()

def plot_runtime_comparison(df, dataset):
    """Bar chart comparing runtime."""
    avg_runtime_gedlib = df["runtime_gedlib"].mean()
    avg_runtime_simgnn = df["runtime_simgnn"].mean()

    plt.figure(figsize=(6, 4))
    plt.bar(["GEDLIB", "SimGNN"], [avg_runtime_gedlib, avg_runtime_simgnn], color=["red", "green"])
    plt.ylabel("Average Runtime (seconds)")
    plt.title(f"Runtime Comparison - {dataset}")
    plt.savefig(os.path.join(PLOTS_DIR, f"{dataset}_runtime_comparison.png"))
    plt.close()

def visualize_results():
    """Generate and save all plots for each dataset."""
    df = pd.read_csv(ANALYSIS_CSV)

    datasets = df["dataset"].unique()
    for dataset in datasets:
        dataset_df = df[df["dataset"] == dataset]
        plot_scatter(dataset_df, dataset)
        plot_error_distribution(dataset_df, dataset)
        plot_runtime_comparison(dataset_df, dataset)

    print(f"Plots saved in {PLOTS_DIR}")

if __name__ == "__main__":
    visualize_results()
