#!/usr/bin/env python3
import subprocess
import json
import os
import random
import xml.etree.ElementTree as ET

# ---------------- Constants ----------------
# Adjust these paths as needed. For instance, if you generated 100 graphs, use a max_index of 99.
DATASET_PATH = "../../../processed_data/synthetic_graphs/gxl"  # folder containing generated GXL files
COLLECTION_XML = "../../../processed_data/synthetic_graphs/xml/collection.xml"
EXECUTABLE = "../../../gedlib/build/edit_path_exec"  # path to the executable
MAX_INDEX = 99  # if 100 graphs exist, indices 0 to 99 are used
TOLERANCE = 0.05  # 5% tolerance

# -------------- Helper Functions --------------

def load_gxl(file_path):
    """
    Parses a GXL file and returns a list of nodes.
    Each node is represented as a dictionary with keys: symbol, charge, x, y.
    Expects a structure like:
      <gxl>
        <graph ...>
          <node id="n1">
            <attr name="symbol"><string>C</string></attr>
            <attr name="charge"><int>0</int></attr>
            <attr name="x"><float>0.0</float></attr>
            <attr name="y"><float>0.0</float></attr>
          </node>
          ...
        </graph>
      </gxl>
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        graph_elem = root.find('graph')
        if graph_elem is None:
            raise ValueError("No <graph> element found in " + file_path)
        nodes = []
        for node in graph_elem.findall('node'):
            # For each node, extract attributes from the children <attr> elements.
            node_data = {}
            for attr in node.findall('attr'):
                attr_name = attr.attrib.get('name')
                # Use the first child element (e.g., <string>, <int>, or <float>)
                for child in attr:
                    if child.tag == 'string':
                        node_data[attr_name] = child.text
                    elif child.tag == 'int':
                        node_data[attr_name] = int(child.text)
                    elif child.tag == 'float':
                        node_data[attr_name] = float(child.text)
            nodes.append((node.attrib.get("id"), node_data))
        # Sort nodes by their id (assuming id format such as "n1", "n2", …)
        nodes.sort(key=lambda tup: tup[0])
        # Return only the node attribute dictionaries in sorted order.
        return [nd[1] for nd in nodes]
    except Exception as e:
        print("Error parsing GXL file {}: {}".format(file_path, e))
        return None

def compute_true_ged(idx1, idx2, dataset_path):
    """
    Compute the true graph edit distance (GED) between two GXL graphs generated from the same base.
    For these generated graphs only node attribute modifications are expected.
    Compare the nodes' attributes: 'symbol', 'charge', 'x', and 'y'.
    The GED is computed as the sum of all differences over corresponding nodes.
    """
    # Files are named "1.gxl", "2.gxl", … so add 1 to the indices.
    file1 = os.path.join(dataset_path, f"{idx1+1}.gxl")
    file2 = os.path.join(dataset_path, f"{idx2+1}.gxl")
    nodes1 = load_gxl(file1)
    nodes2 = load_gxl(file2)
    if nodes1 is None or nodes2 is None:
        return None
    if len(nodes1) != len(nodes2):
        print("Graphs have different number of nodes:", file1, file2)
        return None
    attributes = ["symbol", "charge", "x", "y"]
    ged = 0
    for n1, n2 in zip(nodes1, nodes2):
        for attr in attributes:
            # If either attribute is missing or the values differ, count an edit.
            if n1.get(attr) != n2.get(attr):
                ged += 1
    return ged

def check_values(output, true_ged):
    """
    Compare the 'edit_operations_count' returned by the executable
    with the true GED computed from the GXL files.
    For true_ged == 0 an exact match is required.
    Otherwise, the difference must be within TOLERANCE.
    """
    try:
        edit_op = output["edit_operations_count"]
        if true_ged == 0:
            return edit_op == 0
        return abs(edit_op - true_ged) <= TOLERANCE * abs(true_ged)
    except KeyError:
        print("Required keys missing in output:", output)
        return False

def is_exact_match(output, true_ged):
    """
    Check if the edit operations count exactly matches the true GED
    """
    try:
        edit_op = output["edit_operations_count"]
        return edit_op == true_ged
    except KeyError:
        return False

def run_executable(dataset_path, collection_xml, idx1, idx2, executable):
    """
    Runs the external executable with the given parameters (dataset_path, collection_xml, idx1, idx2)
    and returns the parsed JSON output.
    """
    command = [
        executable,
        dataset_path,
        collection_xml,
        str(idx1),
        str(idx2),
        "IPFP"
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("Error running executable for indices {} and {}:".format(idx1, idx2), e)
        print("stderr:", e.stderr)
        return None

    try:
        output_json = json.loads(result.stdout)
        return output_json
    except Exception as e:
        print("Error parsing JSON output for indices {} and {}:".format(idx1, idx2), e)
        print("Output was:", result.stdout)
        return None

# ---------------- Main Script ----------------

def main():
    total_pairs = 0
    valid_pairs = 0
    invalid_pairs = 0
    within_tolerance_count = 0
    exact_match_count = 0
    total_diff = 0.0  # Sum of absolute differences between edit_operations_count and true GED

    # Iterate over all unique pairs: indices 0 to MAX_INDEX (inclusive)
    for idx1 in range(0, MAX_INDEX + 1):
        for idx2 in range(idx1 + 1, MAX_INDEX + 1):
            total_pairs += 1
            # Run the executable to get its reported edit operations count
            output = run_executable(DATASET_PATH, COLLECTION_XML, idx1, idx2, EXECUTABLE)
            if output is None:
                invalid_pairs += 1
                continue
            # Compute the true GED by comparing the two GXL files
            true_ged = compute_true_ged(idx1, idx2, DATASET_PATH)
            if true_ged is None:
                invalid_pairs += 1
                continue

            # Count the pair as valid (processed) regardless of match
            valid_pairs += 1

            diff = abs(output["edit_operations_count"] - true_ged)
            total_diff += diff

            # Check if within tolerance
            if check_values(output, true_ged):
                within_tolerance_count += 1

            # Check if exact match
            if is_exact_match(output, true_ged):
                exact_match_count += 1

    # Compute overall statistics
    if valid_pairs > 0:
        avg_diff = total_diff / valid_pairs
        optimal_percentage = 100.0 * within_tolerance_count / valid_pairs
        exact_match_percentage = 100.0 * exact_match_count / valid_pairs
    else:
        avg_diff = 0.0
        optimal_percentage = 0.0
        exact_match_percentage = 0.0

    print("\n=== Overall Statistics ===")
    print(f"Total pairs processed: {total_pairs}")
    print(f"Valid pairs (processed without errors): {valid_pairs}")
    print(f"Invalid pairs (errors during processing): {invalid_pairs}")
    print(f"Pairs within {TOLERANCE*100}% tolerance: {within_tolerance_count}")
    print(f"Pairs with exact GED match (truly optimal): {exact_match_count}")
    print(f"Optimality percentage (within tolerance): {optimal_percentage:.2f}%")
    print(f"Exact match percentage (truly optimal): {exact_match_percentage:.2f}%")
    print(f"Average absolute difference between edit_operations_count and true GED: {avg_diff:.2f}")

if __name__ == "__main__":
    main()