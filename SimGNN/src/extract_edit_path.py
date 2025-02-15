#!/usr/bin/env python3
"""
extract_edit_path.py

This script loads a saved SimGNN model and a JSON file representing a pair of graphs.
It computes node embeddings for both graphs (using the model's convolutional layers)
and then uses the Hungarian algorithm to derive an approximate alignment between nodes.
Based on this alignment (and comparing node labels), the script outputs a sequence of
approximate edit operations (matches, substitutions, deletions, insertions) that describe
an edit path from graph_1 to graph_2.

Usage (from SimGNN/src directory):
    python extract_edit_path.py --json_file ../../processed_data/json_pairs/PROTEINS/pair_1_2.json [--model_path <relative_model_path>] [--dummy_cost 1.0]

By default, if --model_path is not provided, the model at ../models/simgnn_model.pth is used.
"""

import os
import sys
import argparse
import numpy as np
from scipy.optimize import linear_sum_assignment

# Import SimGNN modules
from param_parser import parameter_parser  # Provided param_parser.py (does not accept argument list)
from simgnn import SimGNNTrainer
from utils import process_pair


def parse_custom_args():
    """
    Parse custom arguments (like --json_file, --model_path, and --dummy_cost)
    and remove them from sys.argv before invoking the SimGNN parameter parser.
    """
    custom_parser = argparse.ArgumentParser(add_help=False)
    custom_parser.add_argument("--json_file", type=str, required=True,
                               help="Relative path to a JSON file with a graph pair (e.g., ../../processed_data/json_pairs/PROTEINS/pair_1_2.json).")
    custom_parser.add_argument("--model_path", type=str, default=None,
                               help="Relative path to a saved SimGNN model. Default: ../models/simgnn_model.pth")
    custom_parser.add_argument("--dummy_cost", type=float, default=1.0,
                               help="Cost for insertions/deletions when padding the cost matrix.")
    custom_args, remaining_args = custom_parser.parse_known_args()
    # Replace sys.argv with the leftover arguments so that parameter_parser() doesn't see our custom ones.
    sys.argv = [sys.argv[0]] + remaining_args
    return custom_args


def load_model(custom_args, simgnn_args):
    """
    Load a pretrained SimGNN model using the SimGNN parameters.
    If the custom --model_path argument is provided, it overrides the default load path.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if custom_args.model_path:
        simgnn_args.load_path = os.path.normpath(os.path.join(script_dir, custom_args.model_path))
    else:
        simgnn_args.load_path = os.path.normpath(os.path.join(script_dir, "..", "models", "simgnn_model.pth"))
    trainer = SimGNNTrainer(simgnn_args)
    trainer.load()
    return trainer


def get_node_embeddings(trainer, data):
    """
    Given a data dictionary (with keys "edge_index_1", "features_1", etc.)
    and a trainer, compute the node embeddings for each graph using the model's
    convolutional layers.
    """
    data_torch = trainer.transfer_to_torch(data)
    emb1 = trainer.model.convolutional_pass(data_torch["edge_index_1"], data_torch["features_1"])
    emb2 = trainer.model.convolutional_pass(data_torch["edge_index_2"], data_torch["features_2"])
    return emb1, emb2


def pad_cost_matrix(cost_matrix, n_rows, n_cols, dummy_cost):
    """
    Pad a non-square cost matrix to a square one by adding extra rows or columns
    with a fixed dummy cost.
    """
    n = max(n_rows, n_cols)
    padded = np.full((n, n), dummy_cost)
    padded[:n_rows, :n_cols] = cost_matrix
    return padded


def extract_edit_operations(emb1, emb2, labels1, labels2, dummy_cost=1.0):
    """
    Given node embeddings and corresponding labels for two graphs, compute a cost matrix
    (using Euclidean distance), solve the assignment problem, and interpret the matching
    as edit operations.

    Returns:
        List of strings, each describing one edit operation.
    """
    # Convert embeddings to numpy arrays.
    emb1_np = emb1.detach().cpu().numpy()
    emb2_np = emb2.detach().cpu().numpy()
    n1 = emb1_np.shape[0]
    n2 = emb2_np.shape[0]

    # Compute pairwise Euclidean distances.
    cost_matrix = np.linalg.norm(emb1_np[:, None, :] - emb2_np[None, :, :], axis=2)
    padded_cost = pad_cost_matrix(cost_matrix, n1, n2, dummy_cost)
    row_ind, col_ind = linear_sum_assignment(padded_cost)

    edit_operations = []
    for i, j in zip(row_ind, col_ind):
        if i < n1 and j < n2:
            if labels1[i] == labels2[j]:
                op = f"Match: Graph1 node {i} -> Graph2 node {j} (label {labels1[i]})"
            else:
                op = f"Substitute: Graph1 node {i} (label {labels1[i]}) -> Graph2 node {j} (label {labels2[j]})"
            edit_operations.append(op)
        elif i < n1 and j >= n2:
            op = f"Delete: Graph1 node {i} (label {labels1[i]})"
            edit_operations.append(op)
        elif i >= n1 and j < n2:
            op = f"Insert: Graph2 node {j} (label {labels2[j]})"
            edit_operations.append(op)
    return edit_operations


def main():
    # First, parse our custom arguments.
    custom_args = parse_custom_args()

    # Now parse SimGNN parameters (leftover command-line arguments).
    simgnn_args = parameter_parser()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.normpath(os.path.join(script_dir, custom_args.json_file))
    if not os.path.exists(json_path):
        print(f"Error: JSON file '{json_path}' does not exist.")
        sys.exit(1)

    # Load the graph pair.
    data = process_pair(json_path)

    # Load the pretrained model.
    trainer = load_model(custom_args, simgnn_args)

    # Compute node embeddings.
    emb1, emb2 = get_node_embeddings(trainer, data)

    # Extract edit operations.
    labels1 = data["labels_1"]
    labels2 = data["labels_2"]
    edit_ops = extract_edit_operations(emb1, emb2, labels1, labels2, dummy_cost=custom_args.dummy_cost)

    # Prepare the results directory relative to this script's location.
    project_root = os.path.normpath(os.path.join(script_dir, '..', '..'))
    results_dir = os.path.join(project_root, 'results', 'extracted_paths')
    os.makedirs(results_dir, exist_ok=True)

    output_file = os.path.join(results_dir, 'edit_path.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('Extracted approximate edit path:\n')
        for op in edit_ops:
            f.write(op + '\n')

    print("Extracted approximate edit path:")
    for op in edit_ops:
        print(op)


if __name__ == "__main__":
    main()
