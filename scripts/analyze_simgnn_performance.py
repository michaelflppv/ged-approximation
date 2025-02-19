#!/usr/bin/env python3
"""
analyze_simgnn_performance.py

This script analyzes the synthesized performance data of the SimGNN algorithm.
The input Excel file should contain the following columns:
  - File (each JSON file name for a graph pair)
  - Predicted GED (predicted graph edit distance)
  - Ground Truth GED (ground truth graph edit distance)
  - Absolute Error
  - Squared Error
  - Graph1 Nodes, Graph2 Nodes (number of nodes in each graph)
  - Graph1 Density, Graph2 Density (density of each graph)
  - Runtime (s) (runtime per pair)
  - Memory Usage (MB) (memory usage per pair)

The script performs:
  Step 5: Data Analysis and Interpretation:
     - Identifies patterns/trends, trade-offs, and potential outliers.
     - Compares observed trends against expected hypotheses.
     - Conducts error analysis.

  Step 6: Statistical Validation:
     - Performs paired t-test and Wilcoxon signed-rank test comparing predicted vs. ground truth GED.
     - Computes 95% confidence intervals (e.g., for Absolute Error).

  Step 8: Derives actionable insights on accuracy, efficiency, robustness, scalability, and trade-offs.

The final report is printed to the console and also saved as a text file.
"""

import os
import pandas as pd
import numpy as np
import scipy.stats as stats


def load_data(excel_path):
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found at {excel_path}")
    df = pd.read_excel(excel_path)
    return df


def descriptive_statistics(df):
    stats_dict = {}
    metrics = ["Predicted GED", "Ground Truth GED", "Absolute Error", "Squared Error",
               "Graph1 Nodes", "Graph2 Nodes", "Graph1 Density", "Graph2 Density",
               "Runtime (s)", "Memory Usage (MB)"]
    for metric in metrics:
        if metric in df.columns:
            stats_dict[metric] = {
                "mean": df[metric].mean(),
                "median": df[metric].median(),
                "std": df[metric].std(),
                "min": df[metric].min(),
                "max": df[metric].max()
            }
    return stats_dict


def correlation_analysis(df):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    corr_matrix = df[numeric_cols].corr()
    return corr_matrix


def perform_paired_tests(df):
    results = {}
    if "Predicted GED" in df.columns and "Ground Truth GED" in df.columns:
        # Paired t-test
        t_stat, p_val = stats.ttest_rel(df["Predicted GED"], df["Ground Truth GED"])
        results["paired_t_test"] = {"t_stat": t_stat, "p_value": p_val}
        # Wilcoxon signed-rank test (non-parametric)
        try:
            w_stat, p_val_w = stats.wilcoxon(df["Predicted GED"], df["Ground Truth GED"])
            results["wilcoxon"] = {"w_stat": w_stat, "p_value": p_val_w}
        except Exception as e:
            results["wilcoxon"] = {"error": str(e)}
    return results


def compute_confidence_interval(data, confidence=0.95):
    data = np.array(data)
    mean_val = np.mean(data)
    std_error = stats.sem(data)
    df_deg = len(data) - 1
    t_critical = stats.t.ppf((1 + confidence) / 2, df_deg)
    margin_error = t_critical * std_error
    return mean_val - margin_error, mean_val + margin_error


def confidence_intervals(df):
    ci_dict = {}
    if "Absolute Error" in df.columns:
        ci = compute_confidence_interval(df["Absolute Error"].dropna())
        ci_dict["Absolute Error (95% CI)"] = ci
    # More confidence intervals could be computed similarly.
    return ci_dict


def identify_outliers(df, metric, threshold=1.5):
    if metric not in df.columns:
        return None
    Q1 = df[metric].quantile(0.25)
    Q3 = df[metric].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - threshold * IQR
    upper_bound = Q3 + threshold * IQR
    outliers = df[(df[metric] < lower_bound) | (df[metric] > upper_bound)]
    return outliers


def derive_insights(df, stats_dict, corr_matrix, test_results, ci_dict):
    insights = []
    # 1. Accuracy and Approximation Quality
    if "Absolute Error" in stats_dict:
        mean_abs_error = stats_dict["Absolute Error"]["mean"]
        insights.append(f"Average Absolute Error: {mean_abs_error:.2f}. Lower values indicate higher accuracy.")
    if "Predicted GED" in stats_dict and "Ground Truth GED" in stats_dict:
        mean_pred = stats_dict["Predicted GED"]["mean"]
        mean_gt = stats_dict["Ground Truth GED"]["mean"]
        insights.append(f"Average Predicted GED: {mean_pred:.2f} vs. Ground Truth GED: {mean_gt:.2f}.")
        corr_pred_gt = corr_matrix.loc["Predicted GED", "Ground Truth GED"]
        if abs(corr_pred_gt) > 0.7:
            insights.append(
                f"Strong linear relationship between predicted and ground truth GED (corr = {corr_pred_gt:.2f}).")
        else:
            insights.append(f"Weak correlation (corr = {corr_pred_gt:.2f}); the approximation may be inconsistent.")
    # 2. Trade-offs between runtime and accuracy.
    if "Runtime (s)" in stats_dict and "Absolute Error" in stats_dict:
        insights.append(
            "Examination of runtime vs. absolute error indicates whether longer runtimes yield significantly lower errors.")
    # 3. Effect of graph size/density.
    if "Graph1 Nodes" in stats_dict and "Graph2 Nodes" in stats_dict:
        insights.append("Graph sizes vary considerably; check if larger graphs lead to higher errors.")
    if "Graph1 Density" in stats_dict and "Graph2 Density" in stats_dict:
        insights.append("Variations in graph density may influence the GED approximation accuracy.")
    # 4. Statistical significance testing.
    if "paired_t_test" in test_results:
        p_val = test_results["paired_t_test"]["p_value"]
        if p_val < 0.05:
            insights.append(
                f"Paired t-test shows significant differences (p = {p_val:.4f}) between predicted and ground truth GED.")
        else:
            insights.append(f"Paired t-test indicates no significant difference (p = {p_val:.4f}).")
    # 5. Confidence intervals.
    if "Absolute Error (95% CI)" in ci_dict:
        ci_lower, ci_upper = ci_dict["Absolute Error (95% CI)"]
        insights.append(f"95% Confidence Interval for Absolute Error: ({ci_lower:.2f}, {ci_upper:.2f}).")
    # 6. Outlier analysis.
    outliers = identify_outliers(df, "Absolute Error")
    if outliers is not None and not outliers.empty:
        insights.append(
            f"There are {len(outliers)} outlier pairs in terms of absolute error; these require further investigation.")
    else:
        insights.append("No significant outliers in absolute error were detected.")
    return insights


def main():
    # Define the Excel file path (adjust relative path as needed)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = "../results/neural/PROTEINS/performance.xlsx"

    # Load the data.
    try:
        df = load_data(excel_path)
    except FileNotFoundError as e:
        print(e)
        return

    # Step 5: Analyze and Interpret the Data.
    stats_dict = descriptive_statistics(df)
    corr_matrix = correlation_analysis(df)
    test_results = perform_paired_tests(df)
    ci_dict = confidence_intervals(df)

    insights = derive_insights(df, stats_dict, corr_matrix, test_results, ci_dict)

    # Print a summary report.
    print("=== SimGNN Performance Analysis Report ===\n")
    print("Descriptive Statistics:")
    for metric, s in stats_dict.items():
        print(f"  {metric}: mean = {s['mean']:.2f}, median = {s['median']:.2f}, std = {s['std']:.2f}")
    print("\nCorrelation Matrix:")
    print(corr_matrix)
    print("\nStatistical Test Results:")
    for test, result in test_results.items():
        print(f"  {test}: {result}")
    print("\nConfidence Intervals:")
    for ci, value in ci_dict.items():
        print(f"  {ci}: ({value[0]:.2f}, {value[1]:.2f})")
    print("\nActionable Insights:")
    for insight in insights:
        print(" -", insight)

    # Save the report to a text file.
    report_path = "../results/analysis/SimGNN/PROTEINS/SimGNN_analysis_report.txt"
    with open(report_path, "w") as f:
        f.write("=== SimGNN Performance Analysis Report ===\n\n")
        f.write("Descriptive Statistics:\n")
        for metric, s in stats_dict.items():
            f.write(f"  {metric}: mean = {s['mean']:.2f}, median = {s['median']:.2f}, std = {s['std']:.2f}\n")
        f.write("\nCorrelation Matrix:\n")
        f.write(corr_matrix.to_string())
        f.write("\n\nStatistical Test Results:\n")
        for test, result in test_results.items():
            f.write(f"  {test}: {result}\n")
        f.write("\nConfidence Intervals:\n")
        for ci, value in ci_dict.items():
            f.write(f"  {ci}: ({value[0]:.2f}, {value[1]:.2f})\n")
        f.write("\nActionable Insights:\n")
        for insight in insights:
            f.write(" - " + insight + "\n")

    print(f"\nAnalysis report saved to {report_path}")


if __name__ == "__main__":
    main()
