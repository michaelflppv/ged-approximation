#!/usr/bin/env python3
import os
import xml.etree.ElementTree as ET
import argparse


def process_gxl_file(filepath, output_dir):
    """
    Convert a single GXL file (representing one graph) into a txt file
    with the following format:

    t # <graph_id>
    v <vertex_id> <vertex_label>
    e <vertex_id1> <vertex_id2> <edge_label>

    For this script we:
      - Use the numeric part of the filename (e.g., graph_4.gxl → "4") as the graph id.
      - Map the GXL node ids to 0-indexed integers.
      - Use the "attr1" attribute (if present) as the vertex label.
      - Assign a constant edge label of 1 (since the GXL edge elements lack a label).
    """
    try:
        tree = ET.parse(filepath)
    except ET.ParseError as e:
        print(f"Error parsing {filepath}: {e}")
        return

    root = tree.getroot()
    # Find the <graph> element. (Assuming one per file.)
    graph_element = root.find('graph')
    if graph_element is None:
        print(f"No <graph> element found in {filepath}")
        return

    # Extract graph id from the filename: "graph_{id}.gxl" → id.
    filename = os.path.basename(filepath)
    try:
        graph_id = filename.split('.')[0].split('_')[-1]
    except IndexError:
        print(f"Filename {filename} does not match expected format 'graph_<id>.gxl'")
        return

    # Create a mapping from the original node id to a new 0-based index.
    node_mapping = {}
    vertex_lines = []

    # Process each node element.
    nodes = graph_element.findall('node')
    for new_id, node in enumerate(nodes):
        orig_id = node.attrib.get('id')
        node_mapping[orig_id] = new_id

        # Prefer using the "attr1" attribute as vertex label.
        vertex_label = None
        for attr in node.findall('attr'):
            if attr.attrib.get('name') == 'attr1':
                float_elem = attr.find('float')
                if float_elem is not None and float_elem.text is not None:
                    try:
                        vertex_label = int(float(float_elem.text))
                    except ValueError:
                        vertex_label = float_elem.text
                break
        # Fallback: if no "attr1", use the "label" attribute.
        if vertex_label is None:
            for attr in node.findall('attr'):
                if attr.attrib.get('name') == 'label':
                    str_elem = attr.find('string')
                    if str_elem is not None and str_elem.text is not None:
                        vertex_label = str_elem.text
                    break
        # If still not found, default to 0.
        if vertex_label is None:
            vertex_label = 0

        vertex_lines.append(f"v {new_id} {vertex_label}")

    # Process edges.
    edge_lines = []
    # Since the GXL graphs are undirected but may list both directions, we use a set to avoid duplicates.
    seen_edges = set()
    edges = graph_element.findall('edge')
    for edge in edges:
        src_orig = edge.attrib.get('from')
        tgt_orig = edge.attrib.get('to')
        if src_orig is None or tgt_orig is None:
            continue

        src = node_mapping.get(src_orig)
        tgt = node_mapping.get(tgt_orig)
        if src is None or tgt is None:
            continue

        # Use a sorted tuple to avoid duplicate undirected edges.
        key = tuple(sorted((src, tgt)))
        if key in seen_edges:
            continue
        seen_edges.add(key)
        # Use a constant edge label (e.g., 1) since GXL edge elements have no label attribute.
        edge_lines.append(f"e {src} {tgt} 1")

    # Prepare the final output content.
    # The header line uses the graph id from the filename.
    out_lines = [f"t # {graph_id}"] + vertex_lines + edge_lines
    output_content = "\n".join(out_lines)

    # Write to an output txt file named "graph_<id>.txt"
    output_filepath = os.path.join(output_dir, f"graph_{graph_id}.txt")
    with open(output_filepath, 'w') as outfile:
        outfile.write(output_content)
    print(f"Processed {filepath} into {output_filepath}")


def main(input_dir, output_dir):
    # Create the output directory if it doesn't exist.
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Process all .gxl files in the input directory.
    for filename in os.listdir(input_dir):
        if filename.endswith('.gxl'):
            filepath = os.path.join(input_dir, filename)
            process_gxl_file(filepath, output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert each GXL graph in a directory to a txt file with format:\n"
                    "t # <graph_id>\n"
                    "v <vertex_id> <vertex_label>\n"
                    "e <vertex_id1> <vertex_id2> <edge_label>"
    )
    parser.add_argument("input_dir", help="Directory containing GXL files")
    parser.add_argument("output_dir", help="Directory to store the resulting txt files")
    args = parser.parse_args()
    main(args.input_dir, args.output_dir)
