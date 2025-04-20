import os
import sys
import json
import math
import random
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from torch.serialization import safe_globals
from torch.nn.parameter import UninitializedParameter

from param_parser import parameter_parser
from simgnn import SimGNNTrainer
from utils import process_pair

# File and directory constants
JSON_DIR = "../../processed_data/json_pairs/PROTEINS"
MODEL_PATH = "../models/simgnn_model.h5"
EXCEL_PATH = "../../results/exact_ged/PROTEINS/results.xlsx"  # Path to the Excel file with min_ged values
DUMMY_COST = 1.0
THRESHOLD = 0.05  # 5% tolerance

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
    simgnn_args.load_path = MODEL_PATH
    trainer = SimGNNTrainer(simgnn_args)
    with safe_globals([UninitializedParameter]):
        trainer.load()
    return trainer

def get_node_embeddings(trainer, data):
    data_torch = trainer.transfer_to_torch(data)
    emb1 = trainer.model.convolutional_pass(data_torch["edge_index_1"], data_torch["features_1"])
    emb2 = trainer.model.convolutional_pass(data_torch["edge_index_2"], data_torch["features_2"])
    return emb1, emb2

def pad_cost_matrix(cost_matrix, n_rows, n_cols, dummy_cost):
    n = max(n_rows, n_cols)
    padded = np.full((n, n), dummy_cost)
    padded[:n_rows, :n_cols] = cost_matrix
    return padded

def extract_edit_operations(emb1, emb2, labels1, labels2, dummy_cost=1.0):
    emb1_np = emb1.detach().cpu().numpy()
    emb2_np = emb2.detach().cpu().numpy()
    n1 = emb1_np.shape[0]
    n2 = emb2_np.shape[0]
    cost_matrix = np.linalg.norm(emb1_np[:, None, :] - emb2_np[None, :, :], axis=2)
    padded_cost = pad_cost_matrix(cost_matrix, n1, n2, dummy_cost)
    row_ind, col_ind = linear_sum_assignment(padded_cost)
    edit_operations = []
    for i, j in zip(row_ind, col_ind):
        if i < n1 and j < n2:
            if labels1[i] == labels2[j]:
                op = {"op": "match", "graph1_node": int(i), "graph2_node": int(j), "label": labels1[i]}
            else:
                op = {"op": "substitute", "graph1_node": int(i), "graph1_label": labels1[i],
                      "graph2_node": int(j), "graph2_label": labels2[j]}
            edit_operations.append(op)
        elif i < n1 and j >= n2:
            op = {"op": "delete", "graph1_node": int(i), "graph1_label": labels1[i]}
            edit_operations.append(op)
        elif i >= n1 and j < n2:
            op = {"op": "insert", "graph2_node": int(j), "graph2_label": labels2[j]}
            edit_operations.append(op)
    return edit_operations

def validate_and_order_edit_path(edit_ops, labels1, labels2):
    modifications = []
    deletions = []
    insertions = []
    for op in edit_ops:
        if op["op"] in ["match", "substitute"]:
            modifications.append(op)
        elif op["op"] == "delete":
            deletions.append(op)
        elif op["op"] == "insert":
            insertions.append(op)
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
    # Validate the edit path by simulating the modifications on graph1
    current_state = {f"n{i}": labels1[i] for i in range(len(labels1))}
    for op in ordered_ops:
        if op["op"] == "match":
            node_id = f"n{op['graph1_node']}"
            if node_id not in current_state or current_state[node_id] != op["label"]:
                raise ValueError(f"Match op error at node {node_id}.")
        elif op["op"] == "substitute":
            node_id = f"n{op['graph1_node']}"
            if node_id not in current_state:
                raise ValueError(f"Substitute op error at node {node_id}.")
            current_state[node_id] = op["graph2_label"]
        elif op["op"] == "delete":
            node_id = f"n{op['graph1_node']}"
            if node_id not in current_state:
                raise ValueError(f"Delete op error at node {node_id}.")
            del current_state[node_id]
        elif op["op"] == "insert":
            node_id = f"t{op['graph2_node']}"
            if node_id in current_state:
                raise ValueError(f"Insert op error at node {node_id}.")
            current_state[node_id] = op["graph2_label"]
    # Build the target state from the edit operations (as recorded by matches/substitutions and insertions)
    target_state = {}
    for op in modifications:
        node_id = f"n{op['graph1_node']}"
        target_state[node_id] = op.get("label", op.get("graph2_label"))
    for op in insertions:
        node_id = f"t{op['graph2_node']}"
        target_state[node_id] = op["graph2_label"]
    if sorted(list(current_state.values())) != sorted(list(target_state.values())):
        raise ValueError("Final state does not match target state.")
    return ordered_ops

def load_exact_ged_data():
    """
    Load the exact GED values from the Excel file
    """
    try:
        df = pd.read_excel(EXCEL_PATH)
        # Create a dictionary with pair keys and min_ged values
        ged_dict = {}
        for _, row in df.iterrows():
            g1 = int(row['graph_id_1'])
            g2 = int(row['graph_id_2'])
            if g1 > g2:  # Ensure consistent ordering
                g1, g2 = g2, g1
            pair_key = f"{g1}_{g2}"
            ged_dict[pair_key] = int(row['min_ged'])
        return ged_dict
    except Exception as e:
        print(f"Error loading exact GED data from Excel: {e}")
        return {}

def process_pair_json(json_path, trainer, exact_ged_dict):
    # Extract graph indices from filename
    filename = os.path.basename(json_path)
    g1, g2 = map(int, filename.replace("pair_", "").replace(".json", "").split('_'))
    pair_key = f"{g1}_{g2}"

    # Load data from json file
    data = process_pair(json_path)
    labels1 = data["labels_1"]
    labels2 = data["labels_2"]
    emb1, emb2 = get_node_embeddings(trainer, data)
    edit_ops = extract_edit_operations(emb1, emb2, labels1, labels2, dummy_cost=DUMMY_COST)
    # Validate and order the edit path (will raise an error if invalid)
    ordered_edit_ops = validate_and_order_edit_path(edit_ops, labels1, labels2)
    final_number_ops = len(ordered_edit_ops)

    # Use the exact GED from Excel file instead of JSON
    true_ged = exact_ged_dict.get(pair_key)
    if true_ged is None:
        # Fallback to JSON value if not found in Excel
        true_ged = data["ged"]
        #print(f"Warning: Exact GED not found in Excel for pair {pair_key}, using JSON value: {true_ged}")

    return final_number_ops, true_ged

def main():
    simgnn_args = parameter_parser()
    trainer = load_model(simgnn_args)

    # Load exact GED values from Excel
    exact_ged_dict = load_exact_ged_data()
    print(f"Loaded {len(exact_ged_dict)} exact GED values from Excel")

    # Statistics counters
    total_pairs = 0
    valid_pairs = 0
    invalid_pairs = 0
    optimal_pairs = 0
    exact_match_pairs = 0
    total_diff = 0.0

    # Target total number of valid pairs to process
    target_valid_pairs = 5000
    total_samples = 3
    pairs_per_sample = target_valid_pairs // total_samples

    # For each sample, pick pairs from the JSON directory until we reach the target
    for sample in range(total_samples):
        sample_processed = 0
        sample_valid = 0
        sample_optimal = 0
        sample_exact = 0
        sample_total_diff = 0.0
        attempts = 0
        max_attempts = pairs_per_sample * 10  # Safety limit to prevent infinite loops

        while sample_valid < pairs_per_sample and attempts < max_attempts:
            attempts += 1
            # Randomly select two graph indices (from 0 to 99)
            g1 = random.randint(0, 99)
            g2 = random.randint(0, 99)
            # Ensure g1 < g2 to match generation of unique pairs
            if g1 >= g2:
                continue

            # Create pair key to check if it exists in our exact GED dictionary
            pair_key = f"{g1}_{g2}"
            if pair_key not in exact_ged_dict:
                # Skip pairs that don't have exact GED values in Excel
                continue

            json_file = os.path.join(JSON_DIR, f"pair_{g1}_{g2}.json")
            if not os.path.exists(json_file):
                continue

            total_pairs += 1
            sample_processed += 1

            try:
                final_ops, true_ged = process_pair_json(json_file, trainer, exact_ged_dict)
                # If we reached here, the edit path is valid.
                valid_pairs += 1
                sample_valid += 1
                diff = abs(final_ops - true_ged)
                sample_total_diff += diff
                total_diff += diff

                # Check exact match (truly optimal)
                if final_ops == true_ged:
                    exact_match_pairs += 1
                    sample_exact += 1

                # Check optimality: if the edit path cost is within THRESHOLD tolerance of true GED.
                if final_ops == 0:
                    is_optimal = (true_ged == 0)
                else:
                    is_optimal = (diff / final_ops <= THRESHOLD)
                if is_optimal:
                    optimal_pairs += 1
                    sample_optimal += 1
            except Exception as e:
                # If an error is raised, the edit path is invalid.
                invalid_pairs += 1
                continue

        # Print sample-level statistics
        if sample_valid > 0:
            avg_diff_sample = sample_total_diff / sample_valid
            exact_percentage_sample = 100.0 * sample_exact / sample_valid
        else:
            avg_diff_sample = float('nan')
            exact_percentage_sample = 0.0

        print(f"Sample {sample + 1}: Processed {sample_processed} pairs; "
              f"Valid: {sample_valid}; Invalid: {sample_processed - sample_valid}; "
              f"Optimal (within {THRESHOLD*100:.1f}%): {sample_optimal}; "
              f"Exactly Optimal: {sample_exact} ({exact_percentage_sample:.2f}%); "
              f"Average absolute difference: {avg_diff_sample:.2f}")

        # Check if we've reached the overall target
        if valid_pairs >= target_valid_pairs:
            break

    # Print overall statistics
    if valid_pairs > 0:
        avg_diff = total_diff / valid_pairs
        optimal_percentage = 100.0 * optimal_pairs / valid_pairs
        exact_match_percentage = 100.0 * exact_match_pairs / valid_pairs
    else:
        avg_diff = float('nan')
        optimal_percentage = 0.0
        exact_match_percentage = 0.0

    print("\n=== Overall Statistics ===")
    print(f"Total pairs processed: {total_pairs}")
    print(f"Valid edit paths: {valid_pairs} (target: {target_valid_pairs})")
    print(f"Invalid edit paths: {invalid_pairs}")
    print(f"Optimal edit paths (within {THRESHOLD*100:.1f}% tolerance): {optimal_pairs}")
    print(f"Optimality percentage (among valid pairs): {optimal_percentage:.2f}%")
    print(f"Truly optimal edit paths (exact GED match): {exact_match_pairs}")
    print(f"Truly optimal percentage (among valid pairs): {exact_match_percentage:.2f}%")
    print(f"Average absolute difference between edit path cost and true GED: {avg_diff:.2f}")
if __name__ == "__main__":
    main()