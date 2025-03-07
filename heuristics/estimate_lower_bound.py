#!/usr/bin/env python3
"""
This script processes graph pair JSON files from multiple dataset directories.
Each dataset directory is named after the dataset and contains JSON files named
"pair_id1_id2.json" (where id1 and id2 identify the graphs in the pair).

Each JSON file is expected to have the structure:
{
  "graph_1": [[node1, node2], [node3, node4], ...],
  "graph_2": [[...], ...],
  "labels_1": [<label for node1>, <label for node2>, ...],    # optional
  "labels_2": [<...>],                                         # optional
  "ged": <optional ground truth value>
}

For every pair, the script builds a NetworkX graph from the edge list and computes
the following lower bound heuristics:
  1. Node Count Difference
  2. Edge Count Difference
  3. Degree Distribution Difference
  4. Edge Overlap Difference
  5. Combined Basic (Node+Edge Count Difference)
  6. (Optional) Node Label Mismatch – if label lists are available

The results (including dataset name, graph_id1, graph_id2, heuristic type, and the computed lower bound)
are saved to separate Excel files per dataset and per heuristic.
Each Excel file will not exceed 1,048,574 rows – if more rows are present, additional files will be produced.
"""

import os
import re
import json
import networkx as nx
import pandas as pd
from glob import glob

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
    parent_dir = "/home/mfilippov/ged_data/processed_data/json_pairs"  # Change as needed.
    # Directory to save the results Excel files.
    output_dir = "/home/mfilippov/ged_data/results/lower_bound"
    os.makedirs(output_dir, exist_ok=True)

    # Maximum number of rows per Excel file.
    max_rows = 1048574

    # Dictionary to store degree information for each dataset.
    degree_info = {}

    # Iterate over each dataset directory.
    for dataset_name in os.listdir(parent_dir):
        dataset_path = os.path.join(parent_dir, dataset_name)
        if not os.path.isdir(dataset_path):
            continue

        print(f"Processing dataset: {dataset_name}")

        # Initialize dictionaries to accumulate results for each heuristic.
        heuristic_results = {
            "Node Count Difference": [],
            "Edge Count Difference": [],
            "Degree Distribution Difference": [],
            "Edge Overlap Difference": [],
            "Combined Basic (Node+Edge Count Difference)": [],
            "Node Label Mismatch": []  # Will only be populated if labels exist.
        }
        degrees = []

        # Find all JSON files in the current dataset directory matching "pair_*.json"
        json_files = glob(os.path.join(dataset_path, "pair_*.json"))
        for json_file in json_files:
            # Expected filename format: "pair_id1_id2.json"
            base = os.path.basename(json_file)
            match = re.match(r"pair_(\d+)_(\d+)\.json", base)
            if not match:
                continue
            id1, id2 = match.groups()

            # Load the pair data.
            G1, G2, labels1, labels2 = load_pair_json(json_file)

            # Collect degrees from both graphs.
            degrees.extend(dict(G1.degree()).values())
            degrees.extend(dict(G2.degree()).values())

            # Compute each heuristic and append result.
            h1 = heuristic_node_count(G1, G2)
            heuristic_results["Node Count Difference"].append({
                "Dataset": dataset_name,
                "graph_id1": id1,
                "graph_id2": id2,
                "Heuristic": "Node Count Difference",
                "Lower Bound": h1
            })

            h2 = heuristic_edge_count(G1, G2)
            heuristic_results["Edge Count Difference"].append({
                "Dataset": dataset_name,
                "graph_id1": id1,
                "graph_id2": id2,
                "Heuristic": "Edge Count Difference",
                "Lower Bound": h2
            })

            h3 = heuristic_degree_distribution(G1, G2)
            heuristic_results["Degree Distribution Difference"].append({
                "Dataset": dataset_name,
                "graph_id1": id1,
                "graph_id2": id2,
                "Heuristic": "Degree Distribution Difference",
                "Lower Bound": h3
            })

            h4 = heuristic_edge_overlap(G1, G2)
            heuristic_results["Edge Overlap Difference"].append({
                "Dataset": dataset_name,
                "graph_id1": id1,
                "graph_id2": id2,
                "Heuristic": "Edge Overlap Difference",
                "Lower Bound": h4
            })

            h5 = heuristic_basic_combined(G1, G2)
            heuristic_results["Combined Basic (Node+Edge Count Difference)"].append({
                "Dataset": dataset_name,
                "graph_id1": id1,
                "graph_id2": id2,
                "Heuristic": "Combined Basic (Node+Edge Count Difference)",
                "Lower Bound": h5
            })

            # Optional: Only compute node label mismatch if both label lists exist.
            if labels1 is not None and labels2 is not None:
                h6 = heuristic_node_label_mismatch(labels1, labels2)
                heuristic_results["Node Label Mismatch"].append({
                    "Dataset": dataset_name,
                    "graph_id1": id1,
                    "graph_id2": id2,
                    "Heuristic": "Node Label Mismatch",
                    "Lower Bound": h6
                })

        # Calculate and store degree information for the current dataset.
        if degrees:
            max_degree = max(degrees)
            avg_degree = sum(degrees) / len(degrees)
            degree_info[dataset_name] = (max_degree, avg_degree)
            print(f"Dataset: {dataset_name}, Max Degree: {max_degree}, Avg Degree: {avg_degree:.2f}")

        # For each heuristic, create a DataFrame and write out Excel files.
        for heuristic, results_list in heuristic_results.items():
            if not results_list:
                # If no results for this heuristic (e.g. no label data), skip writing.
                continue
            df = pd.DataFrame(results_list)
            # Sanitize heuristic name for file names: remove non-word characters.
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

    # Optionally, print aggregated degree information for all datasets.
    print("\n--- Degree Information for All Datasets ---")
    for dataset_name, (max_degree, avg_degree) in degree_info.items():
        print(f"Dataset: {dataset_name}, Max Degree: {max_degree}, Avg Degree: {avg_degree:.2f}")

if __name__ == "__main__":
    main()
