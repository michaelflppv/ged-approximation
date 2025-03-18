"""
extract_edit_path.py

This script loads a saved SimGNN model and a JSON file representing a pair of graphs.
It computes node embeddings for both graphs (using the model's convolutional layers)
and then uses the Hungarian algorithm to derive an approximate alignment between nodes.
Based on this alignment (and comparing node labels), the script outputs a sequence of
approximate edit operations (matches, substitutions, deletions, insertions) that describe
an edit path from graph_1 to graph_2 in machine-readable JSON format.

Paths for the JSON file, model file, and output directory are specified directly in the code.
"""

import os
import sys
import json
import numpy as np
from scipy.optimize import linear_sum_assignment
import torch
from torch.serialization import safe_globals
from torch.nn.parameter import UninitializedParameter

# Import SimGNN modules
from param_parser import parameter_parser  # Provided param_parser.py (does not accept argument list)
from simgnn import SimGNNTrainer
from utils import process_pair

# ============================================================================
# Specify your file paths here:
# ============================================================================
JSON_PATH   = r"C:\project_data\processed_data\json_pairs\PROTEINS\pair_1000_1003.json"
MODEL_PATH  = r"C:\Users\mikef\PycharmProjects\ged-approximation\SimGNN\models\simgnn_model.pth"  # update this path if necessary
OUTPUT_DIR  = r"C:\project_data\results\extracted_paths"   # update this path if necessary
DUMMY_COST  = 1.0
# ============================================================================

# Define a custom JSON encoder to handle NumPy types.
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

def load_model(simgnn_args):
    """
    Load a pretrained SimGNN model using the SimGNN parameters.
    The model path is specified by the MODEL_PATH constant.
    The model is loaded within a safe_globals context so that the uninitialized parameter
    global is allowed.
    """
    simgnn_args.load_path = MODEL_PATH
    trainer = SimGNNTrainer(simgnn_args)
    # Wrap the load() call in a safe_globals context manager to allow UninitializedParameter.
    with safe_globals([UninitializedParameter]):
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
        List of dictionaries, each describing one edit operation in machine-readable format.
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

    # Interpret the assignment as edit operations.
    edit_operations = []
    for i, j in zip(row_ind, col_ind):
        if i < n1 and j < n2:
            if labels1[i] == labels2[j]:
                op = {
                    "op": "match",
                    "graph1_node": int(i),
                    "graph2_node": int(j),
                    "label": labels1[i]
                }
            else:
                op = {
                    "op": "substitute",
                    "graph1_node": int(i),
                    "graph1_label": labels1[i],
                    "graph2_node": int(j),
                    "graph2_label": labels2[j]
                }
            edit_operations.append(op)
        elif i < n1 and j >= n2:
            op = {
                "op": "delete",
                "graph1_node": int(i),
                "graph1_label": labels1[i]
            }
            edit_operations.append(op)
        elif i >= n1 and j < n2:
            op = {
                "op": "insert",
                "graph2_node": int(j),
                "graph2_label": labels2[j]
            }
            edit_operations.append(op)
    return edit_operations

def main():
    # Parse SimGNN parameters (from the command line or defaults)
    simgnn_args = parameter_parser()

    # Load the graph pair using the specified JSON_PATH.
    if not os.path.exists(JSON_PATH):
        print(f"Error: JSON file '{JSON_PATH}' does not exist.")
        sys.exit(1)
    data = process_pair(JSON_PATH)

    # Load the pretrained model.
    trainer = load_model(simgnn_args)

    # Compute node embeddings.
    emb1, emb2 = get_node_embeddings(trainer, data)

    # Extract edit operations in machine-readable format.
    labels1 = data["labels_1"]
    labels2 = data["labels_2"]
    edit_ops = extract_edit_operations(emb1, emb2, labels1, labels2, dummy_cost=DUMMY_COST)

    # Prepare the results directory.
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, 'simgnn_edit_path.json')
    # Write the machine-readable edit path as JSON using the custom encoder.
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"edit_path": edit_ops}, f, indent=2, cls=NumpyEncoder)

    print("Extracted machine-readable edit path saved to:")
    print(output_file)
    # Optionally, also print the JSON to the console.
    print(json.dumps({"edit_path": edit_ops}, indent=2, cls=NumpyEncoder))

if __name__ == "__main__":
    main()