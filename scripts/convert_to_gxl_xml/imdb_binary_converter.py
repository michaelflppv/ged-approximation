#!/usr/bin/env python3
import os
import argparse
import xml.etree.ElementTree as ET


def read_edge_list(filename):
    """
    Read the sparse adjacency list from file.
    Each line is expected to contain two comma-separated integers: (node_id, node_id).
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
    Read the graph indicator file.
    Each line corresponds to a node (by its id) and its value is the graph id.
    """
    with open(filename, "r") as f:
        indicator = [int(line.strip()) for line in f if line.strip()]
    return indicator


def read_graph_labels(filename):
    """
    Read graph labels from file (one label per line).
    If the labels are numeric, they are converted to int.
    """
    with open(filename, "r") as f:
        labels = [line.strip() for line in f if line.strip()]
    try:
        labels = [int(x) for x in labels]
    except ValueError:
        pass
    return labels


def create_gxl_for_graph_imdb(g_id, node_ids, local_ids, graph_edges, graph_label):
    """
    Create a GXL XML element for a single graph.
      - g_id: the graph identifier (integer)
      - node_ids: sorted list of global node ids (1-indexed) belonging to this graph
      - local_ids: mapping from global node id to a local id (e.g. "_1", "_2", ...)
      - graph_edges: list of edges (u, v) for this graph; if None, no edges are added
      - graph_label: the label for the graph (as read from file)

    For IMDB‑BINARY, no node attributes are provided so each node is given a default label "0".
    Also, we do not include any graph‑level <attr> element.
    """
    # Create the root <gxl> element.
    gxl = ET.Element("gxl")
    # Create the <graph> element.
    # Note: we use id="molid<g_id>" and set edgeids="false", edgemode="undirected" to match examples.
    graph_elem = ET.SubElement(gxl, "graph", id=f"molid{g_id}", edgeids="false", edgemode="undirected")

    # (Do not add a graph-level <attr> element here.)

    # Add nodes (each gets a default label "0").
    for global_id in node_ids:
        node_elem = ET.SubElement(graph_elem, "node", id=local_ids[global_id])
        attr_label = ET.SubElement(node_elem, "attr", name="label")
        string_label = ET.SubElement(attr_label, "string")
        string_label.text = "0"

    # Add edges.
    if graph_edges is not None:
        for edge_index, (u, v) in enumerate(graph_edges, start=1):
            edge_elem = ET.SubElement(graph_elem, "edge", id=f"e{edge_index}", to=local_ids[v])
            edge_elem.attrib["from"] = local_ids[u]

    return gxl


def write_xml_with_doctype(root, file_path, doctype):
    """
    Write the XML tree to file with an XML declaration and the given DOCTYPE.
    """
    xml_str = ET.tostring(root, encoding="unicode")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0"?>\n')
        f.write(doctype + "\n")
        f.write(xml_str)


def main():
    parser = argparse.ArgumentParser(
        description="Convert IMDB-BINARY_re dataset text files into GXL graph files and a collection XML file."
    )
    # Default prefix is "IMDB-BINARY_re"
    parser.add_argument("prefix", nargs="?", default="IMDB-BINARY_re",
                        help="Prefix for the dataset files (default: 'IMDB-BINARY_re')")
    parser.add_argument("--output_dir", default="data/IMDB-BINARY_re/AIDS",
                        help="Output directory for GXL files (default: data/IMDB-BINARY_re/AIDS)")
    parser.add_argument("--collection_file", default="data/IMDB-BINARY_re/AIDS/AIDS_re.xml",
                        help="Output collection XML file (default: data/IMDB-BINARY_re/AIDS/AIDS_re.xml)")
    args = parser.parse_args()

    # Define input directory (adjust as needed).
    input_dir = os.path.join("../../data", "IMDB-BINARY_re")
    file_A = os.path.join(input_dir, f"{args.prefix}_A.txt")
    file_graph_indicator = os.path.join(input_dir, f"{args.prefix}_graph_indicator.txt")
    file_graph_labels = os.path.join(input_dir, f"{args.prefix}_graph_labels.txt")

    # Read input files.
    edges = read_edge_list(file_A)
    graph_indicator = read_graph_indicator(file_graph_indicator)
    graph_labels_list = read_graph_labels(file_graph_labels)

    # Group nodes by graph.
    graphs = {}  # key: graph id, value: list of global node ids (1-indexed)
    for i, g in enumerate(graph_indicator, start=1):
        graphs.setdefault(g, []).append(i)

    # Group edges by graph.
    graph_edges = {}
    for (u, v) in edges:
        g_u = graph_indicator[u - 1]
        g_v = graph_indicator[v - 1]
        if g_u != g_v:
            print(f"Warning: Edge ({u}, {v}) connects nodes from different graphs ({g_u} vs {g_v}). Skipping.")
            continue
        graph_edges.setdefault(g_u, []).append((u, v))

    os.makedirs(args.output_dir, exist_ok=True)
    collection_entries = []

    # Process each graph.
    for g_id, nodes in graphs.items():
        nodes_sorted = sorted(nodes)
        # Create a mapping from global node id to a local id using an underscore (e.g., "_1", "_2", …)
        local_ids = {global_id: f"_{i}" for i, global_id in enumerate(nodes_sorted, start=1)}
        # Get the graph label.
        if g_id <= len(graph_labels_list):
            gl = graph_labels_list[g_id - 1]
        else:
            gl = "unknown"
        edges_for_graph = graph_edges.get(g_id, None)
        gxl_tree = create_gxl_for_graph_imdb(g_id, nodes_sorted, local_ids, edges_for_graph, gl)
        # Generate a filename – here we use "<g_id>.gxl"
        graph_filename = f"{g_id}.gxl"
        graph_filepath = os.path.join(args.output_dir, graph_filename)
        doctype_gxl = '<!DOCTYPE gxl SYSTEM "http://www.gupro.de/GXL/gxl-1.0.dtd">'
        write_xml_with_doctype(gxl_tree, graph_filepath, doctype_gxl)
        # In the collection XML we record the relative filename and the graph label (as class).
        collection_entries.append((graph_filename, str(gl)))

    # Create the collection XML.
    collection_root = ET.Element("GraphCollection")
    for file_name, class_label in collection_entries:
        ET.SubElement(collection_root, "graph", file=file_name, **{"class": class_label})
    collection_filepath = args.collection_file
    doctype_collection = '<!DOCTYPE GraphCollection SYSTEM "http://www.inf.unibz.it/~blumenthal/dtd/GraphCollection.dtd">'
    write_xml_with_doctype(collection_root, collection_filepath, doctype_collection)

    print(f"Conversion complete. {len(collection_entries)} graphs written to '{args.output_dir}'.")
    print(f"Collection file created: '{collection_filepath}'.")


if __name__ == "__main__":
    main()