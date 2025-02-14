#!/usr/bin/env python3
"""
proteins_converter.py

This script reads the PROTEINS_re dataset from relative path:
    ../../data/PROTEINS_re
relative to the script location and creates an output folder “AIDS”
in the same PROTEINS_re folder. The dataset is expected to contain the following files:
  - DS_A.txt                : Comma separated edge list (global node IDs) for all graphs.
  - DS_graph_indicator.txt  : One integer per line indicating the graph_id for each node.
  - DS_graph_labels.txt     : (Not used in this script; contains graph labels.)
  - DS_node_labels.txt      : One integer per line indicating the label of each node.
  - DS_node_attributes.txt  : (Not used in this script; contains node attributes.)

For each unordered pair of graphs in the dataset, the script produces a JSON file
with the following structure:
{
    "graph_1": [[0, 1], [1, 2], ...],
    "graph_2": [[0, 1], [1, 2], ...],
    "labels_1": [label0, label1, ...],
    "labels_2": [label0, label1, ...]
}
where the edges are expressed with local node indices (starting from 0) and the
node label lists are ordered by the node’s local index.
"""

import os
import sys
import json
from collections import defaultdict


def main():
    # Determine the directory of this script.
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Build the relative paths.
    # Assumes the following structure:
    #   ged-approximation/
    #       data/PROTEINS_re/          <-- input dataset folder
    #       SimGNN/src/              <-- this script location
    dataset_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "data", "PROTEINS_re"))

    # Check if the input dataset folder exists.
    if not os.path.exists(dataset_dir):
        print(f"Error: Input folder '{dataset_dir}' does not exist.")
        sys.exit(1)

    # Define the required file paths.
    file_A = os.path.join(dataset_dir, "PROTEINS_A.txt")
    file_graph_indicator = os.path.join(dataset_dir, "PROTEINS_graph_indicator.txt")
    file_graph_labels = os.path.join(dataset_dir, "PROTEINS_graph_labels.txt")  # Not used here.
    file_node_labels = os.path.join(dataset_dir, "PROTEINS_node_labels.txt")
    file_node_attributes = os.path.join(dataset_dir, "PROTEINS_node_attributes.txt")  # Not used here.

    # Verify that the essential input files exist.
    for file_path in [file_A, file_graph_indicator, file_node_labels]:
        if not os.path.exists(file_path):
            print(f"Error: Required file '{file_path}' does not exist.")
            sys.exit(1)

    # Prepare the output folder ("AIDS") inside the dataset directory.
    output_dir = os.path.join(dataset_dir, "AIDS")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output folder '{output_dir}'.")

    # --- Step 1. Parse DS_graph_indicator.txt ---
    # Build a mapping from graph_id to the list of global node IDs (1-indexed)
    graph_nodes = defaultdict(list)
    # Also keep a list (indexed by global node id - 1) of each node's graph_id.
    global_indicator = []
    with open(file_graph_indicator, 'r') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                graph_id = int(line)
            except ValueError:
                continue
            global_node_id = i + 1  # Nodes are numbered from 1.
            global_indicator.append(graph_id)
            graph_nodes[graph_id].append(global_node_id)

    # Build a mapping for each graph: global node id -> local node id (0-indexed)
    graph_node_mapping = {}
    for graph_id, nodes in graph_nodes.items():
        mapping = {global_id: idx for idx, global_id in enumerate(nodes)}
        graph_node_mapping[graph_id] = mapping

    # --- Step 2. Parse DS_node_labels.txt ---
    # Read node labels into a list so that node_labels[global_node_id - 1] gives the label.
    node_labels = []
    with open(file_node_labels, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                label = int(line)
            except ValueError:
                try:
                    label = float(line)
                except ValueError:
                    label = line  # Keep as string if neither int nor float.
            node_labels.append(label)

    # --- Step 3. Parse DS_A.txt and build edge lists for each graph ---
    # Each line in DS_A.txt corresponds to an edge (u,v) with global node ids.
    # We convert these to local node indices using the mappings above.
    graph_edges = {graph_id: [] for graph_id in graph_nodes.keys()}
    with open(file_A, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) < 2:
                continue
            try:
                u = int(parts[0])
                v = int(parts[1])
            except ValueError:
                continue

            # Retrieve the graph_id for both nodes (note: global_indicator is 0-indexed).
            if u - 1 >= len(global_indicator) or v - 1 >= len(global_indicator):
                continue
            graph_id_u = global_indicator[u - 1]
            graph_id_v = global_indicator[v - 1]
            if graph_id_u != graph_id_v:
                # If nodes belong to different graphs (should not happen in a block diagonal matrix), skip.
                continue
            graph_id = graph_id_u
            # Convert global node ids to local indices.
            local_u = graph_node_mapping[graph_id][u]
            local_v = graph_node_mapping[graph_id][v]
            graph_edges[graph_id].append([local_u, local_v])

    # --- Step 4. Build local node label lists for each graph ---
    graph_local_node_labels = {}
    for graph_id, nodes in graph_nodes.items():
        # The nodes in 'nodes' are in the order they appeared in DS_graph_indicator.
        labels = [node_labels[global_id - 1] for global_id in nodes]
        graph_local_node_labels[graph_id] = labels

    # --- Step 5. Produce JSON files for every pair of graphs ---
    sorted_graph_ids = sorted(graph_nodes.keys())
    pair_count = 0
    total_pairs = len(sorted_graph_ids) * (len(sorted_graph_ids) - 1) // 2
    print(f"Total graph pairs to process: {total_pairs}")

    for i in range(len(sorted_graph_ids)):
        for j in range(i + 1, len(sorted_graph_ids)):
            if pair_count >= 2000:
                print(f"Reached the limit of 2000 JSON files. Stopping.")
                break
            g1 = sorted_graph_ids[i]
            g2 = sorted_graph_ids[j]
            json_data = {
                "graph_1": graph_edges[g1],
                "graph_2": graph_edges[g2],
                "labels_1": graph_local_node_labels[g1],
                "labels_2": graph_local_node_labels[g2],
            }
            # Name the JSON file according to the pair of graph ids.
            json_filename = f"pair_{g1}_{g2}.AIDS"
            json_filepath = os.path.join(output_dir, json_filename)
            with open(json_filepath, 'w') as json_file:
                json.dump(json_data, json_file)
            pair_count += 1
            # Print progress every 1000 pairs (adjust as needed).
            if pair_count % 1000 == 0:
                print(f"Processed {pair_count}/{total_pairs} pairs...")

        if pair_count >= 2000:
            break

    print(f"Finished processing {pair_count} graph pairs.")


if __name__ == '__main__':
    main()
