#!/usr/bin/env python3
import os
import argparse
import xml.etree.ElementTree as ET


def read_edge_list(filename):
    """Reads the adjacency list from file."""
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
    """Reads the graph indicator file."""
    with open(filename, "r") as f:
        indicator = [int(line.strip()) for line in f if line.strip()]
    return indicator


def read_graph_labels(filename):
    """Reads the graph labels file."""
    with open(filename, "r") as f:
        labels = [line.strip() for line in f if line.strip()]
    return labels


def read_node_labels(filename):
    """Reads the node labels file."""
    with open(filename, "r") as f:
        labels = [line.strip() for line in f if line.strip()]
    return labels


def read_node_attributes(filename):
    """Reads the node attributes file if it exists."""
    attributes = []
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            attributes.append(parts)
    return attributes


def create_gxl_for_graph_proteins(g_id, node_ids, local_ids, graph_edges,
                                  node_labels, graph_label, node_attributes=None):
    """Creates a GXL XML element for a single graph."""
    gxl = ET.Element("gxl")
    graph_elem = ET.SubElement(gxl, "graph", id=f"G{g_id}", edgeids="true", edgemode="undirected")

    for global_id in node_ids:
        node_elem = ET.SubElement(graph_elem, "node", id=local_ids[global_id])
        label_val = node_labels[global_id - 1]
        attr_label = ET.SubElement(node_elem, "attr", name="label")
        string_label = ET.SubElement(attr_label, "string")
        string_label.text = label_val

        if node_attributes is not None:
            attr_list = node_attributes[global_id - 1]
            for i, val in enumerate(attr_list, start=1):
                attr_node = ET.SubElement(node_elem, "attr", name=f"attr{i}")
                try:
                    float_val = float(val)
                    float_elem = ET.SubElement(attr_node, "float")
                    float_elem.text = str(float_val)
                except ValueError:
                    string_elem = ET.SubElement(attr_node, "string")
                    string_elem.text = val

    if graph_edges is not None:
        for edge_index, (u, v) in enumerate(graph_edges, start=1):
            edge_elem = ET.SubElement(graph_elem, "edge", id=f"e{edge_index}", to=local_ids[v])
            edge_elem.attrib["from"] = local_ids[u]

    return gxl


def write_xml_with_doctype(root, file_path, doctype):
    """Writes the XML tree to file with an XML declaration and the given DOCTYPE."""
    xml_str = ET.tostring(root, encoding="unicode")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0"?>\n')
        f.write(doctype + "\n")
        f.write(xml_str)


def main():
    parser = argparse.ArgumentParser(
        description="Convert PROTEINS dataset text files into GXL graph files and a collection XML file."
    )
    parser.add_argument("prefix", nargs="?", default="PROTEINS",
                        help="Prefix for the dataset files (default: 'PROTEINS')")
    args = parser.parse_args()

    input_dir = "../../../data/PROTEINS/"
    output_dir = "../../../processed_data/gxl/PROTEINS/"
    collection_file = "../../../processed_data/xml/PROTEINS.xml"

    os.makedirs(output_dir, exist_ok=True)

    file_A = os.path.join(input_dir, f"{args.prefix}_A.txt")
    file_graph_indicator = os.path.join(input_dir, f"{args.prefix}_graph_indicator.txt")
    file_graph_labels = os.path.join(input_dir, f"{args.prefix}_graph_labels.txt")
    file_node_labels = os.path.join(input_dir, f"{args.prefix}_node_labels.txt")
    file_node_attributes = os.path.join(input_dir, f"{args.prefix}_node_attributes.txt")

    edges = read_edge_list(file_A)
    graph_indicator = read_graph_indicator(file_graph_indicator)
    graph_labels_list = read_graph_labels(file_graph_labels)
    node_labels = read_node_labels(file_node_labels)

    node_attributes = read_node_attributes(file_node_attributes) if os.path.exists(file_node_attributes) else None

    n_nodes = len(graph_indicator)
    if len(node_labels) != n_nodes:
        print("Error: Mismatch in the number of nodes in node_labels vs graph_indicator.")
        return
    if node_attributes is not None and len(node_attributes) != n_nodes:
        print("Error: Mismatch in the number of nodes in node_attributes vs graph_indicator.")
        return

    graphs = {}
    for i, g in enumerate(graph_indicator, start=1):
        graphs.setdefault(g, []).append(i)

    graph_edges = {}
    for (u, v) in edges:
        g_u = graph_indicator[u - 1]
        g_v = graph_indicator[v - 1]
        if g_u != g_v:
            print(f"Warning: Edge ({u}, {v}) connects nodes from different graphs ({g_u} vs {g_v}). Skipping.")
            continue
        graph_edges.setdefault(g_u, []).append((u, v))

    collection_entries = []
    for g_id, nodes in graphs.items():
        nodes_sorted = sorted(nodes)
        local_ids = {global_id: f"_{i}" for i, global_id in enumerate(nodes_sorted, start=1)}
        gl = graph_labels_list[g_id - 1] if g_id <= len(graph_labels_list) else "unknown"

        edges_for_graph = graph_edges.get(g_id, None)
        gxl_tree = create_gxl_for_graph_proteins(g_id, nodes_sorted, local_ids,
                                                 edges_for_graph, node_labels, gl,
                                                 node_attributes)

        graph_filename = f"graph_{g_id}.gxl"
        graph_filepath = os.path.join(output_dir, graph_filename)
        doctype_gxl = '<!DOCTYPE gxl SYSTEM "http://www.gupro.de/GXL/gxl-1.0.dtd">'
        write_xml_with_doctype(gxl_tree, graph_filepath, doctype_gxl)

        collection_entries.append((graph_filename, gl))

    collection_root = ET.Element("GraphCollection")
    for file_name, class_label in collection_entries:
        ET.SubElement(collection_root, "graph", file=file_name, **{"class": class_label})

    doctype_collection = '<!DOCTYPE GraphCollection SYSTEM "http://www.inf.unibz.it/~blumenthal/dtd/GraphCollection.dtd">'
    write_xml_with_doctype(collection_root, collection_file, doctype_collection)

    print(f"Conversion complete. {len(collection_entries)} graphs written to '{output_dir}'.")
    print(f"Collection file created: '{collection_file}'.")


if __name__ == "__main__":
    main()
