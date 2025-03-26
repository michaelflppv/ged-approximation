#!/usr/bin/env python3
import os
import argparse
import xml.etree.ElementTree as ET

from torch_geometric.datasets import TUDataset


def create_gxl_for_graph_imdb(g_id, node_ids, local_ids, graph_edges, graph_label):
    """
    Create a GXL XML element for a single graph.

    Parameters:
      - g_id: integer id for the graph.
      - node_ids: list of node indices (local to the graph).
      - local_ids: dictionary mapping node id -> local string id (e.g. "_1")
      - graph_edges: list of tuples (u, v) representing undirected edges.
      - graph_label: the class label for the graph.

    Returns:
      - An ElementTree Element representing the GXL graph.
    """
    gxl = ET.Element("gxl")
    # The graph is marked as undirected and no edge IDs are needed.
    graph_elem = ET.SubElement(gxl, "graph", id=f"molid{g_id}", edgeids="false", edgemode="undirected")

    # Add nodes. Every node is given a default label "1".
    for node_id in node_ids:
        node_elem = ET.SubElement(graph_elem, "node", id=local_ids[node_id])
        attr_label = ET.SubElement(node_elem, "attr", name="label")
        string_label = ET.SubElement(attr_label, "string")
        string_label.text = "1"

    # Add edges. Here we now add an attribute for the edge label (constant "1")
    if graph_edges is not None:
        for edge_index, (u, v) in enumerate(graph_edges, start=1):
            edge_elem = ET.SubElement(graph_elem, "edge", id=f"e{edge_index}", to=local_ids[v])
            edge_elem.attrib["from"] = local_ids[u]
            # Add a constant edge label attribute "valence" with value "1"
            attr_edge = ET.SubElement(edge_elem, "attr", name="valence")
            int_edge = ET.SubElement(attr_edge, "int")
            int_edge.text = "1"

    return gxl


def write_xml_with_doctype(root, file_path, doctype):
    """
    Write an XML tree to a file with an XML declaration and the given DOCTYPE.
    """
    xml_str = ET.tostring(root, encoding="unicode")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0"?>\n')
        f.write(doctype + "\n")
        f.write(xml_str)


def main():
    parser = argparse.ArgumentParser(
        description="Convert IMDB-BINARY from PyTorch Geometric into GXL graph files and an XML collection file."
    )
    parser.add_argument("--tud_root", type=str, default="../../../data/ged",
                        help="Root directory for downloading/saving the TUDataset (default: ./data)")
    parser.add_argument("--output_dir", type=str, default="/mnt/c/project_data/processed_data/IMDB-BINARY/gxl",
                        help="Output directory for GXL files (default: gxl/IMDB-BINARY)")
    parser.add_argument("--collection_file", type=str, default="/mnt/c/project_data/processed_data/IMDB-BINARY/xml/IMDB-BINARY.xml",
                        help="Output XML collection file (default: IMDB-BINARY.xml)")
    args = parser.parse_args()

    # Load the IMDB-BINARY dataset using PyTorch Geometric.
    dataset = TUDataset(root=args.tud_root, name="IMDB-BINARY", use_node_attr=False)

    os.makedirs(args.output_dir, exist_ok=True)

    collection_entries = []
    doctype_gxl = '<!DOCTYPE gxl SYSTEM "http://www.gupro.de/GXL/gxl-1.0.dtd">'

    # Process each graph in the dataset.
    for idx, data in enumerate(dataset, start=1):
        g_id = idx
        num_nodes = data.num_nodes
        # Create a list of node indices (0-indexed within each graph)
        node_ids = list(range(num_nodes))
        # Create local ids mapping: node index -> string like "_1", "_2", ...
        local_ids = {node_id: f"_{node_id + 1}" for node_id in node_ids}

        # Process edge_index to obtain a list of undirected edges without duplicates.
        # data.edge_index is a tensor of shape [2, num_edges].
        edge_index = data.edge_index.tolist()
        edges = []
        for u, v in zip(edge_index[0], edge_index[1]):
            # Since the graphs are undirected, only keep one ordering.
            if u < v:
                edges.append((u, v))

        # Get the graph label (data.y is typically a tensor with one element).
        graph_label = int(data.y.item()) if data.y.dim() > 0 else int(data.y)

        # Create GXL XML tree for the graph.
        gxl_tree = create_gxl_for_graph_imdb(g_id, node_ids, local_ids, edges, graph_label)

        # Write the GXL file.
        graph_filename = f"{g_id}.gxl"
        graph_filepath = os.path.join(args.output_dir, graph_filename)
        write_xml_with_doctype(gxl_tree, graph_filepath, doctype_gxl)

        # Append collection entry using the graph label.
        collection_entries.append((graph_filename, str(graph_label)))

    # Create the XML collection file.
    collection_root = ET.Element("GraphCollection")
    for file_name, class_label in collection_entries:
        ET.SubElement(collection_root, "graph", file=file_name, **{"class": class_label})

    doctype_collection = '<!DOCTYPE GraphCollection SYSTEM "http://www.inf.unibz.it/~blumenthal/dtd/GraphCollection.dtd">'
    write_xml_with_doctype(collection_root, args.collection_file, doctype_collection)

    print(f"Conversion complete. {len(collection_entries)} graphs written to '{args.output_dir}'.")
    print(f"Collection file created: '{args.collection_file}'.")


if __name__ == "__main__":
    main()
