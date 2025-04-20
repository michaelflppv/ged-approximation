#!/usr/bin/env python
"""
This script evaluates a SimGNN model using a set of JSON files containing graph pairs.
It loads an Excel file containing exact GED values and compares them to the model's predictions.
If the number of rows in the exact GED Excel file does not match number of JSON files,
a warning is printed and missing values are replaced with "N/A".
If the final performance DataFrame is too large, it is split into multiple Excel files.
Additionally, torch.load is now called with weights_only=True to avoid FutureWarnings.
"""

import os
import glob
import json
import time
import math
import torch
import psutil
import pandas as pd
from tqdm import tqdm
from utils import process_pair
from simgnn import SimGNNTrainer
from param_parser import parameter_parser


# -------------------------------
# Helper functions
# -------------------------------
def load_json(filepath):
    """Load a JSON file and return the data. Raises ValueError if file is empty."""
    with open(filepath, "r") as f:
        content = f.read().strip()
        if not content:
            raise ValueError(f"Empty JSON file: {filepath}")
        return json.loads(content)


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

def calculate_accuracy(predicted, exact):
    """
    Calculate accuracy for a pair based on the predicted GED and the exact GED (min_ged).
    Accuracy is defined as 1 - (absolute_error / exact), clamped to a minimum of 0.
    If the exact value is 0, we return 1 if predicted is also 0, else 0.
    """
    if exact == 0:
        return 1.0 if predicted == 0 else 0.0
    acc = 1 - abs(predicted - exact) / exact
    return max(0.0, acc)


def split_and_save_dataframe(df, base_save_path, max_rows=1048576):
    """Split DataFrame into multiple Excel files if needed."""
    if len(df) <= max_rows:
        df.to_excel(base_save_path, index=False)
        print(f"Performance saved to: {base_save_path}")
    else:
        num_files = math.ceil(len(df) / max_rows)
        for part in range(num_files):
            start = part * max_rows
            end = start + max_rows
            chunk = df.iloc[start:end]
            part_path = os.path.splitext(base_save_path)[0] + f"_part{part+1}.xlsx"
            chunk.to_excel(part_path, index=False)
            print(f"Part {part+1}: Performance saved to: {part_path}")


# -------------------------------
# Main testing routine
# -------------------------------
def main():
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_dir = "../../processed_data/json_pairs/AIDS"
    model_path = "../models/simgnn_model.h5"
    # Path to the Excel file with exact GED results (must contain a column "min_ged")
    exact_ged_path = "../../results/exact_ged/AIDS/results.xlsx"

    # Find and sort all JSON files in the directory to ensure order matches the Excel file rows.
    json_files = glob.glob(os.path.join(json_dir, "*.json"))
    json_files.sort()
    if not json_files:
        print("No JSON files found in", json_dir)
        return

    # Load the exact GED Excel file.
    df_exact = pd.read_excel(exact_ged_path)
    if df_exact.shape[0] != len(json_files):
        print("Warning: Number of rows in exact GED Excel file does not match number of JSON files.")

    # Create a dummy args namespace required for model instantiation.
    args = parameter_parser()
    args.load_path = model_path
    args.histogram = False

    # Create device and move model to device.
    #device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = SimGNNTrainer(args).model
    state_dict = torch.load(model_path, map_location=torch.device("cpu"), weights_only=False)
    model.load_state_dict(state_dict)
    #model.to(device)
    model.eval()

    # List to store per-pair results.
    pair_results = []

    # Get process handle.
    process = psutil.Process(os.getpid())

    counter = 0
    # Process each JSON file.
    for graph_pair in tqdm(json_files):
        data = process_pair(graph_pair)

        counter += 1
        if counter == 200000:
            break
        # Measure per-pair runtime and memory usage.
        pair_start_time = time.time()
        mem_before = process.memory_info().rss / (1024 * 1024)

        n1 = len(data["labels_1"])
        n2 = len(data["labels_2"])

        # Compute graph densities.
        density1 = compute_density(data["graph_1"], n1)
        density2 = compute_density(data["graph_2"], n2)

        # Convert raw data to torch tensors.
        try:
            torch_data = model.transfer_to_torch(data)
        except Exception as e:
            print(f"Skipping pair due to error in transfer_to_torch: {e}")
            continue

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

        # Measure per-pair runtime and memory after processing.
        pair_end_time = time.time()
        mem_after = process.memory_info().rss / (1024 * 1024)
        runtime_pair = pair_end_time - pair_start_time
        mem_delta = mem_after - mem_before
        mem_delta = mem_delta if mem_delta > 0 else 0.0

        # Parse graph IDs from filename (expects format: "pair_id1_id2.json")
        base_name = os.path.splitext(os.path.basename(graph_pair))[0]
        parts = base_name.split('_')
        if len(parts) >= 3 and parts[0] == "pair":
            graph_id_1 = parts[1]
            graph_id_2 = parts[2]
        else:
            if len(parts) >= 2:
                graph_id_1 = parts[0]
                graph_id_2 = parts[1]
            else:
                graph_id_1 = base_name
                graph_id_2 = base_name

        scalability = runtime_pair / (n1 + n2) if (n1 + n2) > 0 else runtime_pair

        print("Pair: " + graph_id_1 + " " + graph_id_2)

        pair_results.append({
            "method": "SimGNN",
            "ged": pred_ged,
            "runtime": runtime_pair,
            "graph_id_1": graph_id_1,
            "graph_id_2": graph_id_2,
            "accuracy": "",
            "absolute_error": "",
            "squared_error": "",
            "memory_usage_mb": mem_delta,
            "graph1_n": n1,
            "graph1_density": density1,
            "graph2_n": n2,
            "graph2_density": density2,
            "scalability": scalability
        })

    # Define the required column order.
    ordered_columns = [
        "method",
        "graph_id_1",
        "graph_id_2",
        "ged",
        "accuracy",
        "absolute_error",
        "squared_error",
        "runtime",
        "memory_usage_mb",
        "graph1_n",
        "graph1_density",
        "graph2_n",
        "graph2_density",
        "scalability"
    ]
    df_pairs = pd.DataFrame(pair_results)[ordered_columns]

    # Define the directory for saving performance results.
    results_dir = "../../results/simgnn/AIDS"
    os.makedirs(results_dir, exist_ok=True)
    save_path = os.path.join(results_dir, "performance.xlsx")

    # Split and save DataFrame if necessary.
    split_and_save_dataframe(df_pairs, save_path)

    print(f"\nPerformance saved to: {save_path}")

if __name__ == "__main__":
    main()
