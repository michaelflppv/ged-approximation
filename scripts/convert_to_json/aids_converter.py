#!/usr/bin/env python3
import os
import argparse
import json

# Define the node label mapping (integer → chemical symbol)
# (Originally provided with trailing spaces; we will .strip() them.)
node_label_map = {
    0: "C  ", 1: "O  ", 2: "N  ", 3: "Cl ", 4: "F  ", 5: "S  ", 6: "Se ", 7: "P  ",
    8: "Na ", 9: "I  ", 10: "Co ", 11: "Br ", 12: "Li ", 13: "Si ", 14: "Mg ", 15: "Cu ",
    16: "As ", 17: "B  ", 18: "Pt ", 19: "Ru ", 20: "K  ", 21: "Pd ", 22: "Au ", 23: "Te ",
    24: "W  ", 25: "Rh ", 26: "Zn ", 27: "Bi ", 28: "Pb ", 29: "Ge ", 30: "Sb ", 31: "Sn ",
    32: "Ga ", 33: "Hg ", 34: "Ho ", 35: "Tl ", 36: "Ni ", 37: "Tb "
}

# Compute base directory relative to this script's location.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEFAULT_INPUT_DIR = os.path.join(BASE_DIR, 'data', 'AIDS_re')
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'AIDS_re', 'AIDS')


def read_edge_list(filename):
    """
    Reads the edge list from AIDS_A.txt.
    Each line contains two comma-separated integers (global node IDs, 1-indexed).
    """
    edges = []
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2:
                continue
            try:
                u = int(parts[0].strip())
                v = int(parts[1].strip())
            except ValueError:
                continue
            edges.append((u, v))
    return edges


def read_graph_indicator(filename):
    """
    Reads AIDS_graph_indicator.txt.
    Each line gives the graph id for the corresponding (global) node.
    """
    indicators = []
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    indicators.append(int(line))
                except ValueError:
                    indicators.append(None)
    return indicators


def read_node_labels(filename):
    """
    Reads AIDS_node_labels.txt.
    Each line contains an integer node label.
    """
    labels = []
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    labels.append(int(line))
                except ValueError:
                    labels.append(None)
    return labels


def group_nodes_by_graph(indicators):
    """
    Returns a dict mapping graph id to a sorted list of global node ids (1-indexed).
    """
    groups = {}
    for idx, gid in enumerate(indicators, start=1):
        if gid is None:
            continue
        groups.setdefault(gid, []).append(idx)
    for gid in groups:
        groups[gid] = sorted(groups[gid])
    return groups


def group_edges_by_graph(edges, indicators):
    """
    Returns a dict mapping graph id to a list of edges (u, v) that belong to that graph.
    An edge is assigned if both endpoints have the same graph id.
    """
    groups = {}
    for (u, v) in edges:
        if u - 1 < 0 or u - 1 >= len(indicators) or v - 1 < 0 or v - 1 >= len(indicators):
            continue
        gid_u = indicators[u - 1]
        gid_v = indicators[v - 1]
        if gid_u is None or gid_v is None or gid_u != gid_v:
            continue
        groups.setdefault(gid_u, []).append((u, v))
    return groups


def process_graph(graph_id, node_groups, edge_groups, node_labels):
    """
    For a given graph id, returns a tuple (labels, edges) where:
      - labels is a list of node labels (as chemical symbols, stripped of whitespace)
        for the nodes in that graph,
      - edges is a list of edges [u, v] with local indexing (starting at 0).
    """
    global_ids = node_groups[graph_id]
    mapping = {gid: i for i, gid in enumerate(global_ids)}
    labels = []
    for gid in global_ids:
        raw_label = node_labels[gid - 1]
        # Convert using the mapping and strip trailing spaces.
        labels.append(node_label_map.get(raw_label, str(raw_label)).strip())
    edges = []
    if graph_id in edge_groups:
        for (u, v) in edge_groups[graph_id]:
            if u in mapping and v in mapping:
                edges.append([mapping[u], mapping[v]])
    return labels, edges


def convert_aids_to_json_files(input_dir, prefix, output_dir):
    # Build file paths.
    file_A = os.path.join(input_dir, f"{prefix}_A.txt")
    file_indicator = os.path.join(input_dir, f"{prefix}_graph_indicator.txt")
    file_node_labels = os.path.join(input_dir, f"{prefix}_node_labels.txt")

    # Read required files.
    edges = read_edge_list(file_A)
    indicators = read_graph_indicator(file_indicator)
    node_labels = read_node_labels(file_node_labels)

    # Group nodes and edges by graph.
    node_groups = group_nodes_by_graph(indicators)
    edge_groups = group_edges_by_graph(edges, indicators)

    sorted_graph_ids = sorted(node_groups.keys())
    total_graphs = len(sorted_graph_ids)
    if total_graphs % 2 != 0:
        print("Warning: Odd number of graphs; the last JSON file will contain only one graph.")

    os.makedirs(output_dir, exist_ok=True)
    file_counter = 1
    for i in range(0, total_graphs - 1, 2):
        graph1_id = sorted_graph_ids[i]
        graph2_id = sorted_graph_ids[i + 1]
        labels_1, graph_1 = process_graph(graph1_id, node_groups, edge_groups, node_labels)
        labels_2, graph_2 = process_graph(graph2_id, node_groups, edge_groups, node_labels)

        ged_value = 11  # Placeholder GED value

        data = {
            "labels_1": labels_1,
            "labels_2": labels_2,
            "graph_2": graph_2,
            "ged": ged_value,
            "graph_1": graph_1
        }

        output_file = os.path.join(output_dir, f"pair_{file_counter}.AIDS")
        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(data, out_f, indent=2)
        file_counter += 1

    print(f"Conversion complete. {file_counter - 1} JSON files created in '{output_dir}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Convert AIDS_re dataset txt files into JSON files (each containing 2 graphs) using relative paths."
    )
    parser.add_argument("prefix", nargs="?", default="AIDS_re",
                        help="Prefix for the dataset files (default: 'AIDS_re')")
    parser.add_argument("--input_dir", default=DEFAULT_INPUT_DIR,
                        help=f"Directory containing the AIDS_re txt files (default: {DEFAULT_INPUT_DIR})")
    parser.add_argument("--output_dir", default=DEFAULT_OUTPUT_DIR,
                        help=f"Directory to save the JSON files (default: {DEFAULT_OUTPUT_DIR})")
    args = parser.parse_args()

    convert_aids_to_json_files(args.input_dir, args.prefix, args.output_dir)


if __name__ == "__main__":
    main()
