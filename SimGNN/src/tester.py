#!/usr/bin/env python3
import os
import sys
import warnings
import time
import math
import numpy as np
import pandas as pd
import torch

# Try to import psutil for memory measurement; if not available, skip memory metrics.
try:
    import psutil
except ImportError:
    psutil = None

warnings.filterwarnings("ignore", category=RuntimeWarning)  # Suppress NumPy warnings

from param_parser import parameter_parser
from simgnn import SimGNNTrainer
from utils import tab_printer, process_pair


def compute_predicted_ged(model_output):
    """
    Compute the predicted graph edit distance (GED) from the model output.
    The model outputs a similarity score s = exp(-normalized_GED); thus,
    normalized_GED = -log(s).
    """
    pred_sim = model_output.item()
    # Avoid log(0)
    if pred_sim <= 0:
        return float('inf')
    return -math.log(pred_sim)


def compute_graph_metrics(graph_edges, graph_labels):
    """
    Compute basic graph metrics:
      - n: number of nodes (based on the label list)
      - m: number of edges (as provided in the edge list)
      - density: for an undirected graph, density = (2*m)/(n*(n-1)) (if n > 1)
    """
    n = len(graph_labels)
    m = len(graph_edges)
    density = (2 * m) / (n * (n - 1)) if n > 1 else 0
    return n, m, density


def evaluate_model(trainer, args):
    """
    Evaluate the model on all test graph pairs and compute additional metrics:
      - Average predicted GED (using -log(predicted similarity))
      - Average runtime per graph pair evaluation
      - Average graph size (nodes) and density (averaged over both graphs in each pair)
      - Total number of test pairs (as a measure of scalability)
      - Memory usage of the process (in MB)
    """
    # List all JSON files in the testing folder.
    test_files = sorted([f for f in os.listdir(args.testing_graphs) if f.endswith(".json")])
    test_paths = [os.path.join(args.testing_graphs, f) for f in test_files]

    pred_ged_list = []
    runtime_list = []
    graph_sizes = []
    graph_densities = []

    for test_path in test_paths:
        start_time = time.time()

        # Load the graph pair data.
        data = process_pair(test_path)
        # Data keys: "graph_1", "graph_2", "labels_1", "labels_2"
        # Compute metrics for each graph.
        n1, m1, density1 = compute_graph_metrics(data["graph_1"], data["labels_1"])
        n2, m2, density2 = compute_graph_metrics(data["graph_2"], data["labels_2"])
        graph_sizes.append((n1, n2))
        graph_densities.append((density1, density2))

        # Prepare data for the model.
        data_torch = trainer.transfer_to_torch(data)
        with torch.no_grad():
            output = trainer.model(data_torch)
        pred_ged = compute_predicted_ged(output)
        pred_ged_list.append(pred_ged)

        end_time = time.time()
        runtime_list.append(end_time - start_time)

    avg_pred_ged = np.mean(pred_ged_list) if pred_ged_list else None
    avg_runtime = np.mean(runtime_list) if runtime_list else None
    avg_nodes = np.mean([(n1 + n2) / 2 for (n1, n2) in graph_sizes]) if graph_sizes else None
    avg_density = np.mean([(d1 + d2) / 2 for (d1, d2) in graph_densities]) if graph_densities else None
    scalability = len(test_paths)

    # Memory usage in MB.
    if psutil is not None:
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / (1024 * 1024)
    else:
        memory_usage = None

    performance = {
        "avg_predicted_ged": avg_pred_ged,
        "avg_runtime_sec": avg_runtime,
        "avg_nodes": avg_nodes,
        "avg_density": avg_density,
        "num_test_pairs": scalability,
        "memory_usage_MB": memory_usage,
    }

    return performance


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

    # Print parameters in a tabular format.
    tab_printer(args)

    # Initialize the SimGNN trainer.
    trainer = SimGNNTrainer(args)

    # Load or train the model.
    if args.load_path:
        trainer.load()
    else:
        trainer.fit()
        trainer.save()

    # Evaluate the model with additional metrics.
    performance = evaluate_model(trainer, args)

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
