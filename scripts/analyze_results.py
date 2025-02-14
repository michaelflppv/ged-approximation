import pandas as pd
import json
import os

# Paths to results
GEDLIB_RESULTS_PATH = "results/gedlib/"
NEURAL_RESULTS_PATH = "results/neural/"
OUTPUT_CSV = "results/summary_analysis.csv"


def load_gedlib_results(dataset):
    """Load GEDLIB results from Excel."""
    file_path = os.path.join(GEDLIB_RESULTS_PATH, f"{dataset}_results.xlsx")
    df = pd.read_excel(file_path)
    return df


def load_simgnn_results(dataset):
    """Load SimGNN results from JSON."""
    file_path = os.path.join(NEURAL_RESULTS_PATH, f"{dataset}_predictions.json")
    with open(file_path, "r") as f:
        data = json.load(f)
    return pd.DataFrame(data)


def analyze_results(dataset):
    """Computes error metrics and runtime comparisons."""
    gedlib_df = load_gedlib_results(dataset)
    simgnn_df = load_simgnn_results(dataset)

    # Merge results on graph pairs
    merged_df = pd.merge(gedlib_df, simgnn_df, on="graph_pair", suffixes=("_gedlib", "_simgnn"))

    # Compute errors
    merged_df["approximation_error"] = abs(merged_df["ged_simgnn"] - merged_df["ged_gedlib"])
    merged_df["relative_error"] = merged_df["approximation_error"] / merged_df["ged_gedlib"]

    # Compute runtime statistics
    avg_runtime_gedlib = merged_df["runtime_gedlib"].mean()
    avg_runtime_simgnn = merged_df["runtime_simgnn"].mean()

    # Save results
    merged_df.to_csv(OUTPUT_CSV, index=False)

    print(f"Dataset: {dataset}")
    print(f"Average Approximation Error: {merged_df['approximation_error'].mean():.4f}")
    print(f"Average Relative Error: {merged_df['relative_error'].mean():.4f}")
    print(f"GEDLIB Runtime: {avg_runtime_gedlib:.4f} sec")
    print(f"SimGNN Runtime: {avg_runtime_simgnn:.4f} sec")
    print("=" * 50)


if __name__ == "__main__":
    datasets = ["AIDS", "IMDB-BINARY", "PROTEINS", "MUTAG"]
    for dataset in datasets:
        analyze_results(dataset)
