#!/usr/bin/env python

import os
import pandas as pd


def main():
    # Define paths to the input summary Excel files.
    gedlib_summary_path = r"C:\Users\mikef\PycharmProjects\ged-approximation\results\gedlib\PROTEINS_results.xlsx"
    simgnn_summary_path = r"C:\Users\mikef\PycharmProjects\ged-approximation\results\neural\PROTEINS\performance.xlsx"

    # Define output directory and file.
    relative_results_dir = r"C:\Users\mikef\PycharmProjects\ged-approximation\results\relative_performance"
    os.makedirs(relative_results_dir, exist_ok=True)
    relative_results_file = os.path.join(relative_results_dir, "PROTEINS_relative_performance.xlsx")

    # Load summary sheets.
    # GEDLIB summary sheet is assumed to have columns:
    # "Total Graph Pairs", "Average MSE", "Average MAE", "Total Runtime (s)", "Average Memory Usage (MB)", "Maximum Graph Size"
    df_gedlib = pd.read_excel(gedlib_summary_path, sheet_name="Summary")

    # SimGNN summary sheet is assumed to have columns (or similar):
    # "Total graph pairs processed", "Average MSE", "Average MAE", "Total runtime (s)", "Memory usage (MB)", "Maximum graph size processed (number of nodes)"
    df_simgnn = pd.read_excel(simgnn_summary_path, sheet_name="Summary")

    # Extract values from GEDLIB summary.
    total_pairs_gedlib = df_gedlib.iloc[0]["Total Graph Pairs"]
    avg_mse_gedlib = df_gedlib.iloc[0]["Average MSE"]
    avg_mae_gedlib = df_gedlib.iloc[0]["Average MAE"]
    total_runtime_gedlib = df_gedlib.iloc[0]["Total Runtime (s)"]
    avg_mem_gedlib = df_gedlib.iloc[0]["Average Memory Usage (MB)"]
    max_graph_size_gedlib = df_gedlib.iloc[0]["Maximum Graph Size"]

    # Extract values from SimGNN summary.
    # Depending on the exact column names, we try a couple of alternatives.
    total_pairs_simgnn = df_simgnn.iloc[0].get("Total graph pairs processed",
                                               df_simgnn.iloc[0].get("Total Graph Pairs"))
    avg_mse_simgnn = df_simgnn.iloc[0]["Average MSE"]
    avg_mae_simgnn = df_simgnn.iloc[0]["Average MAE"]
    total_runtime_simgnn = df_simgnn.iloc[0].get("Total runtime (s)", df_simgnn.iloc[0].get("Total Runtime (s)"))
    avg_mem_simgnn = df_simgnn.iloc[0].get("Memory usage (MB)", df_simgnn.iloc[0].get("Memory Usage (MB)"))
    max_graph_size_simgnn = df_simgnn.iloc[0].get("Maximum graph size processed (number of nodes)",
                                                  df_simgnn.iloc[0].get("Maximum Graph Size"))

    # Compute relative improvements for error metrics.
    # For error metrics, a lower value is better so we compute:
    #   Relative improvement (%) = (GEDLIB_error - SimGNN_error) / GEDLIB_error * 100
    mse_improvement = ((avg_mse_gedlib - avg_mse_simgnn) / avg_mse_gedlib * 100) if avg_mse_gedlib else None
    mae_improvement = ((avg_mae_gedlib - avg_mae_simgnn) / avg_mae_gedlib * 100) if avg_mae_gedlib else None

    # For runtime and memory usage, we compute the ratio (SimGNN value relative to GEDLIB).
    runtime_ratio = (total_runtime_simgnn / total_runtime_gedlib * 100) if total_runtime_gedlib else None
    memory_ratio = (avg_mem_simgnn / avg_mem_gedlib * 100) if avg_mem_gedlib else None

    # Build a summary DataFrame with the relative metrics.
    summary_data = {
        "Metric": [
            "Total Graph Pairs",
            "Average MSE",
            "Average MAE",
            "Total Runtime (s)",
            "Average Memory Usage (MB)",
            "Maximum Graph Size"
        ],
        "GEDLIB": [
            total_pairs_gedlib,
            avg_mse_gedlib,
            avg_mae_gedlib,
            total_runtime_gedlib,
            avg_mem_gedlib,
            max_graph_size_gedlib
        ],
        "SimGNN": [
            total_pairs_simgnn,
            avg_mse_simgnn,
            avg_mae_simgnn,
            total_runtime_simgnn,
            avg_mem_simgnn,
            max_graph_size_simgnn
        ],
        "Relative Difference (%)": [
            None,  # For total pairs, relative difference may not be meaningful.
            mse_improvement,
            mae_improvement,
            runtime_ratio,
            memory_ratio,
            None  # Maximum graph size is determined by the dataset.
        ]
    }
    df_relative = pd.DataFrame(summary_data)

    # (Optional) Additional performance metrics could be computed here, e.g.:
    #   - Outlier detection in per-pair errors
    #   - Correlation between runtime and graph size
    #   - Standard deviation of errors, etc.

    # Save the relative performance summary to an Excel file.
    with pd.ExcelWriter(relative_results_file, engine='openpyxl') as writer:
        df_relative.to_excel(writer, sheet_name="Relative Summary", index=False)

    print("Analysis completed. Relative performance results saved in:")
    print(relative_results_file)


if __name__ == "__main__":
    main()
