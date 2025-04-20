#!/usr/bin/env python3
"""
analyze_results.py

This script performs a comprehensive statistical analysis on the synthesized performance data
of multiple GED approximation algorithms. The input Excel file should contain the following columns:
  - method                : Name of the approximation algorithm.
  - ged                   : Approximated graph edit distance.
  - runtime               : Duration of approximation (seconds).
  - graph1, graph2        : Graph IDs in a pair.
  - memory_usage_mb       : Memory usage in MB.
  - graph1_n, graph2_n    : Number of nodes in graph1 and graph2.
  - graph1_density, graph2_density : Density of graph1 and graph2.
  - average_n             : Average number of nodes (or maximum nodes among the two).
  - average_density       : Average density of the two graphs.
  - scalability           : The maximum number of nodes in any graph processed.

The script accomplishes the following:
  1. Analyze and interpret the data:
       - Compute overall and per-method descriptive statistics.
       - Identify patterns/trends and potential outliers.
       - Compare performance metrics across methods.
  2. Perform statistical validation:
       - One-way ANOVA (and pairwise tests, if desired) to test for differences in GED among methods.
       - Compute 95% confidence intervals for selected metrics.
  3. Derive actionable insights.

All results are printed to the console and saved into an Excel file with multiple sheets.
"""

import os
import pandas as pd
import numpy as np
import scipy.stats as stats
import seaborn as sns
import matplotlib.pyplot as plt
from pandas.plotting import parallel_coordinates

# Set Power BI-like style
sns.set_style("whitegrid")
sns.set_palette(["#B19CD9", "#7D6EA7", "#E6E6FA", "#9370DB", "#CBAACB"])  # Lavender tones

# Define figure size and DPI for 4K resolution
figsize = (32, 18)
dpi = 300


def load_data(excel_path):
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found at {excel_path}")
    df = pd.read_excel(excel_path)
    return df


def descriptive_statistics(df):
    metrics = ["ged", "runtime", "memory_usage_mb", "graph1_n", "graph2_n",
               "graph1_density", "graph2_density", "average_n", "average_density", "scalability"]
    desc = df[metrics].describe().T
    return desc


def group_by_method_stats(df):
    # Group by the 'method' column and compute descriptive stats for each numeric metric.
    grouped = df.groupby("method").describe()
    return grouped


def correlation_analysis(df):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    corr_matrix = df[numeric_cols].corr()
    return corr_matrix


def perform_anova(df):
    # Perform a one-way ANOVA test on the 'ged' values across methods.
    groups = [group["ged"].dropna().values for name, group in df.groupby("method")]
    if len(groups) > 1:
        f_stat, p_val = stats.f_oneway(*groups)
        return {"F-statistic": f_stat, "p_value": p_val}
    else:
        return {"F-statistic": None, "p_value": None}


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
    for metric in ["ged", "runtime", "memory_usage_mb"]:
        if metric in df.columns:
            data = df[metric].dropna()
            if len(data) > 1:
                ci_dict[metric] = compute_confidence_interval(data)
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


def derive_insights(df, desc_stats, corr_matrix, anova_results, ci_dict):
    insights = []
    # 1. Accuracy and Approximation Quality (ged)
    mean_ged = desc_stats.loc["ged", "mean"]
    insights.append(f"Overall average approximated GED is {mean_ged:.2f}.")
    # 2. Runtime and Efficiency
    mean_runtime = desc_stats.loc["runtime", "mean"]
    insights.append(f"Overall average runtime is {mean_runtime:.2f} seconds.")
    # 3. Memory Usage
    mean_memory = desc_stats.loc["memory_usage_mb", "mean"]
    insights.append(f"Average memory usage per pair is {mean_memory:.2f} MB.")
    # 4. Correlation insights
    if "ged" in corr_matrix.index and "runtime" in corr_matrix.columns:
        corr_ged_runtime = corr_matrix.loc["ged", "runtime"]
        insights.append(f"Correlation between GED and runtime is {corr_ged_runtime:.2f}.")
    # 5. ANOVA on GED across methods
    if anova_results["p_value"] is not None:
        if anova_results["p_value"] < 0.05:
            insights.append("There is a statistically significant difference in GED across methods (ANOVA p < 0.05).")
        else:
            insights.append(
                "No statistically significant difference in GED was observed across methods (ANOVA p >= 0.05).")
    # 6. Confidence intervals
    for metric, ci in ci_dict.items():
        insights.append(f"95% CI for {metric}: ({ci[0]:.2f}, {ci[1]:.2f}).")
    # 7. Outlier detection (for runtime)
    outliers_runtime = identify_outliers(df, "runtime")
    if outliers_runtime is not None and not outliers_runtime.empty:
        insights.append(
            f"Found {len(outliers_runtime)} outlier pairs in runtime. Investigate these for potential algorithmic bottlenecks.")
    else:
        insights.append("No significant outliers detected in runtime.")
    # 8. Scalability
    avg_scalability = desc_stats.loc["scalability", "mean"]
    insights.append(
        f"On average, the maximum graph size processed is {avg_scalability:.0f} nodes, indicating scalability limits.")
    return insights


def save_plots(df, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    # -------- Group 1: Performance Evaluation --------
    ## 1.1 Runtime vs. Approximation Quality (Scatter with regression)
    ax = sns.lmplot(data=df, x="runtime", y="ged", hue="method", height=12, aspect=2,
                    scatter_kws={'s': 100, 'alpha': 0.7})
    plt.xscale("log")
    plt.title("Runtime vs. Approximation Quality", fontsize=24, fontweight="bold")
    plt.xlabel("Runtime (s) [log-scale]", fontsize=18)
    plt.ylabel("Approximated GED", fontsize=18)
    plt.savefig(os.path.join(output_folder, "runtime_vs_ged.png"), dpi=300)
    plt.close("all")

    ## 1.2 Runtime vs. Memory Usage (Bubble Plot)
    plt.figure(figsize=(32, 18), dpi=300)
    ax = sns.scatterplot(data=df, x="runtime", y="memory_usage_mb", hue="method", size="average_n", sizes=(50, 400),
                         alpha=0.7, edgecolor="white", linewidth=1.5)
    plt.xscale("log")
    plt.title("Runtime vs. Memory Usage", fontsize=24, fontweight="bold")
    plt.xlabel("Runtime (s) [log-scale]", fontsize=18)
    plt.ylabel("Memory Usage (MB)", fontsize=18)
    plt.savefig(os.path.join(output_folder, "runtime_vs_memory.png"), dpi=300)
    plt.close()

    ## 1.3 Memory Usage vs. Number of Nodes (Violin Plot)
    plt.figure(figsize=(32, 18), dpi=300)
    sns.violinplot(data=df, x="method", y="memory_usage_mb", inner="box", linewidth=2)
    plt.title("Memory Usage vs. Method", fontsize=24, fontweight="bold")
    plt.xlabel("Method", fontsize=18)
    plt.ylabel("Memory Usage (MB)", fontsize=18)
    plt.savefig(os.path.join(output_folder, "memory_vs_method.png"), dpi=300)
    plt.close()

    # -------- Group 2: Scalability Analysis --------
    ## 2.1 Scalability vs. Runtime (Scatter with trend line)
    ax = sns.lmplot(data=df, x="scalability", y="runtime", hue="method", height=12, aspect=2,
                    scatter_kws={'s': 100, 'alpha': 0.7})
    plt.title("Scalability vs. Runtime", fontsize=24, fontweight="bold")
    plt.xlabel("Scalability (max nodes)", fontsize=18)
    plt.ylabel("Runtime (s)", fontsize=18)
    plt.savefig(os.path.join(output_folder, "scalability_vs_runtime.png"), dpi=300)
    plt.close("all")

    ## 2.2 Scalability vs. Approximation Quality (Scatter with trend line)
    ax = sns.lmplot(data=df, x="scalability", y="ged", hue="method", height=12, aspect=2,
                    scatter_kws={'s': 100, 'alpha': 0.7})
    plt.title("Scalability vs. Approximated GED", fontsize=24, fontweight="bold")
    plt.xlabel("Scalability (max nodes)", fontsize=18)
    plt.ylabel("Approximated GED", fontsize=18)
    plt.savefig(os.path.join(output_folder, "scalability_vs_ged.png"), dpi=300)
    plt.close("all")

    ## 2.3 Scalability vs. Memory Usage (Line Plot)
    sorted_df = df.sort_values("scalability")
    plt.figure(figsize=(32, 18), dpi=300)
    sns.lineplot(data=sorted_df, x="scalability", y="memory_usage_mb", hue="method", style="method", markers=True,
                 linewidth=2)
    plt.title("Scalability vs. Memory Usage", fontsize=24, fontweight="bold")
    plt.xlabel("Scalability (max nodes)", fontsize=18)
    plt.ylabel("Memory Usage (MB)", fontsize=18)
    plt.savefig(os.path.join(output_folder, "scalability_vs_memory.png"), dpi=300)
    plt.close()

    # -------- Group 3: Approximation Quality and Accuracy --------
    ## 3.1 GED vs. Average Node Count (Scatter Plot)
    plt.figure(figsize=(32, 18), dpi=300)
    sns.scatterplot(data=df, x="average_n", y="ged", hue="method", s=100, alpha=0.7, edgecolor="white", linewidth=1.5)
    plt.title("GED vs. Average Number of Nodes", fontsize=24, fontweight="bold")
    plt.xlabel("Average Number of Nodes", fontsize=18)
    plt.ylabel("Approximated GED", fontsize=18)
    plt.savefig(os.path.join(output_folder, "ged_vs_avg_nodes.png"), dpi=300)
    plt.close()

    ## 3.2 GED vs. Graph Density (Scatter with regression)
    ax = sns.lmplot(data=df, x="average_density", y="ged", hue="method", height=12, aspect=2,
                    scatter_kws={'s': 100, 'alpha': 0.7})
    plt.title("GED vs. Average Graph Density", fontsize=24, fontweight="bold")
    plt.xlabel("Average Graph Density", fontsize=18)
    plt.ylabel("Approximated GED", fontsize=18)
    plt.savefig(os.path.join(output_folder, "ged_vs_avg_density.png"), dpi=300)
    plt.close("all")

    # -------- Group 4: Correlation and Comparative Insights --------
    ## 4.1 Correlation Matrix (Heatmap)
    selected_vars = ["runtime", "ged", "memory_usage_mb", "average_n", "scalability"]
    corr = df[selected_vars].corr()
    plt.figure(figsize=(32, 18), dpi=300)
    sns.heatmap(corr, annot=True, cmap="Purples", fmt=".2f", square=True, linewidths=1, linecolor="white")
    plt.title("Correlation Matrix", fontsize=24, fontweight="bold")
    plt.savefig(os.path.join(output_folder, "correlation_heatmap.png"), dpi=300)
    plt.close()

    ## 4.2 Distribution of GED Across Methods (Violin Plot)
    plt.figure(figsize=(32, 18), dpi=300)
    sns.violinplot(data=df, x="method", y="ged", inner="box", linewidth=2)
    plt.title("Distribution of GED Across Methods", fontsize=24, fontweight="bold")
    plt.xlabel("Method", fontsize=18)
    plt.ylabel("Approximated GED", fontsize=18)
    plt.savefig(os.path.join(output_folder, "ged_distribution.png"), dpi=300)
    plt.close()

    ## 4.3 Parallel Coordinates Plot (Multidimensional Analysis)
    pc_df = df[["method", "runtime", "ged", "memory_usage_mb", "scalability"]].copy()
    for col in ["runtime", "ged", "memory_usage_mb", "scalability"]:
        pc_df[col] = (pc_df[col] - pc_df[col].min()) / (pc_df[col].max() - pc_df[col].min())

    plt.figure(figsize=(32, 18), dpi=300)
    parallel_coordinates(pc_df, "method", colormap=plt.get_cmap("Purples"))
    plt.title("Parallel Coordinates Plot", fontsize=24, fontweight="bold")
    plt.xlabel("Metrics", fontsize=18)
    plt.ylabel("Normalized Value", fontsize=18)
    plt.savefig(os.path.join(output_folder, "parallel_coordinates.png"), dpi=300)
    plt.close()

    print("All plots saved in:", output_folder)


def main():
    # Define the path to the Excel file containing algorithm performance data.
    excel_path = "../../results/gedlib/PROTEINS/PROTEINS_HED_results.xlsx"

    try:
        df = load_data(excel_path)
    except FileNotFoundError as e:
        print(e)
        return

    # Compute overall descriptive statistics.
    desc_stats = descriptive_statistics(df)

    # Compute per-method descriptive statistics.
    grouped_stats = group_by_method_stats(df)

    # Compute the overall correlation matrix.
    corr_matrix = correlation_analysis(df)

    # Perform a one-way ANOVA test on the "ged" values across methods.
    anova_results = perform_anova(df)

    # Compute 95% confidence intervals for selected metrics.
    ci_dict = confidence_intervals(df)

    # Derive actionable insights.
    insights = derive_insights(df, desc_stats, corr_matrix, anova_results, ci_dict)

    # Save plots into a folder.
    plots_folder = "../results/analysis/HED/PROTEINS/plots"
    save_plots(df, plots_folder)

    # Compile results into a report DataFrame (for descriptive stats and tests).
    report_lines = []
    report_lines.append("=== Overall Descriptive Statistics ===")
    report_lines.append(desc_stats.to_string())
    report_lines.append("\n=== Per-Method Descriptive Statistics ===")
    report_lines.append(grouped_stats.to_string())
    report_lines.append("\n=== Correlation Matrix ===")
    report_lines.append(corr_matrix.to_string())
    report_lines.append("\n=== ANOVA Results (GED across methods) ===")
    report_lines.append(str(anova_results))
    report_lines.append("\n=== Confidence Intervals ===")
    for metric, ci in ci_dict.items():
        report_lines.append(f"{metric}: ({ci[0]:.2f}, {ci[1]:.2f})")
    report_lines.append("\n=== Actionable Insights ===")
    for ins in insights:
        report_lines.append(" - " + ins)

    report_text = "\n".join(report_lines)
    print(report_text)

    # Save the report into an Excel file with multiple sheets.
    writer_path = "../../results/analysis/HED/PROTEINS/algorithm_performance_analysis.xlsx"
    with pd.ExcelWriter(writer_path, engine="openpyxl") as writer:
        desc_stats.to_excel(writer, sheet_name="Overall_Stats")
        grouped_stats.to_excel(writer, sheet_name="Per_Method_Stats")
        corr_matrix.to_excel(writer, sheet_name="Correlation")
        # Also write a sheet for ANOVA, Confidence Intervals, and Insights.
        extra_df = pd.DataFrame({
            "Metric": list(ci_dict.keys()) + ["ANOVA_F", "ANOVA_p"],
            "Value": [f"({ci[0]:.2f}, {ci[1]:.2f})" for ci in ci_dict.values()] +
                     [anova_results.get("F-statistic", "N/A"), anova_results.get("p_value", "N/A")]
        })
        extra_df.to_excel(writer, sheet_name="Statistical_Tests", index=False)
        insights_df = pd.DataFrame({"Insight": insights})
        insights_df.to_excel(writer, sheet_name="Insights", index=False)

    print(f"Analysis report saved to {writer_path}")


if __name__ == "__main__":
    main()
