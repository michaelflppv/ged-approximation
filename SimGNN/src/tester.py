#!/usr/bin/env python3
import os
import sys
import time
import math
import warnings
import numpy as np
import pandas as pd
import torch

# Suppress NumPy runtime warnings.
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Add the 'scripts' directory (two levels up from SimGNN/src) to sys.path to import gedlib_parser.
script_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.normpath(os.path.join(script_dir, "..", "..", "scripts"))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

import scripts.gedlib_parser as gedlib_parser  # This module provides the STAR (Exact) ground truth GED.

from param_parser import parameter_parser
from simgnn import SimGNNTrainer
from utils import tab_printer, process_pair

# Optionally import psutil for memory measurement.
try:
    import psutil
except ImportError:
    psutil = None


def compute_predicted_ged(model_output):
    """
    Compute the predicted GED from the model's output.
    The model outputs a similarity score s = exp(-normalized_GED), so:
         normalized_GED = -log(s)
    """
    pred_sim = model_output.item()
    # Avoid log(0); if s is zero or negative, return infinity.
    if pred_sim <= 0:
        return float('inf')
    return -math.log(pred_sim)


def compute_graph_metrics(graph_edges, graph_labels):
    """
    Compute basic graph metrics:
      - n: number of nodes (from the label list)
      - m: number of edges (as provided in the edge list)
      - density: for an undirected graph, density = (2*m)/(n*(n-1)) (if n>1)
    """
    n = len(graph_labels)
    m = len(graph_edges)
    density = (2 * m) / (n * (n - 1)) if n > 1 else 0
    return n, m, density


def evaluate_simgnn(trainer, test_folder):
    """
    Evaluate the SimGNN model on each test JSON file.
    For each graph pair, compute:
      - Predicted GED (via the model)
      - Runtime for processing that test pair
      - Graph sizes and densities for both graphs
    Returns aggregated metrics.
    """
    test_files = sorted([f for f in os.listdir(test_folder) if f.endswith(".json")])
    test_paths = [os.path.join(test_folder, f) for f in test_files]

    pred_ged_list = []
    runtime_list = []
    sizes_list = []
    densities_list = []

    for test_path in test_paths:
        start_time = time.time()

        data = process_pair(test_path)
        # Compute graph metrics for both graphs.
        n1, _, density1 = compute_graph_metrics(data["graph_1"], data["labels_1"])
        n2, _, density2 = compute_graph_metrics(data["graph_2"], data["labels_2"])
        sizes_list.append((n1, n2))
        densities_list.append((density1, density2))

        # Prepare data and compute predicted GED.
        data_torch = trainer.transfer_to_torch(data)
        with torch.no_grad():
            output = trainer.model(data_torch)
        pred_ged = compute_predicted_ged(output)
        pred_ged_list.append(pred_ged)

        end_time = time.time()
        runtime_list.append(end_time - start_time)

    # Aggregate metrics.
    avg_pred_ged = np.mean(pred_ged_list) if pred_ged_list else None
    avg_runtime = np.mean(runtime_list) if runtime_list else None
    avg_nodes = np.mean([(n1 + n2) / 2 for (n1, n2) in sizes_list]) if sizes_list else None
    avg_density = np.mean([(d1 + d2) / 2 for (d1, d2) in densities_list]) if densities_list else None
    num_test_pairs = len(test_paths)

    # Memory usage of the current process (in MB).
    if psutil is not None:
        process = psutil.Process(os.getpid())
        mem_usage_mb = process.memory_info().rss / (1024 * 1024)
    else:
        mem_usage_mb = None

    simgnn_metrics = {
        "simgnn_avg_predicted_ged": avg_pred_ged,
        "simgnn_avg_runtime_sec": avg_runtime,
        "simgnn_avg_nodes": avg_nodes,
        "simgnn_avg_density": avg_density,
        "simgnn_num_test_pairs": num_test_pairs,
        "simgnn_memory_usage_MB": mem_usage_mb,
    }
    return simgnn_metrics


def get_ground_truth_metrics():
    """
    Use gedlib_parser to run the STAR (Exact) method and obtain ground truth GED and metrics.
    Note: gedlib_parser.py uses preset relative paths (e.g., for the AIDS dataset). If you
    intend to evaluate PROTEINS, update the paths in gedlib_parser.py accordingly.
    """
    # Run the GEDLIB executable.
    gt_results = gedlib_parser.run_ged(gedlib_parser.DATASET_PATH, gedlib_parser.COLLECTION_XML)
    ground_truth = {}
    # Look for the STAR (Exact) method result.
    for res in gt_results:
        if res.get("method") == "STAR (Exact)":
            ground_truth = {
                "ground_truth_ged": res.get("ged"),
                "ground_truth_runtime_sec": res.get("runtime"),
                "ground_truth_memory_usage_kb": res.get("memory_usage_kb"),
                "ground_truth_graph1_n": res.get("graph1_n"),
                "ground_truth_graph1_density": res.get("graph1_density"),
                "ground_truth_graph2_n": res.get("graph2_n"),
                "ground_truth_graph2_density": res.get("graph2_density"),
            }
            break
    if not ground_truth:
        # If STAR (Exact) was not found, mark values as N/A.
        ground_truth = {
            "ground_truth_ged": "N/A",
            "ground_truth_runtime_sec": "N/A",
            "ground_truth_memory_usage_kb": "N/A",
            "ground_truth_graph1_n": "N/A",
            "ground_truth_graph1_density": "N/A",
            "ground_truth_graph2_n": "N/A",
            "ground_truth_graph2_density": "N/A",
        }
    return ground_truth


def main():
    # Parse command-line parameters.
    args = parameter_parser()
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Set relative path for JSON graph pairs.
    json_folder = os.path.join("..", "..", "processed_data", "json_pairs", "PROTEINS")
    args.training_graphs = os.path.normpath(os.path.join(script_dir, json_folder))
    args.testing_graphs = os.path.normpath(os.path.join(script_dir, json_folder))

    # Verify that training and testing folders exist.
    if not os.path.exists(args.training_graphs):
        print(f"Error: Training graphs folder '{args.training_graphs}' does not exist.")
        sys.exit(1)
    if not os.path.exists(args.testing_graphs):
        print(f"Error: Testing graphs folder '{args.testing_graphs}' does not exist.")
        sys.exit(1)

    print(f"Using training graphs folder: {args.training_graphs}")
    print(f"Using testing graphs folder: {args.testing_graphs}")

    # Set up model save/load path relative to the src directory.
    model_dir = os.path.join("..", "models")
    model_dir = os.path.normpath(os.path.join(script_dir, model_dir))
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        print(f"Created models directory: {model_dir}")
    model_file = os.path.join(model_dir, "simgnn_model.pth")

    # Use a pretrained model if it exists; otherwise, set the save_path.
    if os.path.exists(model_file):
        args.load_path = model_file
        print(f"Pretrained model found. Loading model from: {model_file}")
    else:
        args.load_path = None
        args.save_path = model_file
        print("No pretrained model found. The model will be trained and saved.")

    # Print parameters in tabular format.
    tab_printer(args)

    # Initialize the SimGNN trainer.
    trainer = SimGNNTrainer(args)
    if args.load_path:
        trainer.load()
    else:
        trainer.fit()
        trainer.save()

    # Evaluate the SimGNN model on the test set.
    simgnn_metrics = evaluate_simgnn(trainer, args.testing_graphs)
    print("SimGNN evaluation metrics:")
    print(simgnn_metrics)

    # Get ground-truth GED metrics from the STAR (Exact) method via gedlib_parser.
    ground_truth_metrics = get_ground_truth_metrics()
    print("Ground-truth metrics (from STAR (Exact)):")
    print(ground_truth_metrics)

    # Compute error metrics if ground truth GED is available.
    if isinstance(ground_truth_metrics.get("ground_truth_ged"), (int, float)) and simgnn_metrics.get("simgnn_avg_predicted_ged") is not None:
        abs_error = abs(simgnn_metrics["simgnn_avg_predicted_ged"] - ground_truth_metrics["ground_truth_ged"])
        rel_error = (abs_error / ground_truth_metrics["ground_truth_ged"]) * 100 if ground_truth_metrics["ground_truth_ged"] != 0 else None
    else:
        abs_error = "N/A"
        rel_error = "N/A"

    # Combine all performance metrics.
    performance = {}
    performance.update(simgnn_metrics)
    performance.update(ground_truth_metrics)
    performance["abs_error_ged"] = abs_error
    performance["rel_error_ged_percent"] = rel_error

    # Prepare the performance output directory (relative path).
    perf_dir = os.path.join("..", "..", "results", "neural", "PROTEINS")
    perf_dir = os.path.normpath(os.path.join(script_dir, perf_dir))
    if not os.path.exists(perf_dir):
        os.makedirs(perf_dir)
        print(f"Created performance directory: {perf_dir}")

    # Save the performance metrics to an Excel file.
    excel_file = os.path.join(perf_dir, "performance.xlsx")
    df = pd.DataFrame([performance])
    df.to_excel(excel_file, index=False)
    print(f"Performance results saved to {excel_file}")


if __name__ == "__main__":
    main()
