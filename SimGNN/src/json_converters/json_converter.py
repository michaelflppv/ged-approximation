#!/usr/bin/env python3
import os
import argparse
import json


def read_edge_list(filename):
    """
    Reads the edge list from AIDS_A.txt.
    Each line is expected to contain two comma-separated integers: (u, v)
    (global node indices, 1-indexed).
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
    Each line corresponds to a node (in global order) and its value is the graph id.
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
    Returns a dictionary mapping graph id to a sorted list of global node ids (1-indexed).
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
    Returns a dictionary mapping graph id to a list of edges (u, v) that belong to that graph.
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
      - labels is a list of node labels (as strings) for the nodes in that graph,
      - edges is a list of edges [u, v] with local indexing (starting at 0).
    """
    global_ids = node_groups[graph_id]
    # Create a mapping from global node id to local index (starting at 0)
    mapping = {gid: i for i, gid in enumerate(global_ids)}
    labels = [str(node_labels[gid - 1]) for gid in global_ids]
    edges = []
    if graph_id in edge_groups:
        for (u, v) in edge_groups[graph_id]:
            if u in mapping and v in mapping:
                edges.append([mapping[u], mapping[v]])
    return labels, edges


def main():
    parser = argparse.ArgumentParser(
        description="Convert AIDS dataset txt files into JSON files (each containing 2 graphs)."
    )
    parser.add_argument("prefix", nargs="?", default="AIDS",
                        help="Prefix for the dataset files (default: 'AIDS')")
    parser.add_argument("--input_dir", default="/home/mfilippov/PycharmProjects/ged-approximation/data/AIDS",
                        help="Directory containing the AIDS txt files (default: data/AIDS)")
    parser.add_argument("--output_dir", default="data/AIDS/json",
                        help="Directory to save the JSON files (default: data/AIDS/json)")
    args = parser.parse_args()

    # Build file paths.
    file_A = os.path.join(args.input_dir, f"{args.prefix}_A.txt")
    file_indicator = os.path.join(args.input_dir, f"{args.prefix}_graph_indicator.txt")
    file_node_labels = os.path.join(args.input_dir, f"{args.prefix}_node_labels.txt")

    # Read input files.
    if not os.path.exists(file_A) or not os.path.exists(file_indicator) or not os.path.exists(file_node_labels):
        print("Error: One or more required files are missing.")
        return

    edges = read_edge_list(file_A)
    indicators = read_graph_indicator(file_indicator)
    node_labels = read_node_labels(file_node_labels)

    # Group nodes and edges by graph id.
    node_groups = group_nodes_by_graph(indicators)
    edge_groups = group_edges_by_graph(edges, indicators)

    # Sort graph ids.
    sorted_graph_ids = sorted(node_groups.keys())
    total_graphs = len(sorted_graph_ids)
    if total_graphs % 2 != 0:
        print("Warning: Odd number of graphs; the last JSON file will contain only one graph.")

    os.makedirs(args.output_dir, exist_ok=True)
    num_pairs = total_graphs // 2
    file_counter = 1
    # Process graphs in pairs.
    for i in range(0, total_graphs - 1, 2):
        graph1_id = sorted_graph_ids[i]
        graph2_id = sorted_graph_ids[i + 1]
        labels_1, graph_1 = process_graph(graph1_id, node_groups, edge_groups, node_labels)
        labels_2, graph_2 = process_graph(graph2_id, node_groups, edge_groups, node_labels)

        # Use a fixed GED value as a placeholder.
        ged_value = 11

        data = {
            "labels_1": labels_1,
            "labels_2": labels_2,
            "graph_2": graph_2,
            "ged": ged_value,
            "graph_1": graph_1
        }

        output_file = os.path.join(args.output_dir, f"pair_{file_counter}.json")
        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(data, out_f, indent=2)
        file_counter += 1

    print(f"Conversion complete. {file_counter - 1} JSON files created in '{args.output_dir}'.")


if __name__ == "__main__":
    main()
