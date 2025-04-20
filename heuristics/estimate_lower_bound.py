import os
import re
import json
import time
import psutil
import networkx as nx
import pandas as pd
import numpy as np
from glob import glob
from json.decoder import JSONDecodeError

# -------------------------------
# Heuristic functions definitions
# -------------------------------

def heuristic_node_count(G1, G2):
    """Lower bound: absolute difference in number of nodes."""
    return abs(G1.number_of_nodes() - G2.number_of_nodes())

def heuristic_edge_count(G1, G2):
    """Lower bound: absolute difference in number of edges."""
    return abs(G1.number_of_edges() - G2.number_of_edges())

def heuristic_degree_distribution(G1, G2):
    """
    Lower bound based on the difference in degree distributions.
    For each degree value, we sum the absolute differences in the counts and then divide by 2.
    """
    deg_counts1 = {}
    for d in dict(G1.degree()).values():
        deg_counts1[d] = deg_counts1.get(d, 0) + 1
    deg_counts2 = {}
    for d in dict(G2.degree()).values():
        deg_counts2[d] = deg_counts2.get(d, 0) + 1

    all_degrees = set(deg_counts1.keys()).union(deg_counts2.keys())
    diff = 0
    for d in all_degrees:
        diff += abs(deg_counts1.get(d, 0) - deg_counts2.get(d, 0))
    return diff / 2

def heuristic_edge_overlap(G1, G2):
    """
    Lower bound based on edge overlap.
    For undirected graphs, each edge is treated as a frozenset.
    The heuristic computes the sum of the edges missing from each graph relative to their shared edges.
    """
    edges1 = {frozenset(e) for e in G1.edges()}
    edges2 = {frozenset(e) for e in G2.edges()}
    intersection = len(edges1.intersection(edges2))
    return (G1.number_of_edges() + G2.number_of_edges() - 2 * intersection)

def heuristic_basic_combined(G1, G2):
    """
    A simple combined heuristic that adds the node count difference and edge count difference.
    """
    return heuristic_node_count(G1, G2) + heuristic_edge_count(G1, G2)

def heuristic_node_label_mismatch(labels1, labels2):
    """
    If node label lists are available, compute a lower bound based on mismatched node labels.
    The mismatch is computed as half the sum of the absolute differences of label frequencies.
    """
    count1 = {}
    for lab in labels1:
        count1[lab] = count1.get(lab, 0) + 1

    count2 = {}
    for lab in labels2:
        count2[lab] = count2.get(lab, 0) + 1

    all_labels = set(count1.keys()).union(count2.keys())
    diff = 0
    for lab in all_labels:
        diff += abs(count1.get(lab, 0) - count2.get(lab, 0))
    return diff / 2

# -------------------------------
# JSON loading for a pair file
# -------------------------------

def load_pair_json(file_path):
    """
    Loads the JSON file for a graph pair.
    Expected keys:
       "graph_1": list of edges for first graph.
       "graph_2": list of edges for second graph.
       "labels_1" and "labels_2" (optional): list of node labels.
    Returns:
       G1, G2: NetworkX graphs for the two graphs.
       labels1, labels2: Corresponding node label lists (or None if not present).
    Raises:
       JSONDecodeError if the file cannot be parsed as valid JSON.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)

    G1 = nx.Graph()
    for edge in data.get("graph_1", []):
        if len(edge) >= 2:
            G1.add_edge(edge[0], edge[1])

    G2 = nx.Graph()
    for edge in data.get("graph_2", []):
        if len(edge) >= 2:
            G2.add_edge(edge[0], edge[1])

    labels1 = data.get("labels_1")
    labels2 = data.get("labels_2")
    return G1, G2, labels1, labels2

# -------------------------------
# Main processing function
# -------------------------------

def main():
    # Parent directory containing dataset directories.
    parent_dir = r"C:\project_data\processed_data\json_pairs"
    output_dir = r"C:\project_data\results\lower_bound\v2"
    os.makedirs(output_dir, exist_ok=True)
    max_rows = 1048574

    degree_info = {}
    performance_metrics = {}
    skipped_files = []

    for dataset_name in os.listdir(parent_dir):
        dataset_path = os.path.join(parent_dir, dataset_name)
        if not os.path.isdir(dataset_path):
            continue

        print(f"Processing dataset: {dataset_name}")
        performance_metrics[dataset_name] = {}

        heuristic_results = {
            "Node Count Difference": [],
            "Edge Count Difference": [],
            "Degree Distribution Difference": [],
            "Edge Overlap Difference": [],
            "Combined Basic (Node+Edge Count Difference)": [],
            "Node Label Mismatch": []
        }

        degrees = []

        # Start measuring overall dataset performance
        process = psutil.Process(os.getpid())
        overall_start_memory = process.memory_info().rss / 1024 / 1024
        overall_start_time = time.time()

        json_files = glob(os.path.join(dataset_path, "pair_*.json"))

        # Initialize tracking dictionaries
        heuristic_timers = {heur: 0 for heur in heuristic_results}
        heuristic_memory = {heur: 0 for heur in heuristic_results}
        heuristic_counts = {heur: 0 for heur in heuristic_results}

        # For standard deviation calculation, store individual measurements
        heuristic_runtime_values = {heur: [] for heur in heuristic_results}
        heuristic_memory_values = {heur: [] for heur in heuristic_results}

        for json_file in json_files:
            base = os.path.basename(json_file)
            match = re.match(r"pair_(\d+)_(\d+)\.json", base)
            if not match:
                continue
            id1, id2 = match.groups()

            # Load the pair data, skipping files with JSON errors
            try:
                G1, G2, labels1, labels2 = load_pair_json(json_file)
            except JSONDecodeError as e:
                skipped_files.append((json_file, str(e)))
                print(f"Skipping file with JSON error: {json_file} - {str(e)}")
                continue
            except Exception as e:
                skipped_files.append((json_file, str(e)))
                print(f"Skipping file due to error: {json_file} - {str(e)}")
                continue

            # Collect degrees for statistics
            degrees.extend(dict(G1.degree()).values())
            degrees.extend(dict(G2.degree()).values())

            # Compute Node Count Difference
            start_time = time.time()
            start_memory = process.memory_info().rss / 1024 / 1024
            h1 = heuristic_node_count(G1, G2)
            runtime = time.time() - start_time
            memory_used = process.memory_info().rss / 1024 / 1024 - start_memory

            heuristic_timers["Node Count Difference"] += runtime
            heuristic_memory["Node Count Difference"] += memory_used
            heuristic_counts["Node Count Difference"] += 1
            heuristic_runtime_values["Node Count Difference"].append(runtime)
            heuristic_memory_values["Node Count Difference"].append(memory_used)

            heuristic_results["Node Count Difference"].append({
                "Dataset": dataset_name,
                "graph_id1": id1,
                "graph_id2": id2,
                "Heuristic": "Node Count Difference",
                "Lower Bound": h1
            })

            # Compute Edge Count Difference
            start_time = time.time()
            start_memory = process.memory_info().rss / 1024 / 1024
            h2 = heuristic_edge_count(G1, G2)
            runtime = time.time() - start_time
            memory_used = process.memory_info().rss / 1024 / 1024 - start_memory

            heuristic_timers["Edge Count Difference"] += runtime
            heuristic_memory["Edge Count Difference"] += memory_used
            heuristic_counts["Edge Count Difference"] += 1
            heuristic_runtime_values["Edge Count Difference"].append(runtime)
            heuristic_memory_values["Edge Count Difference"].append(memory_used)

            heuristic_results["Edge Count Difference"].append({
                "Dataset": dataset_name,
                "graph_id1": id1,
                "graph_id2": id2,
                "Heuristic": "Edge Count Difference",
                "Lower Bound": h2
            })

            # Compute Degree Distribution Difference
            start_time = time.time()
            start_memory = process.memory_info().rss / 1024 / 1024
            h3 = heuristic_degree_distribution(G1, G2)
            runtime = time.time() - start_time
            memory_used = process.memory_info().rss / 1024 / 1024 - start_memory

            heuristic_timers["Degree Distribution Difference"] += runtime
            heuristic_memory["Degree Distribution Difference"] += memory_used
            heuristic_counts["Degree Distribution Difference"] += 1
            heuristic_runtime_values["Degree Distribution Difference"].append(runtime)
            heuristic_memory_values["Degree Distribution Difference"].append(memory_used)

            heuristic_results["Degree Distribution Difference"].append({
                "Dataset": dataset_name,
                "graph_id1": id1,
                "graph_id2": id2,
                "Heuristic": "Degree Distribution Difference",
                "Lower Bound": h3
            })

            # Compute Edge Overlap Difference
            start_time = time.time()
            start_memory = process.memory_info().rss / 1024 / 1024
            h4 = heuristic_edge_overlap(G1, G2)
            runtime = time.time() - start_time
            memory_used = process.memory_info().rss / 1024 / 1024 - start_memory

            heuristic_timers["Edge Overlap Difference"] += runtime
            heuristic_memory["Edge Overlap Difference"] += memory_used
            heuristic_counts["Edge Overlap Difference"] += 1
            heuristic_runtime_values["Edge Overlap Difference"].append(runtime)
            heuristic_memory_values["Edge Overlap Difference"].append(memory_used)

            heuristic_results["Edge Overlap Difference"].append({
                "Dataset": dataset_name,
                "graph_id1": id1,
                "graph_id2": id2,
                "Heuristic": "Edge Overlap Difference",
                "Lower Bound": h4
            })

            # Compute Combined Basic heuristic
            start_time = time.time()
            start_memory = process.memory_info().rss / 1024 / 1024
            h5 = heuristic_basic_combined(G1, G2)
            runtime = time.time() - start_time
            memory_used = process.memory_info().rss / 1024 / 1024 - start_memory

            heuristic_timers["Combined Basic (Node+Edge Count Difference)"] += runtime
            heuristic_memory["Combined Basic (Node+Edge Count Difference)"] += memory_used
            heuristic_counts["Combined Basic (Node+Edge Count Difference)"] += 1
            heuristic_runtime_values["Combined Basic (Node+Edge Count Difference)"].append(runtime)
            heuristic_memory_values["Combined Basic (Node+Edge Count Difference)"].append(memory_used)

            heuristic_results["Combined Basic (Node+Edge Count Difference)"].append({
                "Dataset": dataset_name,
                "graph_id1": id1,
                "graph_id2": id2,
                "Heuristic": "Combined Basic (Node+Edge Count Difference)",
                "Lower Bound": h5
            })

            # Optional: Only compute node label mismatch if both label lists exist
            if labels1 is not None and labels2 is not None:
                start_time = time.time()
                start_memory = process.memory_info().rss / 1024 / 1024
                h6 = heuristic_node_label_mismatch(labels1, labels2)
                runtime = time.time() - start_time
                memory_used = process.memory_info().rss / 1024 / 1024 - start_memory

                heuristic_timers["Node Label Mismatch"] += runtime
                heuristic_memory["Node Label Mismatch"] += memory_used
                heuristic_counts["Node Label Mismatch"] += 1
                heuristic_runtime_values["Node Label Mismatch"].append(runtime)
                heuristic_memory_values["Node Label Mismatch"].append(memory_used)

                heuristic_results["Node Label Mismatch"].append({
                    "Dataset": dataset_name,
                    "graph_id1": id1,
                    "graph_id2": id2,
                    "Heuristic": "Node Label Mismatch",
                    "Lower Bound": h6
                })

        # Calculate overall dataset runtime and memory usage
        overall_runtime = time.time() - overall_start_time
        overall_memory = process.memory_info().rss / 1024 / 1024 - overall_start_memory
        processed_pairs = len(json_files) - len([f for f, _ in skipped_files if dataset_name in f])

        # Store dataset performance metrics
        performance_metrics[dataset_name]["overall"] = {
            "runtime": overall_runtime,
            "memory_usage_mb": overall_memory,
            "processed_pairs": processed_pairs
        }

        # Calculate statistics per heuristic
        for heuristic in heuristic_timers:
            if heuristic_counts[heuristic] > 0:
                avg_runtime = heuristic_timers[heuristic] / heuristic_counts[heuristic]
                avg_memory = heuristic_memory[heuristic] / heuristic_counts[heuristic]

                # Calculate standard deviation
                runtime_std = np.std(heuristic_runtime_values[heuristic]) if heuristic_runtime_values[heuristic] else 0
                memory_std = np.std(heuristic_memory_values[heuristic]) if heuristic_memory_values[heuristic] else 0

                performance_metrics[dataset_name][heuristic] = {
                    "total_runtime": heuristic_timers[heuristic],
                    "avg_runtime": avg_runtime,
                    "std_runtime": runtime_std,
                    "total_memory_mb": heuristic_memory[heuristic],
                    "avg_memory_mb": avg_memory,
                    "std_memory_mb": memory_std,
                    "count": heuristic_counts[heuristic]
                }

        # Calculate and store degree information
        if degrees:
            max_degree = max(degrees)
            avg_degree = sum(degrees) / len(degrees)
            degree_info[dataset_name] = (max_degree, avg_degree)
            print(f"Dataset: {dataset_name}, Max Degree: {max_degree}, Avg Degree: {avg_degree:.2f}")

        # Print performance metrics
        print(f"Dataset: {dataset_name}, Overall Runtime: {overall_runtime:.2f}s, Memory: {overall_memory:.2f}MB")
        for heuristic, metrics in performance_metrics[dataset_name].items():
            if heuristic != "overall":
                print(f"  - {heuristic}: {metrics['avg_runtime']:.6f}s ± {metrics['std_runtime']:.6f}s, "
                      f"Memory: {metrics['avg_memory_mb']:.2f}MB ± {metrics['std_memory_mb']:.2f}MB")

        # Save results to Excel files
        for heuristic, results_list in heuristic_results.items():
            if not results_list:
                continue
            df = pd.DataFrame(results_list)
            heuristic_clean = re.sub(r'\W+', '_', heuristic).strip('_')
            n_rows = len(df)

            if n_rows > max_rows:
                num_parts = (n_rows - 1) // max_rows + 1
                for part in range(num_parts):
                    chunk = df.iloc[part * max_rows : (part + 1) * max_rows]
                    out_file = os.path.join(output_dir, f"{dataset_name}_{heuristic_clean}_part{part+1}.xlsx")
                    chunk.to_excel(out_file, index=False)
                    print(f"Saved {len(chunk)} rows to '{out_file}'.")
            else:
                out_file = os.path.join(output_dir, f"{dataset_name}_{heuristic_clean}.xlsx")
                df.to_excel(out_file, index=False)
                print(f"Saved {n_rows} rows to '{out_file}'.")

    # Save comprehensive performance metrics to Excel file
    performance_data = []
    for dataset, metrics in performance_metrics.items():
        # Overall dataset metrics
        performance_data.append({
            "Dataset": dataset,
            "Heuristic": "Overall",
            "Total Runtime (s)": metrics["overall"]["runtime"],
            "Avg Runtime (s)": metrics["overall"]["runtime"] / metrics["overall"]["processed_pairs"] if metrics["overall"]["processed_pairs"] > 0 else 0,
            "Std Runtime (s)": "N/A",  # No std for overall
            "Total Memory (MB)": metrics["overall"]["memory_usage_mb"],
            "Avg Memory (MB)": metrics["overall"]["memory_usage_mb"] / metrics["overall"]["processed_pairs"] if metrics["overall"]["processed_pairs"] > 0 else 0,
            "Std Memory (MB)": "N/A",  # No std for overall
            "Processed Pairs": metrics["overall"]["processed_pairs"]
        })

        # Per-heuristic metrics
        for heuristic, heur_metrics in metrics.items():
            if heuristic != "overall":
                performance_data.append({
                    "Dataset": dataset,
                    "Heuristic": heuristic,
                    "Total Runtime (s)": heur_metrics["total_runtime"],
                    "Avg Runtime (s)": heur_metrics["avg_runtime"],
                    "Std Runtime (s)": heur_metrics["std_runtime"],
                    "Total Memory (MB)": heur_metrics["total_memory_mb"],
                    "Avg Memory (MB)": heur_metrics["avg_memory_mb"],
                    "Std Memory (MB)": heur_metrics["std_memory_mb"],
                    "Processed Pairs": heur_metrics["count"]
                })

    # Save performance metrics
    perf_df = pd.DataFrame(performance_data)
    perf_file = os.path.join(output_dir, "performance_metrics.xlsx")
    perf_df.to_excel(perf_file, index=False)
    print(f"Performance metrics saved to {perf_file}")

    # Print degree information summary
    print("\n--- Degree Information for All Datasets ---")
    for dataset_name, (max_degree, avg_degree) in degree_info.items():
        print(f"Dataset: {dataset_name}, Max Degree: {max_degree}, Avg Degree: {avg_degree:.2f}")

    # Report skipped files
    if skipped_files:
        print(f"\n--- Skipped {len(skipped_files)} files due to parsing errors ---")
        skipped_log_path = os.path.join(output_dir, "skipped_files.txt")
        with open(skipped_log_path, 'w') as f:
            for file_path, error in skipped_files:
                f.write(f"{file_path}: {error}\n")
        print(f"List of skipped files saved to {skipped_log_path}")

if __name__ == "__main__":
    main()