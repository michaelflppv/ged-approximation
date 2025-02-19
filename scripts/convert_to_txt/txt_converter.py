#!/usr/bin/env python3
"""
proteins_txt_converter.py

This script reads the PROTEINS dataset from a relative path:
    ../../data/PROTEINS
(relative to this script’s location) and converts the dataset files into
a single text file in the following format:

   t # <graph_label>
   v <local_vertex_id> <vertex_label>
   e <local_vertex_id1> <local_vertex_id2> <edge_label>

Input files (comma separated):
  1. PROTEINS_A.txt                - sparse (block diagonal) adjacency matrix (each line: row,col for an edge)
  2. PROTEINS_graph_indicator.txt  - graph id for each node (line i corresponds to node_id i)
  3. PROTEINS_graph_labels.txt     - class labels for each graph (line i is the label for graph with id i)
  4. PROTEINS_node_labels.txt      - node labels (line i is the label for node_id i)
  5. PROTEINS_node_attributes.txt  - node attributes (not used here)

Output Format Example:
    t # 18
    v 0 6
    v 1 6
    v 2 6
    ...
    e 0 1 1
    e 1 2 1
    ...
    t # 42531
    v 0 6
    v 1 6
    ...
    e 0 1 2
    e 1 2 1
    ...

Note: The "t" line starts a new graph and uses the graph label (from PROTEINS_graph_labels.txt)
as an arbitrary string.
"""

import os
import sys
import json
from collections import defaultdict


def read_lines_strip(filepath):
    with open(filepath, "r") as f:
        return [line.strip() for line in f if line.strip()]


def main():
    # Determine the directory of this script.
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Build relative paths for input and output.
    input_dir = "../../data/PROTEINS/"
    output_dir = "../../processed_data/txt/PROTEINS/"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "PROTEINS.txt")

    # Define input file paths.
    file_A = os.path.join(input_dir, f"PROTEINS_A.txt")
    file_graph_indicator = os.path.join(input_dir, f"PROTEINS_graph_indicator.txt")
    file_graph_labels = os.path.join(input_dir, f"PROTEINS_graph_labels.txt")
    file_node_labels = os.path.join(input_dir, f"PROTEINS_node_labels.txt")
    # DS_node_attributes.txt exists but is not used.

    # Verify required files exist.
    for fp in [file_A, file_graph_indicator, file_graph_labels, file_node_labels]:
        if not os.path.exists(fp):
            print(f"Error: Required file '{fp}' not found.")
            sys.exit(1)

    # Read files.
    # DS_graph_indicator.txt: one graph id per node.
    graph_indicator = [int(x) for x in read_lines_strip(file_graph_indicator)]
    # DS_graph_labels.txt: one graph label per graph; assume graph ids are 1-indexed.
    graph_labels = read_lines_strip(file_graph_labels)
    # DS_node_labels.txt: one label per node.
    node_labels_all = read_lines_strip(file_node_labels)
    # DS_A.txt: each line is "u,v" (global node ids, 1-indexed)
    edges_raw = [line.split(",") for line in read_lines_strip(file_A)]
    edges_raw = [(int(u), int(v)) for u, v in edges_raw if u and v]

    # Build a dictionary mapping graph id -> list of global node ids.
    graph_nodes = defaultdict(list)
    for idx, g in enumerate(graph_indicator):
        # Node ids are 1-indexed in the input.
        node_id = idx + 1
        graph_nodes[g].append(node_id)

    # Build a mapping for each graph: global node id -> local node id (0-indexed).
    graph_node_mapping = {}
    for g, nodes in graph_nodes.items():
        mapping = {global_id: local_id for local_id, global_id in enumerate(nodes)}
        graph_node_mapping[g] = mapping

    # Build per-graph vertex labels.
    # For each graph, for each global node id, get the corresponding node label.
    graph_vertex_labels = {}
    for g, nodes in graph_nodes.items():
        labels = [node_labels_all[node_id - 1] for node_id in nodes]
        graph_vertex_labels[g] = labels

    # Build per-graph edge lists.
    # For each edge (u,v), if both endpoints are in the same graph (by graph_indicator),
    # convert global node ids to local node indices.
    graph_edges = defaultdict(list)
    for u, v in edges_raw:
        # Use graph_indicator (list is 0-indexed; node id u corresponds to index u-1)
        if u - 1 < len(graph_indicator) and v - 1 < len(graph_indicator):
            g_u = graph_indicator[u - 1]
            g_v = graph_indicator[v - 1]
            if g_u == g_v:
                g = g_u
                local_u = graph_node_mapping[g][u]
                local_v = graph_node_mapping[g][v]
                # For this conversion, we set a constant edge label, e.g., "1"
                graph_edges[g].append((local_u, local_v, 1))

    # Now, write the output file.
    with open(output_file, "w") as out_f:
        # Process graphs in sorted order by graph id.
        for g in sorted(graph_nodes.keys()):
            # Get graph label for this graph. Assume DS_graph_labels.txt lines correspond to graph id 1,2,...
            # If not available, use the graph id.
            try:
                graph_label = graph_labels[g - 1]
            except IndexError:
                graph_label = str(g)
            # Write the "t" line.
            out_f.write(f"t # {graph_label}\n")
            # Write vertex lines.
            vertex_labels = graph_vertex_labels[g]
            for local_id, label in enumerate(vertex_labels):
                out_f.write(f"v {local_id} {label}\n")
            # Write edge lines.
            for local_u, local_v, edge_label in graph_edges.get(g, []):
                out_f.write(f"e {local_u} {local_v} {edge_label}\n")

    print(f"Conversion complete. Output written to:\n{output_file}")


if __name__ == "__main__":
    main()
