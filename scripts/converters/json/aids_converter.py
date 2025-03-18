#!/usr/bin/env python3
import os
import argparse
import json

# Define the node label mapping (integer → chemical symbol)
node_label_map = {
    0: "C", 1: "O", 2: "N", 3: "Cl", 4: "F", 5: "S", 6: "Se", 7: "P",
    8: "Na", 9: "I", 10: "Co", 11: "Br", 12: "Li", 13: "Si", 14: "Mg", 15: "Cu",
    16: "As", 17: "B", 18: "Pt", 19: "Ru", 20: "K", 21: "Pd", 22: "Au", 23: "Te",
    24: "W", 25: "Rh", 26: "Zn", 27: "Bi", 28: "Pb", 29: "Ge", 30: "Sb", 31: "Sn",
    32: "Ga", 33: "Hg", 34: "Ho", 35: "Tl", 36: "Ni", 37: "Tb"
}

# Compute base directory relative to this script's location
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_INPUT_DIR = os.path.join(BASE_DIR, "data", "AIDS")
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "processed_data", "json_pairs", "AIDS")


def read_edge_list(filename):
    edges = []
    with open(filename, "r") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 2:
                try:
                    u, v = int(parts[0].strip()), int(parts[1].strip())
                    edges.append((u, v))
                except ValueError:
                    continue
    return edges


def read_graph_indicator(filename):
    indicators = []
    with open(filename, "r") as f:
        for line in f:
            try:
                indicators.append(int(line.strip()))
            except ValueError:
                indicators.append(None)
    return indicators


def read_node_labels(filename):
    labels = []
    with open(filename, "r") as f:
        for line in f:
            try:
                labels.append(int(line.strip()))
            except ValueError:
                labels.append(None)
    return labels


def group_nodes_by_graph(indicators):
    groups = {}
    for idx, gid in enumerate(indicators, start=1):
        if gid is not None:
            groups.setdefault(gid, []).append(idx)
    return {gid: sorted(nodes) for gid, nodes in groups.items()}


def group_edges_by_graph(edges, indicators):
    groups = {}
    for u, v in edges:
        if 0 <= u - 1 < len(indicators) and 0 <= v - 1 < len(indicators):
            gid_u, gid_v = indicators[u - 1], indicators[v - 1]
            if gid_u is not None and gid_v is not None and gid_u == gid_v:
                groups.setdefault(gid_u, []).append((u, v))
    return groups


def process_graph(graph_id, node_groups, edge_groups, node_labels):
    global_ids = node_groups[graph_id]
    mapping = {gid: i for i, gid in enumerate(global_ids)}
    labels = [node_label_map.get(node_labels[gid - 1], str(node_labels[gid - 1])) for gid in global_ids]
    edges = [[mapping[u], mapping[v]] for u, v in edge_groups.get(graph_id, []) if u in mapping and v in mapping]
    return labels, edges


def convert_aids_to_json_files(input_dir, prefix, output_dir):
    # Define input file paths
    file_A = os.path.join(input_dir, f"{prefix}_A.txt")
    file_indicator = os.path.join(input_dir, f"{prefix}_graph_indicator.txt")
    file_node_labels = os.path.join(input_dir, f"{prefix}_node_labels.txt")

    # Read input files
    edges = read_edge_list(file_A)
    indicators = read_graph_indicator(file_indicator)
    node_labels = read_node_labels(file_node_labels)

    # Group data by graphs
    node_groups = group_nodes_by_graph(indicators)
    edge_groups = group_edges_by_graph(edges, indicators)

    sorted_graph_ids = sorted(node_groups.keys())
    total_graphs = len(sorted_graph_ids)

    if total_graphs % 2 != 0:
        print("Warning: Odd number of graphs; the last JSON file will contain only one graph.")

    os.makedirs(output_dir, exist_ok=True)
    file_counter = 1

    for i in range(0, total_graphs - 1, 2):
        g1, g2 = sorted_graph_ids[i], sorted_graph_ids[i + 1]
        labels_1, graph_1 = process_graph(g1, node_groups, edge_groups, node_labels)
        labels_2, graph_2 = process_graph(g2, node_groups, edge_groups, node_labels)

        json_data = {
            "labels_1": labels_1,
            "labels_2": labels_2,
            "graph_1": graph_1,
            "graph_2": graph_2,
            "ged": 11  # Placeholder GED value
        }

        json_filepath = os.path.join(output_dir, f"pair_{file_counter}.json")
        with open(json_filepath, "w", encoding="utf-8") as json_file:
            json.dump(json_data, json_file, indent=2)
        file_counter += 1

    print(f"Conversion complete. {file_counter - 1} JSON files created in '{output_dir}'.")


def main():
    input_dir = r"C:\Users\mikef\PycharmProjects\ged-approximation\data\AIDS"
    prefix = "AIDS"
    output_dir = r"C:\project_data\processed_data\json_pairs\AIDS"

    convert_aids_to_json_files(input_dir, prefix, output_dir)


if __name__ == "__main__":
    main()
