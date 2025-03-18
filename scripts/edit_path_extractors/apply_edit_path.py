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

    Supported operations (by op["op"]):
      - "match": do nothing.
      - "substitute": update an existing node's label (uses "graph1_node" and "graph2_label").
      - "delete": remove a node (specified by "graph1_node").
      - "insert": add a new node with label from "graph2_label".

      - "match_edge": do nothing.
      - "substitute_edge": update an edge attribute (uses "graph1_edge" and "graph2_label").
      - "delete_edge": remove an edge (uses "graph1_edge").
      - "insert_edge": add an edge (uses "graph2_edge").
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


def visualize_graph(G, title, output_path=None):
    """
    Visualize graph G with node labels.
    If output_path is provided, the image is saved to that file.
    """
    plt.figure(figsize=(5, 5))
    pos = nx.spring_layout(G, seed=42)
    node_labels = nx.get_node_attributes(G, "label")
    nx.draw(G, pos, with_labels=True, node_color="lightblue", edge_color="gray", node_size=500)
    nx.draw_networkx_labels(G, pos, labels=node_labels)
    plt.title(title)
    if output_path:
        plt.savefig(output_path)
    plt.show()
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Apply a machine-readable edit path to the query graph (graph_1 from a JSON pair) to simulate its transformation to the target graph."
    )
    parser.add_argument("--pair_file", type=str, required=True,
                        help="Path to the JSON pair file (with 'graph_1' and 'labels_1').")
    parser.add_argument("--edit_path", type=str, required=True,
                        help="Path to the machine-readable edit path JSON file.")
    parser.add_argument("--output_dir", type=str, default="output_graphs",
                        help="Directory to save intermediate graph images.")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Load the query graph from the JSON pair file.
    try:
        G = load_pair_graph(args.pair_file)
    except Exception as e:
        print("Error loading query graph:", e)
        return

    # Visualize the initial (query) graph.
    step = 0
    initial_img = os.path.join(args.output_dir, f"graph_{step}_query.png")
    visualize_graph(G, "Query Graph", initial_img)

    # Set next available node id (for insertions).
    next_node_id = max(G.nodes) + 1 if G.nodes else 0

    # Load the edit path JSON.
    with open(args.edit_path, "r") as f:
        edit_data = json.load(f)
    # The edit operations might be under "edit_operations" or "edit_path"
    edit_ops = edit_data.get("edit_operations") or edit_data.get("edit_path")
    if edit_ops is None:
        print("Error: The edit path JSON must contain an 'edit_operations' or 'edit_path' key.")
        return

    # Apply each edit operation in sequence and visualize the intermediate graph.
    for i, op in enumerate(edit_ops, start=1):
        G, next_node_id = apply_edit_operation(G, op, next_node_id)
        title = f"Step {i}: {op.get('op', 'unknown')}"
        img_path = os.path.join(args.output_dir, f"graph_{i}.png")
        visualize_graph(G, title, img_path)
        print(f"Applied operation {i}: {op}")

    # Optionally, save the final graph structure to a JSON file.
    final_graph = {
        "nodes": [{"id": n, "label": G.nodes[n].get("label")} for n in G.nodes],
        "edges": list(G.edges())
    }
    final_file = os.path.join(args.output_dir, "final_graph.json")
    with open(final_file, "w") as f:
        json.dump(final_graph, f, indent=4)
    print("Transformation complete. Final graph saved to", final_file)


if __name__ == "__main__":
    main()
