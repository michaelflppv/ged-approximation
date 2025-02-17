#!/usr/bin/env python

import os
import glob
import json
import time
import math
import torch
import numpy as np
import psutil
import pandas as pd


# -------------------------------
# Helper functions
# -------------------------------
def load_json(filepath):
    """Load a JSON file and return the data."""
    with open(filepath, "r") as f:
        return json.load(f)


def compute_density(edge_list, num_nodes):
    """
    Compute the density of an undirected graph given its edge list and number of nodes.
    Density = (2 * |E_unique|) / (n * (n - 1))
    where |E_unique| is the number of unique edges (ignoring order).
    """
    unique_edges = set()
    for edge in edge_list:
        if len(edge) < 2:
            continue
        a, b = edge[0], edge[1]
        if a != b:
            unique_edges.add(tuple(sorted((a, b))))
    if num_nodes <= 1:
        return 0.0
    return (2 * len(unique_edges)) / (num_nodes * (num_nodes - 1))


def transfer_to_torch(data, global_labels):
    """
    Convert the raw JSON data into torch tensors.
    This function mimics the conversion in SimGNNTrainer.transfer_to_torch.
    """
    new_data = dict()

    # Create undirected edges by adding reverse edges.
    edges_1 = data["graph_1"] + [[y, x] for x, y in data["graph_1"]]
    edges_2 = data["graph_2"] + [[y, x] for x, y in data["graph_2"]]

    edges_1 = torch.tensor(np.array(edges_1).T, dtype=torch.long)
    edges_2 = torch.tensor(np.array(edges_2).T, dtype=torch.long)

    features_1, features_2 = [], []
    # One-hot encode the node labels based on the global_labels mapping.
    for label in data["labels_1"]:
        label_str = str(label)
        one_hot = [1.0 if global_labels[label_str] == i else 0.0 for i in range(len(global_labels))]
        features_1.append(one_hot)
    for label in data["labels_2"]:
        label_str = str(label)
        one_hot = [1.0 if global_labels[label_str] == i else 0.0 for i in range(len(global_labels))]
        features_2.append(one_hot)

    features_1 = torch.FloatTensor(np.array(features_1))
    features_2 = torch.FloatTensor(np.array(features_2))

    new_data["edge_index_1"] = edges_1
    new_data["edge_index_2"] = edges_2
    new_data["features_1"] = features_1
    new_data["features_2"] = features_2

    # Calculate normalized GED as in training:
    norm_ged = data["ged"] / (0.5 * (len(data["labels_1"]) + len(data["labels_2"])))
    new_data["target"] = torch.tensor(np.exp(-norm_ged), dtype=torch.float32).view(1)
    # Also keep the raw GED and graph sizes for evaluation:
    new_data["raw_ged"] = data["ged"]
    new_data["num_nodes_1"] = len(data["labels_1"])
    new_data["num_nodes_2"] = len(data["labels_2"])

    return new_data


# -------------------------------
# Main testing routine
# -------------------------------
def main():
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_dir = os.path.join(base_dir, "../../processed_data/json_pairs/IMDB-BINARY")
    model_path = os.path.join(base_dir, "models/simgnn_model.h5")

    # Find all JSON files in the directory
    json_files = glob.glob(os.path.join(json_dir, "*.json"))
    if not json_files:
        print("No JSON files found in", json_dir)
        return

    # Build a global mapping of unique node labels across all graph pairs.
    global_labels_set = set()
    for filepath in json_files:
        data = load_json(filepath)
        global_labels_set.update([str(label) for label in data["labels_1"]])
        global_labels_set.update([str(label) for label in data["labels_2"]])
    sorted_labels = sorted(global_labels_set, key=lambda x: x)
    global_labels = {label: idx for idx, label in enumerate(sorted_labels)}

    # Create a dummy args namespace required for model instantiation.
    from argparse import Namespace
    args = Namespace(
        filters_1=128,
        filters_2=64,
        filters_3=32,
        tensor_neurons=16,
        bottle_neck_neurons=16,
        bins=16,
        dropout=0.5,
        histogram=False  # Change to True if your model was trained with histogram features.
    )

    # Import the SimGNN model (assumes simgnn.py is in the same folder)
    from simgnn import SimGNN

    # Instantiate the model with the number of unique labels.
    model = SimGNN(args, number_of_labels=len(global_labels))
    # Load the saved model state.
    state_dict = torch.load(model_path, map_location=torch.device("cpu"))
    model.load_state_dict(state_dict)
    model.eval()

    # Metrics initialization for overall stats.
    total_pairs = len(json_files)
    mse_sum = 0.0
    mae_sum = 0.0
    max_graph_size = 0

    # List to store per-pair results.
    pair_results = []

    # Get process handle.
    process = psutil.Process(os.getpid())

    # Process each JSON file.
    for filepath in json_files:
        # Measure per-pair runtime and memory usage.
        pair_start_time = time.time()
        mem_before = process.memory_info().rss / (1024 * 1024)

        data = load_json(filepath)
        n1 = len(data["labels_1"])
        n2 = len(data["labels_2"])
        max_graph_size = max(max_graph_size, n1, n2)

        # Compute graph densities.
        density1 = compute_density(data["graph_1"], n1)
        density2 = compute_density(data["graph_2"], n2)

        # Convert raw data to torch tensors.
        torch_data = transfer_to_torch(data, global_labels)

        # Get model prediction (a similarity score).
        with torch.no_grad():
            prediction = model(torch_data)  # Expected shape: (1,)
        pred_similarity = prediction.item()
        # Invert the transformation: predicted normalized GED = -log(similarity)
        if pred_similarity <= 0:
            pred_similarity = 1e-10  # safeguard against log(0)
        pred_norm_ged = -math.log(pred_similarity)
        # Compute the predicted raw GED.
        pred_ged = pred_norm_ged * (0.5 * (n1 + n2))

        # Compute per-pair errors.
        gt_ged = data["ged"]
        abs_error = abs(pred_ged - gt_ged)
        squared_error = (pred_ged - gt_ged) ** 2
        mse_sum += squared_error
        mae_sum += abs_error

        # Measure per-pair runtime and memory after processing.
        pair_end_time = time.time()
        mem_after = process.memory_info().rss / (1024 * 1024)
        runtime_pair = pair_end_time - pair_start_time
        mem_delta = mem_after - mem_before
        # In case garbage collection freed memory, we record non-negative usage.
        mem_delta = mem_delta if mem_delta > 0 else 0.0

        pair_results.append({
            "File": os.path.basename(filepath),
            "Predicted GED": pred_ged,
            "Ground Truth GED": gt_ged,
            "Absolute Error": abs_error,
            "Squared Error": squared_error,
            "Graph1 Nodes": n1,
            "Graph2 Nodes": n2,
            "Graph1 Density": density1,
            "Graph2 Density": density2,
            "Runtime (s)": runtime_pair,
            "Memory Usage (MB)": mem_delta
        })

    mse = mse_sum / total_pairs
    mae = mae_sum / total_pairs

    # Compute overall runtime and memory usage for processing all pairs.
    # (For overall memory, we simply take the current memory usage.)
    overall_runtime = sum([r["Runtime (s)"] for r in pair_results])
    overall_memory_usage = process.memory_info().rss / (1024 * 1024)

    # -------------------------------
    # Save Performance Metrics to Excel
    # -------------------------------
    # Create a DataFrame for per-pair results.
    df_pairs = pd.DataFrame(pair_results)

    # Create a summary DataFrame for overall metrics.
    summary_data = {
        "Total Graph Pairs": [total_pairs],
        "Average MSE": [mse],
        "Average MAE": [mae],
        "Total Runtime (s)": [overall_runtime],
        "Memory Usage (MB)": [overall_memory_usage],
        "Maximum Graph Size": [max_graph_size]
    }
    df_summary = pd.DataFrame(summary_data)

    # Define the directory for saving performance results.
    results_dir = os.path.join(base_dir, "../../results/neural/IMDB-BINARY")
    os.makedirs(results_dir, exist_ok=True)
    save_path = os.path.join(results_dir, "performance.xlsx")

    # Save both DataFrames to separate sheets in the Excel workbook.
    with pd.ExcelWriter(save_path) as writer:
        df_pairs.to_excel(writer, sheet_name="Pair Results", index=False)
        df_summary.to_excel(writer, sheet_name="Summary", index=False)

    print(f"\nPerformance saved to: {save_path}")


if __name__ == "__main__":
    main()
