#!/usr/bin/env python3
import argparse
import json
import os
import networkx as nx
import matplotlib.pyplot as plt

def load_pair_graph(pair_file):
    """
    Load the graph pair from a JSON file.
    The file is expected to have keys:
      - "graph_1": a list of edges (each a two-element list)
      - "labels_1": a list of node labels (nodes are assumed to be 0-indexed)
    This function returns the query graph (graph_1) as a NetworkX graph.
    """
    with open(pair_file, "r") as f:
        data = json.load(f)
    if "graph_1" not in data or "labels_1" not in data:
        raise ValueError("JSON pair file must contain 'graph_1' and 'labels_1'.")
    edges = data["graph_1"]
    labels = data["labels_1"]
    G = nx.Graph()
    for i, lab in enumerate(labels):
        G.add_node(i, label=lab)
    for edge in edges:
        if isinstance(edge, list) and len(edge) >= 2:
            u, v = edge[0], edge[1]
            G.add_edge(u, v)
    return G

def apply_edit_operation(G, op, next_node_id):
    """
    Apply one edit operation to graph G.

    Parameters:
      G           : A NetworkX graph.
      op          : A dictionary representing one edit operation.
      next_node_id: An integer for the next available node id (for insertions).

    Returns:
      Updated graph G and next_node_id.

    Supported operations:
      - "match": do nothing.
      - "substitute": update an existing node's label.
      - "delete": remove a node.
      - "insert": add a new node with label from "graph2_label".

      Additionally, edge operations are supported.
    """
    op_type = op.get("op", "").lower()
    # --- Node operations ---
    if op_type in ["match", "substitute", "delete"]:
        # These refer to a node in the original query graph.
        node = op.get("graph1_node")
        if node is None:
            return G, next_node_id
        if op_type == "match":
            pass  # no change
        elif op_type == "substitute":
            new_label = op.get("graph2_label")
            if node in G.nodes and new_label is not None:
                G.nodes[node]["label"] = new_label
        elif op_type == "delete":
            if node in G.nodes:
                G.remove_node(node)
    elif op_type == "insert":
        # Insert a new node with a label from the target graph.
        new_label = op.get("graph2_label")
        G.add_node(next_node_id, label=new_label)
        next_node_id += 1
    # --- Edge operations ---
    elif op_type in ["match_edge", "substitute_edge", "delete_edge", "insert_edge"]:
        if op_type in ["match_edge", "substitute_edge", "delete_edge"]:
            edge = op.get("graph1_edge")
        elif op_type == "insert_edge":
            edge = op.get("graph2_edge")
        if not edge or len(edge) < 2:
            return G, next_node_id
        u, v = edge[0], edge[1]
        if op_type == "match_edge":
            pass
        elif op_type == "substitute_edge":
            new_label = op.get("graph2_label")
            if G.has_edge(u, v) and new_label is not None:
                G.edges[u, v]["label"] = new_label
        elif op_type == "delete_edge":
            if G.has_edge(u, v):
                G.remove_edge(u, v)
        elif op_type == "insert_edge":
            if u in G.nodes and v in G.nodes:
                G.add_edge(u, v)
    return G, next_node_id

def update_layout(G, layout):
    """
    Update the layout dictionary with positions for any new nodes added to G.
    Existing node positions remain fixed.
    """
    new_nodes = [n for n in G.nodes if n not in layout]
    if not new_nodes:
        return layout
    # Fix positions for nodes already in the layout.
    fixed_nodes = list(layout.keys())
    # Compute positions for new nodes using spring_layout with fixed positions.
    new_layout = nx.spring_layout(G, pos=layout, fixed=fixed_nodes, seed=42)
    layout.update(new_layout)
    return layout

def visualize_graph(G, title, pos, output_path=None):
    """
    Visualize graph G with node labels using a fixed layout.
    If output_path is provided, the image is saved to that file.
    """
    plt.figure(figsize=(5, 5))
    # Draw nodes and edges without labels.
    nx.draw_networkx_nodes(G, pos, node_color="lightblue", node_size=500)
    nx.draw_networkx_edges(G, pos, edge_color="gray")
    # Draw labels separately to avoid duplicates.
    node_labels = nx.get_node_attributes(G, "label")
    nx.draw_networkx_labels(G, pos, labels=node_labels)
    plt.title(title)
    if output_path:
        plt.savefig(output_path)
    plt.show()
    plt.close()

def main():
    # Specify the graph IDs for the pair of graphs you want to process.
    graph_id_1 = 1000
    graph_id_2 = 1003

    # Specify your file paths here:
    pair_file = '../../processed_data/json_pairs/PROTEINS/pair_{}_{}.json'.format(graph_id_1, graph_id_2)
    edit_path = '../../results/extracted_paths/simgnn_edit_path.json'.format(graph_id_1, graph_id_2)
    output_dir = '../../results/extracted_paths/recreated_graphs/pair_{}_{}'.format(graph_id_1, graph_id_2)
    os.makedirs(output_dir, exist_ok=True)

    # Load the query graph from the JSON pair file.
    try:
        G = load_pair_graph(pair_file)
    except Exception as e:
        print("Error loading query graph:", e)
        return

    # Compute an initial layout for the query graph.
    layout = nx.spring_layout(G, seed=42)

    # Visualize the initial (query) graph.
    step = 0
    initial_img = os.path.join(output_dir, f"graph_{step}_query.png")
    visualize_graph(G, "Query Graph", layout, initial_img)

    # Set next available node id (for insertions).
    next_node_id = max(G.nodes) + 1 if G.nodes else 0

    # Load the edit path JSON.
    with open(edit_path, "r") as f:
        edit_data = json.load(f)
    # The edit operations might be under "edit_operations" or "edit_path"
    edit_ops = edit_data.get("edit_operations") or edit_data.get("edit_path")
    if edit_ops is None:
        print("Error: The edit path JSON must contain an 'edit_operations' or 'edit_path' key.")
        return

    # Apply each edit operation in sequence and visualize the intermediate graph.
    for i, op in enumerate(edit_ops, start=1):
        G, next_node_id = apply_edit_operation(G, op, next_node_id)
        # Update the layout: keep existing positions fixed; compute positions for new nodes.
        layout = update_layout(G, layout)
        title = f"Step {i}: {op.get('op', 'unknown')}"
        img_path = os.path.join(output_dir, f"graph_{i}.png")
        visualize_graph(G, title, layout, img_path)
        print(f"Applied operation {i}: {op}")

    # Optionally, save the final graph structure to a JSON file.
    final_graph = {
        "nodes": [{"id": n, "label": G.nodes[n].get("label")} for n in G.nodes],
        "edges": list(G.edges())
    }
    final_file = os.path.join(output_dir, "final_graph.json")
    with open(final_file, "w") as f:
        json.dump(final_graph, f, indent=4)
    print("Transformation complete. Final graph saved to", final_file)

if __name__ == "__main__":
    main()
