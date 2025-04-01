#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import networkx as nx
import matplotlib.pyplot as plt


def load_gxl_graph(gxl_file):
    """
    Load a GXL graph that has been converted to JSON.
    The file is expected to have keys:
      - "graph_1": a list of edges (each a two-element list)
      - "labels_1": a list of node labels (nodes are assumed to be 0-indexed)
    This function returns the query graph as a NetworkX graph.
    """
    with open(gxl_file, "r") as f:
        data = json.load(f)
    if "graph_1" not in data or "labels_1" not in data:
        raise ValueError("GXL graph file must contain 'graph_1' and 'labels_1'.")
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


def get_edit_path(executable, dataset_path, collection_xml, idx1, idx2, output_file):
    """
    Call the external executable (produced by your C++ code) to compute the edit path.
    The command-line arguments are passed to the executable; its JSON output is parsed
    and saved to output_file.
    """
    command = [
        executable,
        dataset_path,
        collection_xml,
        str(idx1),
        str(idx2)
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("Error running executable:", e)
        print("stderr:", e.stderr)
        return None
    try:
        output_json = json.loads(result.stdout)
    except Exception as e:
        print("Error parsing JSON output:", e)
        print("Output was:", result.stdout)
        return None
    # Save the JSON output for future reference.
    with open(output_file, "w") as f:
        json.dump(output_json, f, indent=4)
    print(f"Edit path results saved to {output_file}")
    return output_json


def apply_edit_operation(G, op, next_node_id):
    """
    Apply one edit operation to graph G.

    Supported operations (only those explicitly provided in the JSON edit path are applied):
      - Node operations:
          "match": no change.
          "substitute": update an existing node's label.
          "delete": remove a node.
          "insert": add a new node with label from "graph2_label".
      - Edge operations:
          "match_edge": no change.
          "substitute_edge": update an edge's label.
          "delete_edge": remove an edge.
          "insert_edge": add an edge.
    """
    op_type = op.get("op", "").lower()
    # --- Node operations ---
    if op_type in ["match", "substitute", "delete"]:
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
    fixed_nodes = list(layout.keys())
    new_layout = nx.spring_layout(G, pos=layout, fixed=fixed_nodes, seed=42)
    layout.update(new_layout)
    return layout


def visualize_graph(G, title, pos, output_path=None):
    """
    Visualize graph G with node labels using a fixed layout.
    If output_path is provided, the image is saved to that file.
    """
    plt.figure(figsize=(5, 5))
    nx.draw_networkx_nodes(G, pos, node_color="lightblue", node_size=500)
    nx.draw_networkx_edges(G, pos, edge_color="gray")
    node_labels = nx.get_node_attributes(G, "label")
    nx.draw_networkx_labels(G, pos, labels=node_labels)
    plt.title(title)
    if output_path:
        plt.savefig(output_path)
    plt.show()
    plt.close()


def main():
    # --- Parameters ---
    dataset = "PROTEINS"
    dataset_path = "/home/mfilippov/ged_data/processed_data/gxl/PROTEINS"  # Update as needed
    collection_xml = "/home/mfilippov/ged_data/processed_data/xml/PROTEINS.xml"  # Update as needed
    idx1 = 1000  # Query graph index
    idx2 = 1003  # Target graph index
    executable = "/home/mfilippov/CLionProjects/gedlib/build/edit_path_exec"  # Update with your executable's path
    output_file = r"C:\project_data\results\extracted_paths\ipfp_PROTEINS_edit_path_for_1000_1003.json"

    # Load the query graph from a GXL-converted JSON file.
    gxl_query_file = r"C:\project_data\processed_data\gxl_pairs\PROTEINS\graph_1000.json"  # Update as needed
    try:
        G = load_gxl_graph(gxl_query_file)
    except Exception as e:
        print("Error loading query graph from GXL:", e)
        return

    # Compute an initial layout.
    layout = nx.spring_layout(G, seed=42)
    output_dir = r"C:\project_data\results\extracted_paths\recreated_graphs\PROTEINS\graph_1000_1003"
    os.makedirs(output_dir, exist_ok=True)
    step = 0
    initial_img = os.path.join(output_dir, f"graph_{step}_query.png")
    visualize_graph(G, "Query Graph", layout, initial_img)

    next_node_id = max(G.nodes) + 1 if G.nodes else 0

    # Get the edit path JSON from the external executable.
    edit_path_json = get_edit_path(executable, dataset_path, collection_xml, idx1, idx2, output_file)
    if edit_path_json is None:
        print("Failed to retrieve edit path.")
        return

    # The edit operations may be stored under "edit_operations" or "edit_path".
    edit_ops = edit_path_json.get("edit_operations") or edit_path_json.get("edit_path")
    if edit_ops is None:
        print("Edit path JSON does not contain edit operations.")
        return

    # Apply each edit operation in sequence.
    for i, op in enumerate(edit_ops, start=1):
        G, next_node_id = apply_edit_operation(G, op, next_node_id)
        layout = update_layout(G, layout)
        title = f"Step {i}: {op.get('op', 'unknown')}"
        img_path = os.path.join(output_dir, f"graph_{i}.png")
        visualize_graph(G, title, layout, img_path)
        print(f"Applied operation {i}: {op}")

    # Save the final graph structure.
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
