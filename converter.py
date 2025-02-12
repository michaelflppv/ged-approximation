#!/usr/bin/env python3
import os
import argparse
import xml.etree.ElementTree as ET

# Mapping dictionaries from integer labels to their string values
node_label_map = {
    0: "C", 1: "O", 2: "N", 3: "Cl", 4: "F", 5: "S", 6: "Se", 7: "P", 8: "Na", 9: "I",
    10: "Co", 11: "Br", 12: "Li", 13: "Si", 14: "Mg", 15: "Cu", 16: "As", 17: "B",
    18: "Pt", 19: "Ru", 20: "K", 21: "Pd", 22: "Au", 23: "Te", 24: "W", 25: "Rh",
    26: "Zn", 27: "Bi", 28: "Pb", 29: "Ge", 30: "Sb", 31: "Sn", 32: "Ga", 33: "Hg",
    34: "Ho", 35: "Tl", 36: "Ni", 37: "Tb"
}

edge_label_map = {
    0: "1",
    1: "2",
    2: "3"
}

graph_label_map = {
    0: "a",
    1: "i"
}


def read_edge_list(filename):
    """Read edge list from a file where each line is 'number, number'."""
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
    """Read edge labels (one integer per line)."""
    with open(filename, "r") as f:
        labels = [int(line.strip()) for line in f if line.strip()]
    return labels


def read_graph_indicator(filename):
    """Read graph indicator file; each line indicates which graph the corresponding node belongs to."""
    with open(filename, "r") as f:
        indicator = [int(line.strip()) for line in f if line.strip()]
    return indicator


def read_graph_labels(filename):
    """Read graph labels (one integer per line)."""
    with open(filename, "r") as f:
        labels = [int(line.strip()) for line in f if line.strip()]
    return labels


def read_node_attributes(filename):
    """
    Read node attributes from file.
    Each line is expected to contain 4 comma-separated values corresponding to [chem, charge, x, y].
    """
    attributes = []
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            attributes.append(parts)
    return attributes


def read_node_labels(filename):
    """Read node labels (one integer per line)."""
    with open(filename, "r") as f:
        labels = [int(line.strip()) for line in f if line.strip()]
    return labels


def create_gxl_for_graph(g_id, node_ids, local_ids, graph_edges, node_labels, node_attributes, graph_label):
    """
    Create an ElementTree XML element for a single graph in GXL format.
      - g_id: graph identifier (an integer)
      - node_ids: sorted list of global node IDs in this graph
      - local_ids: mapping of global node id -> local id string (e.g. "n1")
      - graph_edges: list of edges for this graph; each edge is a tuple (u, v, edge_label)
      - node_labels: full list of node labels (indexed by global id - 1)
      - node_attributes: full list of node attributes (indexed by global id - 1)
      - graph_label: the label for the graph (a string)
    """
    gxl = ET.Element("gxl")
    graph_elem = ET.SubElement(gxl, "graph", id=f"G{g_id}", edgeids="true", edgemode="undirected")

    # Add graph label as an attribute to the graph element.
    attr_elem = ET.SubElement(graph_elem, "attr", name="graph_label")
    string_elem = ET.SubElement(attr_elem, "string")
    string_elem.text = graph_label

    # Add node elements.
    for global_id in node_ids:
        node_elem = ET.SubElement(graph_elem, "node", id=local_ids[global_id])
        label_int = node_labels[global_id - 1]
        label_str = node_label_map.get(label_int, str(label_int))
        attr_label = ET.SubElement(node_elem, "attr", name="label")
        string_label = ET.SubElement(attr_label, "string")
        string_label.text = label_str

        attributes = node_attributes[global_id - 1]
        attr_names = ["chem_attr", "charge", "x", "y"]
        for name, value in zip(attr_names, attributes):
            attr_node = ET.SubElement(node_elem, "attr", name=name)
            if name == "chem_attr":
                string_attr = ET.SubElement(attr_node, "string")
                string_attr.text = value
            else:
                try:
                    float_val = float(value)
                    float_elem = ET.SubElement(attr_node, "float")
                    float_elem.text = str(float_val)
                except ValueError:
                    string_attr = ET.SubElement(attr_node, "string")
                    string_attr.text = value

    # Add edge elements.
    if graph_edges is not None:
        for edge_index, (u, v, e_lbl) in enumerate(graph_edges, start=1):
            edge_elem = ET.SubElement(graph_elem, "edge", id=f"e{edge_index}", to=local_ids[v])
            edge_elem.attrib["from"] = local_ids[u]
            edge_label_str = edge_label_map.get(e_lbl, str(e_lbl))
            attr_edge = ET.SubElement(edge_elem, "attr", name="label")
            string_edge = ET.SubElement(attr_edge, "string")
            string_edge.text = edge_label_str

    return gxl


def main():
    parser = argparse.ArgumentParser(
        description="Convert dataset text files into GXL graph files and a collection XML file."
    )
    # The prefix argument is now optional and defaults to "AIDS"
    parser.add_argument("prefix", nargs="?", default="AIDS",
                        help="Prefix for the dataset files (default: 'AIDS')")
    parser.add_argument("--output_dir", default="data/AIDS/results",
                        help="Output directory for GXL files (default: data/AIDS/results)")
    parser.add_argument("--collection_file", default="data/AIDS/results/collection.xml",
                        help="Output collection XML file (default: data/AIDS/results/collection.xml)")
    args = parser.parse_args()

    input_dir = os.path.join("data", "AIDS")

    # Construct file names using the prefix "AIDS" (or override via command-line)
    file_A = os.path.join(input_dir, f"{args.prefix}_A.txt")
    file_edge_labels = os.path.join(input_dir, f"{args.prefix}_edge_labels.txt")
    file_graph_indicator = os.path.join(input_dir, f"{args.prefix}_graph_indicator.txt")
    file_graph_labels = os.path.join(input_dir, f"{args.prefix}_graph_labels.txt")
    file_node_attributes = os.path.join(input_dir, f"{args.prefix}_node_attributes.txt")
    file_node_labels = os.path.join(input_dir, f"{args.prefix}_node_labels.txt")

    edges = read_edge_list(file_A)
    edge_labels = read_edge_labels(file_edge_labels)
    graph_indicator = read_graph_indicator(file_graph_indicator)
    graph_labels_list = read_graph_labels(file_graph_labels)
    node_attributes = read_node_attributes(file_node_attributes)
    node_labels = read_node_labels(file_node_labels)

    n_nodes = len(graph_indicator)
    if not (len(node_attributes) == n_nodes and len(node_labels) == n_nodes):
        print("Error: Mismatch in the number of nodes across the input files.")
        return

    # Group nodes by graph.
    graphs = {}
    for i, g in enumerate(graph_indicator, start=1):
        graphs.setdefault(g, []).append(i)

    # Group edges by graph.
    graph_edges = {}
    for (u, v), lbl in zip(edges, edge_labels):
        g_u = graph_indicator[u - 1]
        g_v = graph_indicator[v - 1]
        if g_u != g_v:
            print(f"Warning: Edge ({u}, {v}) connects nodes from different graphs ({g_u} vs {g_v}). Skipping.")
            continue
        graph_edges.setdefault(g_u, []).append((u, v, lbl))

    os.makedirs(args.output_dir, exist_ok=True)
    collection_graphs = []

    for g_id, nodes in graphs.items():
        nodes_sorted = sorted(nodes)
        local_ids = {global_id: f"n{local_index}" for local_index, global_id in enumerate(nodes_sorted, start=1)}

        if g_id <= len(graph_labels_list):
            gl_int = graph_labels_list[g_id - 1]
            gl_str = graph_label_map.get(gl_int, str(gl_int))
        else:
            gl_str = "unknown"

        edges_for_graph = graph_edges.get(g_id, None)
        gxl_tree = create_gxl_for_graph(g_id, nodes_sorted, local_ids, edges_for_graph,
                                        node_labels, node_attributes, gl_str)

        graph_filename = f"graph_{g_id}.gxl"
        graph_filepath = os.path.join(args.output_dir, graph_filename)
        ET.ElementTree(gxl_tree).write(graph_filepath, encoding="utf-8", xml_declaration=True)
        collection_graphs.append(graph_filepath)

    collection_root = ET.Element("graphcollection")
    for gfile in collection_graphs:
        ET.SubElement(collection_root, "graph", file=gfile)
    ET.ElementTree(collection_root).write(args.collection_file, encoding="utf-8", xml_declaration=True)

    print(f"Conversion complete. {len(collection_graphs)} graphs written to '{args.output_dir}'.")
    print(f"Collection file created: '{args.collection_file}'.")


if __name__ == "__main__":
    main()
