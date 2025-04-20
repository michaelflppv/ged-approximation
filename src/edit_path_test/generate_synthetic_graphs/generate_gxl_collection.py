#!/usr/bin/env python3
import os
import random
import copy


def generate_base_graph():
    """
    Create a base graph with 4 nodes (chain) and 3 edges.
    Each node has attributes similar to the provided sample.
    """
    graph = {}
    # Base graph identifier (will not be used in output)
    graph["id"] = "base"
    graph["nodes"] = [
        {"id": "n1", "symbol": "C", "chem": 1, "charge": 0, "x": 0.0, "y": 0.0},
        {"id": "n2", "symbol": "C", "chem": 1, "charge": 0, "x": 1.0, "y": 0.0},
        {"id": "n3", "symbol": "C", "chem": 1, "charge": 0, "x": 2.0, "y": 0.0},
        {"id": "n4", "symbol": "C", "chem": 1, "charge": 0, "x": 3.0, "y": 0.0},
    ]
    graph["edges"] = [
        {"from": "n1", "to": "n2"},
        {"from": "n2", "to": "n3"},
        {"from": "n3", "to": "n4"}
    ]
    return graph


def apply_random_modifications(graph, max_mods=5):
    """
    Apply a random number of modifications (0 to max_mods) to a graph.
    Each modification randomly chooses a node and one attribute to change.
    Modification types:
      - Change symbol (from "C" to "O" or "N", etc.)
      - Change charge (toggle 0 to ±1)
      - Change x or y coordinate (add a small offset)

    Since each graph is at most 5 edits away from the base,
    the edit distance between any two graphs is at most 10.
    """
    num_mods = random.randint(0, max_mods)
    for _ in range(num_mods):
        node = random.choice(graph["nodes"])
        attr = random.choice(["symbol", "charge", "x", "y"])
        if attr == "symbol":
            current = node["symbol"]
            if current == "C":
                alternatives = ["O", "N"]
            elif current == "O":
                alternatives = ["C", "N"]
            elif current == "N":
                alternatives = ["C", "O"]
            else:
                alternatives = ["C", "O", "N"]
            node["symbol"] = random.choice(alternatives)
            # Update chem accordingly: C -> 1, O -> 2, N -> 3.
            mapping = {"C": 1, "O": 2, "N": 3}
            node["chem"] = mapping.get(node["symbol"], 1)
        elif attr == "charge":
            current = node["charge"]
            # If current is 0, change to either -1 or 1; otherwise, reset to 0.
            node["charge"] = random.choice([-1, 1]) if current == 0 else 0
        elif attr == "x":
            # Add a small random offset in the range [-0.5, 0.5]
            offset = random.uniform(-0.5, 0.5)
            node["x"] += offset
        elif attr == "y":
            offset = random.uniform(-0.5, 0.5)
            node["y"] += offset


def generate_graph_variant(base_graph):
    """
    Generate a new graph variant by deep copying the base graph.
    Modifications will be applied later.
    """
    return copy.deepcopy(base_graph)


def save_gxl(graph, filename, graph_id):
    """
    Save a graph in GXL format to a file.
    The GXL file includes a DOCTYPE and the structure for nodes and edges.
    """
    with open(filename, "w") as f:
        f.write('<?xml version="1.0"?>\n')
        f.write('<!DOCTYPE gxl SYSTEM "http://www.gupro.de/GXL/gxl-1.0.dtd">\n')
        f.write('<gxl>\n')
        f.write(f'  <graph id="{graph_id}" edgeids="false" edgemode="undirected">\n')
        # Write nodes
        for node in graph["nodes"]:
            f.write(f'    <node id="{node["id"]}">\n')
            f.write(f'      <attr name="symbol"><string>{node["symbol"]}</string></attr>\n')
            f.write(f'      <attr name="chem"><int>{node["chem"]}</int></attr>\n')
            f.write(f'      <attr name="charge"><int>{node["charge"]}</int></attr>\n')
            f.write(f'      <attr name="x"><float>{node["x"]}</float></attr>\n')
            f.write(f'      <attr name="y"><float>{node["y"]}</float></attr>\n')
            f.write('    </node>\n')
        # Write edges
        for edge in graph["edges"]:
            f.write(f'    <edge from="{edge["from"]}" to="{edge["to"]}">\n')
            f.write('      <attr name="valence"><int>0</int></attr>\n')
            f.write('    </edge>\n')
        f.write('  </graph>\n')
        f.write('</gxl>\n')


def save_xml_collection(graph_files, collection_filename):
    """
    Save an XML collection file that references the graph files.
    Each entry includes the file name and a class attribute.
    """
    with open(collection_filename, "w") as f:
        f.write('<?xml version="1.0"?>\n')
        f.write('<!DOCTYPE GraphCollection SYSTEM "http://www.inf.unibz.it/~blumenthal/dtd/GraphCollection.dtd">\n')
        f.write('<GraphCollection>\n')
        for file, cls in graph_files:
            f.write(f'  <graph file="{file}" class="{cls}" />\n')
        f.write('</GraphCollection>\n')


def main():
    random.seed(42)  # For reproducibility
    num_graphs = 100
    output_dir = "../../../processed_data/synthetic_graphs/gxl"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    base_graph = generate_base_graph()
    graph_files_info = []  # List of (filename, class) for the XML collection

    for i in range(1, num_graphs + 1):
        graph_variant = generate_graph_variant(base_graph)
        # Apply up to 5 random modifications so that the edit distance from the base ≤ 5.
        apply_random_modifications(graph_variant, max_mods=5)
        filename = os.path.join(output_dir, f"{i}.gxl")
        graph_id = f"graph{i}"
        save_gxl(graph_variant, filename, graph_id)
        # Randomly assign a class ("a" or "i") as in the example collection.
        cls = random.choice(["a", "i"])
        # In the XML collection, we reference only the file name (without the directory).
        graph_files_info.append((f"{i}.gxl", cls))

    collection_filename = "../../../processed_data/synthetic_graphs/xml/collection.xml"
    save_xml_collection(graph_files_info, collection_filename)
    print(f"Generated {num_graphs} GXL graph files in '{output_dir}' and collection file '{collection_filename}'.")


if __name__ == "__main__":
    main()
