import os
import sys
import json
import math
import random
import numpy as np
from scipy.optimize import linear_sum_assignment
from torch.serialization import safe_globals
from torch.nn.parameter import UninitializedParameter

from param_parser import parameter_parser
from simgnn import SimGNNTrainer
from utils import process_pair

# File and directory constants
JSON_DIR = r"C:\project_data\processed_data\json_pairs\IMDB-BINARY"
MODEL_PATH = r"C:\Users\mikef\PycharmProjects\ged-approximation\SimGNN\models\simgnn_model.h5"
DUMMY_COST = 1.0

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

def process_pair_json(json_path, trainer):
    # Load data from json file
    data = process_pair(json_path)
    labels1 = data["labels_1"]
    labels2 = data["labels_2"]
    emb1, emb2 = get_node_embeddings(trainer, data)
    edit_ops = extract_edit_operations(emb1, emb2, labels1, labels2, dummy_cost=DUMMY_COST)
    ordered_edit_ops = validate_and_order_edit_path(edit_ops, labels1, labels2)
    final_number_ops = len(ordered_edit_ops)
    # Compute prediction using model
    torch_data = trainer.transfer_to_torch(data)
    trainer.model.eval()
    prediction = trainer.model(torch_data)
    prediction = -math.log(prediction)
    prediction = prediction * (0.5 * (len(labels1) + len(labels2)))
    return final_number_ops, prediction

def main():
    simgnn_args = parameter_parser()
    trainer = load_model(simgnn_args)
    total_samples = 3
    pairs_per_sample = 2000
    # For each sample, count how many pairs satisfy the prediction match condition.
    for sample in range(total_samples):
        count_match = 0
        processed = 0
        for _ in range(pairs_per_sample):
            # Randomly select two graph indices (0 to 999)
            g1 = random.randint(0, 999)
            g2 = random.randint(0, 999)
            json_file = os.path.join(JSON_DIR, f"pair_{g1}_{g2}.json")
            if not os.path.exists(json_file):
                continue
            try:
                final_ops, prediction = process_pair_json(json_file, trainer)
                processed += 1
                # Check if prediction and final number of operations match within 5%
                if abs(final_ops - prediction) / final_ops <= 0.3:
                    count_match += 1
            except Exception as e:
                # Skip pairs that raise errors
                continue
        print(f"Sample {sample + 1}: Processed {processed} pairs, {count_match} pairs match within 30% uncertainty.")

if __name__ == "__main__":
    main()