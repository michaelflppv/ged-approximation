"""
simgnn_extract_edit_path.py

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
import math
from scipy.optimize import linear_sum_assignment
from torch.serialization import safe_globals
from torch.nn.parameter import UninitializedParameter

# Import SimGNN modules
from param_parser import parameter_parser  # Provided param_parser.py (does not accept argument list)
from simgnn import SimGNNTrainer
from utils import process_pair, calculate_normalized_ged

# ============================================================================
# Specify the graph IDs for the pair of graphs you want to process.
# These IDs should correspond to the graphs in the dataset.
# ============================================================================
graph_id_1 = 1000
graph_id_2 = 1003

# ============================================================================
# Specify your file paths here:
# ============================================================================
JSON_PATH   = "../../processed_data/json_pairs/PROTEINS/pair_{}_{}.json".format(graph_id_1, graph_id_2)
MODEL_PATH  = "../models/simgnn_model.h5"
OUTPUT_DIR  = "../../results/extracted_paths"
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

def validate_and_order_edit_path(edit_ops, labels1, labels2):
    """
    Validate that each edit operation can be applied sequentially starting from graph_1,
    and order the operations into a valid sequence (adding an "order" field).

    The simulation assumes:
      - The initial state is graph_1 represented as a dictionary with keys "n<i>".
      - For match/substitute operations, the node (named "n<i>") exists.
      - For deletions, the node must exist and is then removed.
      - For insertions, new nodes (named "t<j>") are added.

    After applying all operations, the multiset of node labels in the final state
    must match that of graph_2 (considering matched/substituted nodes and inserted nodes).
    """
    # Group operations by type.
    modifications = []  # match and substitute ops (operating on existing nodes)
    deletions = []
    insertions = []

    for op in edit_ops:
        if op["op"] in ["match", "substitute"]:
            modifications.append(op)
        elif op["op"] == "delete":
            deletions.append(op)
        elif op["op"] == "insert":
            insertions.append(op)

    # Order modifications by graph1_node, deletions by graph1_node, and insertions by graph2_node.
    modifications.sort(key=lambda op: op["graph1_node"])
    deletions.sort(key=lambda op: op["graph1_node"])
    insertions.sort(key=lambda op: op["graph2_node"])

    ordered_ops = []
    order_index = 0
    for op in modifications:
        op["order"] = order_index
        order_index += 1
        ordered_ops.append(op)
    for op in deletions:
        op["order"] = order_index
        order_index += 1
        ordered_ops.append(op)
    for op in insertions:
        op["order"] = order_index
        order_index += 1
        ordered_ops.append(op)

    # Simulation: start with graph_1's nodes.
    current_state = {f"n{i}": labels1[i] for i in range(len(labels1))}

    # Apply each operation sequentially.
    for op in ordered_ops:
        if op["op"] == "match":
            node_id = f"n{op['graph1_node']}"
            if node_id not in current_state:
                raise ValueError(f"Match op error: node {node_id} does not exist in current state.")
            # For a match, we expect the label to be correct.
            if current_state[node_id] != op["label"]:
                raise ValueError(f"Match op error: label mismatch for node {node_id} (expected {op['label']}, got {current_state[node_id]}).")
        elif op["op"] == "substitute":
            node_id = f"n{op['graph1_node']}"
            if node_id not in current_state:
                raise ValueError(f"Substitute op error: node {node_id} does not exist in current state.")
            # Update the node's label.
            current_state[node_id] = op["graph2_label"]
        elif op["op"] == "delete":
            node_id = f"n{op['graph1_node']}"
            if node_id not in current_state:
                raise ValueError(f"Delete op error: node {node_id} does not exist in current state.")
            del current_state[node_id]
        elif op["op"] == "insert":
            node_id = f"t{op['graph2_node']}"
            if node_id in current_state:
                raise ValueError(f"Insert op error: node {node_id} already exists in current state.")
            current_state[node_id] = op["graph2_label"]

    # Build the target state from the edit operations:
    # For match/substitute, the node remains as "n<i>"; for insert, we use "t<j>".
    target_state = {}
    for op in modifications:
        node_id = f"n{op['graph1_node']}"
        if op["op"] == "match":
            target_state[node_id] = op["label"]
        elif op["op"] == "substitute":
            target_state[node_id] = op["graph2_label"]
    for op in insertions:
        node_id = f"t{op['graph2_node']}"
        target_state[node_id] = op["graph2_label"]

    # Verify that the final state (current_state) has the same multiset of labels as the target state.
    if sorted(list(current_state.values())) != sorted(list(target_state.values())):
        raise ValueError(f"Final state does not match target graph.\nCurrent state: {current_state}\nTarget state: {target_state}")

    return ordered_ops

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

    # Extract raw edit operations in machine-readable format.
    labels1 = data["labels_1"]
    labels2 = data["labels_2"]
    edit_ops = extract_edit_operations(emb1, emb2, labels1, labels2, dummy_cost=DUMMY_COST)

    # Validate and order the edit operations to produce an optimal (sequential) edit path.
    try:
        ordered_edit_ops = validate_and_order_edit_path(edit_ops, labels1, labels2)
    except ValueError as e:
        print("Error during edit path validation:", e)
        sys.exit(1)

    # Convert raw data to torch tensors.
    try:
        torch_data = trainer.transfer_to_torch(data)
    except Exception as e:
        print(f"Skipping pair {JSON_PATH} due to error in transfer_to_torch: {e}")

    # Calculate the graph sizes.
    n1 = len(data["labels_1"])
    n2 = len(data["labels_2"])

    # Compute the prediction using the model.
    trainer.model.eval()
    data = trainer.transfer_to_torch(data)
    prediction = trainer.model(data)
    prediction = -math.log(prediction)

    # Calculate the normalized GED.
    prediction = prediction * (0.5 * (n1 + n2))
    print("Prediction:", prediction)

    # Print the final number of edit operations after ordering.
    final_number_ops = len(ordered_edit_ops)
    print("Final number of edit operations:", final_number_ops)

    # Prepare the results directory.
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f'simgnn_edit_path_pair_{graph_id_1}_{graph_id_2}.json')
    # Write the machine-readable (and validated) edit path as JSON using the custom encoder.
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"edit_path": ordered_edit_ops}, f, indent=2, cls=NumpyEncoder)

    print("Extracted and validated machine-readable edit path saved to:")
    print(output_file)
    # Optionally, also print the JSON to the console.
    print(json.dumps({"edit_path": ordered_edit_ops}, indent=2, cls=NumpyEncoder))

if __name__ == "__main__":
    main()
