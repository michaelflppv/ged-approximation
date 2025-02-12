import os
import networkx as nx
import xml.etree.ElementTree as ET
import pandas as pd

# Directories
DATASET_DIR = "./datasets/raw_txt_files/"  # Folder where txt files are stored
GRAPH_DIR = "./datasets/graph_dir/"  # Output directory for GML graphs
COLLECTION_FILE = "./datasets/collection_file.xml"

# Ensure output directory exists
os.makedirs(GRAPH_DIR, exist_ok=True)

# Node Label Mapping
NODE_LABELS = {
    "C": 0, "O": 1, "N": 2, "Cl": 3, "F": 4, "S": 5, "Se": 6, "P": 7, "Na": 8,
    "I": 9, "Co": 10, "Br": 11, "Li": 12, "Si": 13, "Mg": 14, "Cu": 15, "As": 16,
    "B": 17, "Pt": 18, "Ru": 19, "K": 20, "Pd": 21, "Au": 22, "Te": 23, "W": 24,
    "Rh": 25, "Zn": 26, "Bi": 27, "Pb": 28, "Ge": 29, "Sb": 30, "Sn": 31, "Ga": 32,
    "Hg": 33, "Ho": 34, "Tl": 35, "Ni": 36, "Tb": 37
}

# Edge Label Mapping
EDGE_LABELS = {1: 0, 2: 1, 3: 2}

# Class Label Mapping
CLASS_LABELS = {"a": 0, "i": 1}


def load_txt_files(dataset_name):
    """ Load and process dataset TXT files. """
    # File paths
    A_file = os.path.join(DATASET_DIR, f"{dataset_name}_A.txt")
    edge_labels_file = os.path.join(DATASET_DIR, f"{dataset_name}_edge_labels.txt")
    graph_indicator_file = os.path.join(DATASET_DIR, f"{dataset_name}_graph_indicator.txt")
    graph_labels_file = os.path.join(DATASET_DIR, f"{dataset_name}_graph_labels.txt")
    node_labels_file = os.path.join(DATASET_DIR, f"{dataset_name}_node_labels.txt")
    node_attributes_file = os.path.join(DATASET_DIR, f"{dataset_name}_node_attributes.txt")

    # Load data
    A = pd.read_csv(A_file, header=None, delim_whitespace=True) - 1  # Convert to zero-based indexing
    edge_labels = pd.read_csv(edge_labels_file, header=None, delim_whitespace=True)
    graph_indicator = pd.read_csv(graph_indicator_file, header=None, delim_whitespace=True) - 1
    graph_labels = pd.read_csv(graph_labels_file, header=None, delim_whitespace=True)
    node_labels = pd.read_csv(node_labels_file, header=None, delim_whitespace=True)
    node_attributes = pd.read_csv(node_attributes_file, header=None, delim_whitespace=True)

    return A, edge_labels, graph_indicator, graph_labels, node_labels, node_attributes


def build_graphs(dataset_name):
    """ Construct NetworkX graphs and save as GML files. """
    A, edge_labels, graph_indicator, graph_labels, node_labels, node_attributes = load_txt_files(dataset_name)

    graphs = {}

    for node_id, graph_id in enumerate(graph_indicator[0]):
        if graph_id not in graphs:
            graphs[graph_id] = nx.Graph()
            graphs[graph_id].graph['class_label'] = CLASS_LABELS[graph_labels.iloc[graph_id, 0]]

        label = NODE_LABELS.get(node_labels.iloc[node_id, 0], -1)  # Default -1 if not in mapping
        attributes = node_attributes.iloc[node_id].tolist()
        graphs[graph_id].add_node(node_id, label=label, attributes=attributes)

    for (src, dst), label in zip(A.values, edge_labels[0]):
        graph_id = graph_indicator.iloc[src, 0]
        if graph_id in graphs:
            graphs[graph_id].add_edge(src, dst, label=EDGE_LABELS.get(label, -1))

    # Save graphs to GML files
    graph_files = []
    for graph_id, graph in graphs.items():
        graph_file = os.path.join(GRAPH_DIR, f"{dataset_name}_{graph_id}.gml")
        nx.write_gml(graph, graph_file)
        graph_files.append(graph_file)

    return graph_files


def create_collection_file(graph_files):
    """ Generate an XML collection file listing all graphs. """
    root = ET.Element("collection")
    for graph_file in graph_files:
        graph_name = os.path.basename(graph_file)
        ET.SubElement(root, "graph", filename=graph_name)

    tree = ET.ElementTree(root)
    tree.write(COLLECTION_FILE)
    print(f"Collection file saved to: {COLLECTION_FILE}")


if __name__ == "__main__":
    dataset_name = "YOUR_DATASET_NAME"  # Change this to the actual dataset prefix
    print(f"Processing dataset: {dataset_name}")

    graph_files = build_graphs(dataset_name)
    create_collection_file(graph_files)

    print(f"Conversion completed! Graphs saved in {GRAPH_DIR}")
