#!/usr/bin/env python3
import os
import argparse
import xml.etree.ElementTree as ET

# Mapping dictionaries from integer labels to their string values.
node_label_map = {
    0: "C", 1: "O", 2: "N", 3: "Cl", 4: "F", 5: "S", 6: "Se", 7: "P", 8: "Na", 9: "I",
    10: "Co", 11: "Br", 12: "Li", 13: "Si", 14: "Mg", 15: "Cu", 16: "As", 17: "B",
    18: "Pt", 19: "Ru", 20: "K", 21: "Pd", 22: "Au", 23: "Te", 24: "W", 25: "Rh",
    26: "Zn", 27: "Bi", 28: "Pb", 29: "Ge", 30: "Sb", 31: "Sn", 32: "Ga", 33: "Hg",
    34: "Ho", 35: "Tl", 36: "Ni", 37: "Tb"
}

# The edge label in the output will be the integer cost.
edge_label_map = {
    0: 1,
    1: 2,
    2: 3
}

# Graph label mapping: 0 -> "a", 1 -> "i"
graph_label_map = {
    0: "a",
    1: "i"
}


def read_edge_list(filename):
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
    with open(filename, "r") as f:
        labels = [int(line.strip()) for line in f if line.strip()]
    return labels


def read_graph_indicator(filename):
    with open(filename, "r") as f:
        indicator = [int(line.strip()) for line in f if line.strip()]
    return indicator


def read_graph_labels(filename):
    with open(filename, "r") as f:
        labels = [int(line.strip()) for line in f if line.strip()]
    return labels


def read_node_attributes(filename):
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
    with open(filename, "r") as f:
        labels = [int(line.strip()) for line in f if line.strip()]
    return labels


def create_gxl_for_graph(g_id, node_ids, local_ids, graph_edges, node_labels, node_attributes, graph_label):
    gxl = ET.Element("gxl")
    graph_elem = ET.SubElement(gxl, "graph", id=f"molid{g_id}", edgeids="false", edgemode="undirected")

    for global_id in node_ids:
        local_id = local_ids[global_id]
        node_elem = ET.SubElement(graph_elem, "node", id=local_id)
        symbol = node_label_map.get(node_labels[global_id - 1], str(node_labels[global_id - 1]))
        attr_symbol = ET.SubElement(node_elem, "attr", name="symbol")
        string_symbol = ET.SubElement(attr_symbol, "string")
        string_symbol.text = symbol

        attr_names = ["chem", "charge", "x", "y"]
        values = node_attributes[global_id - 1]
        for attr_name, value in zip(attr_names, values):
            attr_elem = ET.SubElement(node_elem, "attr", name=attr_name)
            if attr_name in ["chem", "charge"]:
                int_elem = ET.SubElement(attr_elem, "int")
                try:
                    int_elem.text = str(int(float(value)))
                except Exception:
                    int_elem.text = value
            else:
                float_elem = ET.SubElement(attr_elem, "float")
                try:
                    float_elem.text = str(float(value))
                except Exception:
                    float_elem.text = value

    if graph_edges is not None:
        for (u, v, e_lbl) in graph_edges:
            edge_elem = ET.SubElement(graph_elem, "edge", to=local_ids[v])
            edge_elem.attrib["from"] = local_ids[u]
            attr_edge = ET.SubElement(edge_elem, "attr", name="valence")
            int_edge = ET.SubElement(attr_edge, "int")
            try:
                int_edge.text = str(int(e_lbl))
            except Exception:
                int_edge.text = str(e_lbl)

    return gxl


def write_xml_with_doctype(root, file_path, doctype):
    xml_str = ET.tostring(root, encoding="unicode")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0"?>\n')
        f.write(doctype + "\n")
        f.write(xml_str)


def main():
    parser = argparse.ArgumentParser(
        description="Convert dataset text files into GXL graph files and a collection XML file.")
    parser.add_argument("prefix", nargs="?", default="AIDS",
                        help="Prefix for the dataset files (default: 'AIDS')")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_dir = os.path.join(base_dir, "data", args.prefix)
    output_dir = os.path.join(base_dir, "processed_data", "gxl", args.prefix)
    collection_file = os.path.join(base_dir, "processed_data", "xml", f"{args.prefix}.xml")

    os.makedirs(output_dir, exist_ok=True)

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

    graphs = {}
    for i, g in enumerate(graph_indicator, start=1):
        graphs.setdefault(g, []).append(i)

    graph_edges = {}
    for (u, v), lbl in zip(edges, edge_labels):
        g_u = graph_indicator[u - 1]
        g_v = graph_indicator[v - 1]
        if g_u != g_v:
            print(f"Warning: Edge ({u}, {v}) connects nodes from different graphs ({g_u} vs {g_v}). Skipping.")
            continue
        graph_edges.setdefault(g_u, []).append((u, v, lbl))

    collection_entries = []
    for g_id, nodes in graphs.items():
        nodes_sorted = sorted(nodes)
        local_ids = {global_id: f"_{i}" for i, global_id in enumerate(nodes_sorted, start=1)}
        gl_int = graph_labels_list[g_id - 1]
        gl_str = graph_label_map.get(gl_int, str(gl_int))
        edges_for_graph = graph_edges.get(g_id, None)
        gxl_tree = create_gxl_for_graph(g_id, nodes_sorted, local_ids, edges_for_graph, node_labels, node_attributes,
                                        gl_str)

        graph_filename = f"{g_id}.gxl"
        graph_filepath = os.path.join(output_dir, graph_filename)
        doctype_gxl = '<!DOCTYPE gxl SYSTEM "http://www.gupro.de/GXL/gxl-1.0.dtd">'
        write_xml_with_doctype(gxl_tree, graph_filepath, doctype_gxl)
        collection_entries.append((graph_filename, gl_str))

    collection_root = ET.Element("GraphCollection")
    for file_name, class_label in collection_entries:
        ET.SubElement(collection_root, "graph", file=file_name, **{"class": class_label})

    doctype_collection = '<!DOCTYPE GraphCollection SYSTEM "http://www.inf.unibz.it/~blumenthal/dtd/GraphCollection.dtd">'
    write_xml_with_doctype(collection_root, collection_file, doctype_collection)

    print(f"Conversion complete. {len(collection_entries)} graphs written to '{output_dir}'.")
    print(f"Collection file created: '{collection_file}'.")


if __name__ == "__main__":
    main()
