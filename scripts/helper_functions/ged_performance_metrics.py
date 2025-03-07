#!/usr/bin/env python3
import argparse
import pandas as pd
import numpy as np


def compute_relative_accuracy(ged_approx, ged_exact):
    """
    Compute relative accuracy (GED approximation error) as:
      (ged_approx - ged_exact) / ged_exact.
    If ged_exact is zero, return 0 if both are zero; otherwise, return infinity.
    """
    if ged_exact == 0:
        return 0.0 if ged_approx == 0 else float('inf')
    return (ged_approx - ged_exact) / ged_exact


def compute_scalability(graph_sizes, runtimes, memory_usages):
    """
    Compute scalability as the change in runtime and memory usage per unit increase in graph size.
    Returns a tuple (slope_runtime, slope_memory).

    Uses a simple linear regression (via numpy.polyfit).
    """
    graph_sizes = np.array(graph_sizes, dtype=float)
    runtimes = np.array(runtimes, dtype=float)
    memory_usages = np.array(memory_usages, dtype=float)

    slope_runtime, _ = np.polyfit(graph_sizes, runtimes, 1)
    slope_memory, _ = np.polyfit(graph_sizes, memory_usages, 1)
    return slope_runtime, slope_memory


def mean_absolute_error(approx_values, exact_values):
    """
    Compute the Mean Absolute Error (MAE) between lists/arrays of approx_values and exact_values.
    """
    approx_values = np.array(approx_values, dtype=float)
    exact_values = np.array(exact_values, dtype=float)
    errors = np.abs(approx_values - exact_values)
    return np.mean(errors)


def mean_squared_error(approx_values, exact_values):
    """
    Compute the Mean Squared Error (MSE) between lists/arrays of approx_values and exact_values.
    """
    approx_values = np.array(approx_values, dtype=float)
    exact_values = np.array(exact_values, dtype=float)
    errors = (approx_values - exact_values) ** 2
    return np.mean(errors)


def merge_data(approx_df, exact_df):
    """
    Merge the approximation and exact GED DataFrames on 'graph_id_1' and 'graph_id_2'.
    """
    merged_df = pd.merge(approx_df, exact_df, on=["graph_id_1", "graph_id_2"], how="inner")
    return merged_df


def compute_metrics(merged_df):
    """
    Compute all performance metrics and append them as new columns to the merged DataFrame.

    Expected columns:
      - 'GED_approx': approximate GED value.
      - 'GED_exact': exact GED value.
      - 'runtime': runtime for the approximation algorithm.
      - 'memory_usage': memory usage for the approximation algorithm.
      - 'graph_size': a numeric measure of graph size (used for scalability).

    New columns appended (or overwritten) are:
      - 'relative_accuracy' (rowwise)
      - 'MAE' and 'MSE' (global, same value for every row)
      - 'scalability_runtime' and 'scalability_memory' (global slopes, same for every row)
    """
    # Compute relative accuracy for each row.
    merged_df["relative_accuracy"] = merged_df.apply(
        lambda row: compute_relative_accuracy(row["GED_approx"], row["GED_exact"]), axis=1
    )

    # Compute global MAE and MSE.
    mae = mean_absolute_error(merged_df["GED_approx"], merged_df["GED_exact"])
    mse = mean_squared_error(merged_df["GED_approx"], merged_df["GED_exact"])
    merged_df["MAE"] = mae
    merged_df["MSE"] = mse

    # Compute scalability if required columns are available.
    if all(col in merged_df.columns for col in ["graph_size", "runtime", "memory_usage"]):
        slope_runtime, slope_memory = compute_scalability(merged_df["graph_size"], merged_df["runtime"],
                                                          merged_df["memory_usage"])
        merged_df["scalability_runtime"] = slope_runtime
        merged_df["scalability_memory"] = slope_memory
    else:
        print(
            "Warning: 'graph_size', 'runtime', and/or 'memory_usage' columns not found. Skipping scalability metrics.")

    return merged_df


def main(approx_excel, exact_excel, output_excel):
    """
    Main function to compute performance metrics.

    Reads the approximation performance Excel file and the exact GED Excel file,
    merges them, computes metrics, and writes the updated DataFrame to output_excel.
    """
    # Read the Excel files.
    approx_df = pd.read_excel(approx_excel)
    exact_df = pd.read_excel(exact_excel)

    # Merge data on 'graph_id_1' and 'graph_id_2'.
    merged_df = merge_data(approx_df, exact_df)

    # Compute all performance metrics.
    merged_df = compute_metrics(merged_df)

    # Save the updated DataFrame to the output Excel file.
    merged_df.to_excel(output_excel, index=False)
    print(f"Updated performance metrics saved to {output_excel}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute GED performance metrics and append them as new columns to the approximation Excel file."
    )
    parser.add_argument("approx_excel", help="Path to the Excel file with performance of the approximation algorithm")
    parser.add_argument("exact_excel", help="Path to the Excel file with exact GED values")
    parser.add_argument("output_excel", help="Path to the output Excel file where updated data should be saved")
    args = parser.parse_args()
    main(args.approx_excel, args.exact_excel, args.output_excel)
