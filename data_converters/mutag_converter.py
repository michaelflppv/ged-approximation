#!/usr/bin/env python3
import os
import argparse
import xml.etree.ElementTree as ET

# Mapping dictionaries for MUTAG.
node_label_map = {
    0: "C",
    1: "N",
    2: "O",
    3: "F",
    4: "I",
    5: "Cl",
    6: "Br"
}

edge_label_map = {
    0: "aromatic",
    1: "single",
    2: "double",
    3: "triple"
}

# For graph labels, many MUTAG versions use -1 and 1.
graph_label_map = {
    -1: "non-mutagenic",
    1: "mutagenic"
}


def read_edge_list(filename):
    """
    Read the sparse adjacency list from file.
    Each line is expected to contain two comma-separated integers: (row, col).
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


def read_edge_labels(filename):
    """
    Read edge labels from file (one integer per line).
    """
    with open(filename, "r") as f:
        labels = [int(line.strip()) for line in f if line.strip()]
    return labels


def read_graph_indicator(filename):
    """
    Read the graph indicator file.
    Each line corresponds to a node (by its id) and the integer value is the graph id.
    """
    with open(filename, "r") as f:
        indicator = [int(line.strip()) for line in f if line.strip()]
    return indicator


def read_graph_labels(filename):
    """
    Read graph labels from file (one integer per line).
    """
    with open(filename, "r") as f:
        labels = [int(line.strip()) for line in f if line.strip()]
    return labels


def read_node_labels(filename):
    """
    Read node labels from file (one integer per line).
    """
    with open(filename, "r") as f:
        labels = [int(line.strip()) for line in f if line.strip()]
    return labels


def create_gxl_for_graph_mutag(g_id, node_ids, local_ids, graph_edges, node_labels, graph_label):
    """
    Create an XML Element (GXL format) for a single graph.
      - g_id: graph id (integer)
      - node_ids: list of global node ids (1-indexed) belonging to the graph.
      - local_ids: mapping from global node id to local id (e.g. "n1", "n2", ...)
      - graph_edges: list of tuples (u, v, edge_label) for this graph; if edge_label is None,
                     the edge label attribute will be omitted.
      - node_labels: full list of node labels (indexed by global node id - 1)
      - graph_label: the label for the graph as a string.
    """
    gxl = ET.Element("gxl")
    graph_elem = ET.SubElement(gxl, "graph", id=f"G{g_id}", edgeids="true", edgemode="undirected")

    # Add the graph label as an attribute.
    attr_elem = ET.SubElement(graph_elem, "attr", name="graph_label")
    string_elem = ET.SubElement(attr_elem, "string")
    string_elem.text = graph_label

    # Add nodes.
    for global_id in node_ids:
        node_elem = ET.SubElement(graph_elem, "node", id=local_ids[global_id])
        label_int = node_labels[global_id - 1]
        label_str = node_label_map.get(label_int, str(label_int))
        attr_label = ET.SubElement(node_elem, "attr", name="label")
        string_label = ET.SubElement(attr_label, "string")
        string_label.text = label_str

    # Add edges.
    if graph_edges is not None:
        for edge_index, (u, v, e_lbl) in enumerate(graph_edges, start=1):
            edge_elem = ET.SubElement(graph_elem, "edge", id=f"e{edge_index}", to=local_ids[v])
            edge_elem.attrib["from"] = local_ids[u]
            # Only add an edge label attribute if one is available.
            if e_lbl is not None:
                edge_label_str = edge_label_map.get(e_lbl, str(e_lbl))
                attr_edge = ET.SubElement(edge_elem, "attr", name="label")
                string_edge = ET.SubElement(attr_edge, "string")
                string_edge.text = edge_label_str

    return gxl


def main():
    parser = argparse.ArgumentParser(
        description="Convert MUTAG dataset text files into GXL graph files and a collection XML file."
    )
    # The prefix defaults to "MUTAG" (can be overridden if needed)
    parser.add_argument("prefix", nargs="?", default="MUTAG",
                        help="Prefix for the dataset files (default: 'MUTAG')")
    parser.add_argument("--output_dir", default="data/MUTAG/results",
                        help="Output directory for GXL files (default: data/MUTAG/results)")
    parser.add_argument("--collection_file", default="data/MUTAG/results/collection.xml",
                        help="Output collection XML file (default: data/MUTAG/results/collection.xml)")
    args = parser.parse_args()

    # Input directory is data/MUTAG.
    input_dir = os.path.join("../data", "MUTAG")

    # Construct file paths.
    file_A = os.path.join(input_dir, f"{args.prefix}_A.txt")
    file_graph_indicator = os.path.join(input_dir, f"{args.prefix}_graph_indicator.txt")
    file_graph_labels = os.path.join(input_dir, f"{args.prefix}_graph_labels.txt")
    file_node_labels = os.path.join(input_dir, f"{args.prefix}_node_labels.txt")
    file_edge_labels = os.path.join(input_dir, f"{args.prefix}_edge_labels.txt")

    # Read required files.
    edges = read_edge_list(file_A)
    graph_indicator = read_graph_indicator(file_graph_indicator)
    graph_labels_list = read_graph_labels(file_graph_labels)
    node_labels = read_node_labels(file_node_labels)

    # Determine if the optional edge labels file exists.
    if os.path.exists(file_edge_labels):
        edge_labels = read_edge_labels(file_edge_labels)
        if len(edge_labels) != len(edges):
            print("Warning: The number of edge labels does not match the number of edges.")
    else:
        edge_labels = None

    n_nodes = len(graph_indicator)
    # Group nodes by graph id.
    graphs = {}  # key: graph id, value: list of global node ids (1-indexed)
    for i, g in enumerate(graph_indicator, start=1):
        graphs.setdefault(g, []).append(i)

    # Group edges by graph id.
    # For each edge from (u, v) (and optionally an edge label), assign it to the graph
    # indicated by the endpoints (they should belong to the same graph).
    graph_edges = {}
    # If edge labels are available, pair them with the edges; otherwise assign None.
    if edge_labels is not None:
        edge_iterable = zip(edges, edge_labels)
    else:
        # Create a dummy iterable where every edge gets a None label.
        edge_iterable = ((edge, None) for edge in edges)

    for (u, v), lbl in edge_iterable:
        g_u = graph_indicator[u - 1]
        g_v = graph_indicator[v - 1]
        if g_u != g_v:
            print(f"Warning: Edge ({u}, {v}) connects nodes from different graphs ({g_u} vs {g_v}). Skipping.")
            continue
        graph_edges.setdefault(g_u, []).append((u, v, lbl))

    # Create the output directory.
    os.makedirs(args.output_dir, exist_ok=True)
    collection_graphs = []

    # Process each graph.
    for g_id, nodes in graphs.items():
        nodes_sorted = sorted(nodes)
        # Create a mapping from global node id to local node id.
        local_ids = {global_id: f"n{local_index}" for local_index, global_id in enumerate(nodes_sorted, start=1)}

        # Get the graph label.
        if g_id <= len(graph_labels_list):
            gl_int = graph_labels_list[g_id - 1]
            gl_str = graph_label_map.get(gl_int, str(gl_int))
        else:
            gl_str = "unknown"

        # Get edges for this graph.
        edges_for_graph = graph_edges.get(g_id, None)

        # Create the GXL element.
        gxl_tree = create_gxl_for_graph_mutag(g_id, nodes_sorted, local_ids, edges_for_graph,
                                              node_labels, gl_str)

        # Write the GXL file.
        graph_filename = f"graph_{g_id}.gxl"
        graph_filepath = os.path.join(args.output_dir, graph_filename)
        ET.ElementTree(gxl_tree).write(graph_filepath, encoding="utf-8", xml_declaration=True)
        collection_graphs.append(graph_filepath)

    # Create the collection XML file.
    collection_root = ET.Element("graphcollection")
    for gfile in collection_graphs:
        ET.SubElement(collection_root, "graph", file=gfile)
    ET.ElementTree(collection_root).write(args.collection_file, encoding="utf-8", xml_declaration=True)

    print(f"Conversion complete. {len(collection_graphs)} graphs written to '{args.output_dir}'.")
    print(f"Collection file created: '{args.collection_file}'.")


if __name__ == "__main__":
    main()
