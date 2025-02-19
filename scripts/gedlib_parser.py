#!/usr/bin/env python3
"""
This script runs the GEDLIB executable and captures its output,
then parses that output and writes the results to an Excel file.
It includes extensive debug output and error checking.
"""

import os
import subprocess
import re
import pandas as pd
import tempfile
import xml.etree.ElementTree as ET
import platform

# Define relative paths (adjust these relative paths as needed)
script_dir = os.path.dirname(os.path.abspath(__file__))

GED_EXECUTABLE = os.path.join(script_dir, "../gedlib/build/main_exec")  # Ensure this path is correct
DATASET_PATH = os.path.join(script_dir, "../processed_data/gxl/PROTEINS")
COLLECTION_XML = os.path.join(script_dir, "../processed_data/xml/PROTEINS.xml")
RESULTS_DIR = os.path.join(script_dir, "../results/gedlib")
RESULTS_FILE = os.path.join(RESULTS_DIR, "PROTEINS_IPFP_results.xlsx")

# Update method mapping according to new C++ enum values (adjust as needed)
METHOD_NAMES = {
    0: "F2",
    20: "STAR (Exact)",
    10: "IPFP",
    11: "BIPARTITE",
    16: "REFINE",
}

# Conditional import for resource module
if platform.system() != "Windows":
    import resource


def preprocess_xml_file(xml_path):
    """Remove DOCTYPE declarations from the XML file and return path to a temporary file."""
    try:
        with open(xml_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading XML file '{xml_path}': {e}")
        raise

    filtered_lines = [line for line in lines if not line.lstrip().startswith("<!DOCTYPE")]
    temp_fd, temp_path = tempfile.mkstemp(suffix=".xml")
    with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
        f.writelines(filtered_lines)
    return temp_path


def get_graph_properties(gxl_file):
    """
    Parse the GXL file to compute:
      - number of nodes (n)
      - number of edges (e)
      - density (p) = 2*e/(n*(n-1)) for undirected graphs (if n>1)
    """
    try:
        temp_path = preprocess_xml_file(gxl_file)
        tree = ET.parse(temp_path)
        os.remove(temp_path)
    except Exception as e:
        print(f"Error parsing {gxl_file}: {e}")
        return None, None, None

    root = tree.getroot()
    graph_elem = root.find('graph')
    if graph_elem is None:
        print(f"No <graph> element found in {gxl_file}.")
        return None, None, None
    nodes = graph_elem.findall('node')
    edges = graph_elem.findall('edge')
    n = len(nodes)
    e = len(edges)
    p = (2 * e) / (n * (n - 1)) if n > 1 else 0
    return n, e, p


def get_first_two_graph_properties(dataset_path, collection_xml):
    """
    Parse the collection XML (after removing DOCTYPE) to get the first two graph file names,
    then compute and return their (n, e, p) properties.
    """
    try:
        temp_xml = preprocess_xml_file(collection_xml)
        tree = ET.parse(temp_xml)
        os.remove(temp_xml)
    except Exception as e:
        print(f"Error parsing collection XML: {e}")
        return None, None

    root = tree.getroot()
    graphs = root.findall('graph')
    if len(graphs) < 2:
        print("Not enough graphs found in collection XML.")
        return None, None
    file1 = graphs[0].get('file')
    file2 = graphs[1].get('file')
    if not file1 or not file2:
        print("Graph file names missing in collection XML.")
        return None, None
    path1 = os.path.join(dataset_path, file1)
    path2 = os.path.join(dataset_path, file2)
    props1 = get_graph_properties(path1)
    props2 = get_graph_properties(path2)
    return props1, props2


def run_ged(dataset_path, collection_xml):
    """Run the GEDLIB executable and parse its output, while collecting additional metrics."""
    try:
        preprocessed_xml = preprocess_xml_file(collection_xml)
    except Exception as e:
        print("Failed to preprocess collection XML:", e)
        return [{"error": "Preprocessing XML failed"}]

    command = [GED_EXECUTABLE, dataset_path, preprocessed_xml]
    print("Running command:", " ".join(command))
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except Exception as e:
        print("Error running subprocess:", e)
        os.remove(preprocessed_xml)
        return [{"error": str(e)}]

    if result.returncode != 0:
        print("GEDLIB returned non-zero exit code:", result.returncode)
        print("Stderr:", result.stderr)

    if not result.stdout.strip():
        print("Warning: GEDLIB did not produce any stdout output.")
    else:
        print("GEDLIB output (first 500 characters):", result.stdout[:500])

    output_lines = result.stdout.strip().split("\n")
    if len(output_lines) == 0:
        print("No output lines captured from GEDLIB.")

    if platform.system() != "Windows":
        rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
        mem_usage_kb = rusage.ru_maxrss  # ru_maxrss is in kilobytes
    else:
        try:
            import psutil
            process = psutil.Process()
            mem_usage_kb = process.memory_info().rss // 1024  # in kilobytes
        except Exception:
            mem_usage_kb = -1

    props = get_first_two_graph_properties(dataset_path, collection_xml)
    if props is not None:
        (n1, e1, p1), (n2, e2, p2) = props
        avg_n = (n1 + n2) / 2
        avg_p = (p1 + p2) / 2
        scalability = max(n1, n2)
    else:
        avg_n = avg_p = scalability = None
        n1 = n2 = p1 = p2 = None

    results = []
    # Adjust regex to exactly match the expected output.
    regex = re.compile(
        r"METHOD=(\d+)\s+GRAPH1=(\d+)\s+GRAPH2=(\d+)\s+PREDGED=([\d.]+)\s+GTGED=N/A\s+RUNTIME=([\d.]+)\s+MEM=([\d.]+)"
    )
    for line in output_lines:
        match = regex.search(line)
        if match:
            method_id = int(match.group(1))
            graph1 = int(match.group(2))
            graph2 = int(match.group(3))
            pred_ged = float(match.group(4))
            runtime = float(match.group(5))
            mem_usage = float(match.group(6))  # in MB as printed by the executable
            method_name = METHOD_NAMES.get(method_id, f"Unknown Method {method_id}")
            results.append({
                "method": method_name,
                "ged": pred_ged,
                "runtime": runtime,
                "graph1": graph1,
                "graph2": graph2,
                "memory_usage_mb": mem_usage,
                "graph1_n": n1 if n1 is not None else "N/A",
                "graph1_density": round(p1, 4) if p1 is not None else "N/A",
                "graph2_n": n2 if n2 is not None else "N/A",
                "graph2_density": round(p2, 4) if p2 is not None else "N/A",
                "average_n": avg_n if avg_n is not None else "N/A",
                "average_density": round(avg_p, 4) if avg_p is not None else "N/A",
                "scalability": scalability if scalability is not None else "N/A",
                "accuracy": "N/A",
                "precision": "N/A",
                "rank_correlation": "N/A"
            })
        else:
            print("Warning: Line did not match expected format:", line)
    os.remove(preprocessed_xml)

    if not results:
        print("No valid results were parsed from GEDLIB output.")
    else:
        # Optionally, determine accuracy if STAR (Exact) method output is available.
        groundtruth = None
        for res in results:
            if res["method"] == "STAR (Exact)":
                groundtruth = res["ged"]
                break
        for res in results:
            if groundtruth is not None:
                res["accuracy"] = 100.0 if res["method"] == "STAR (Exact)" else round((groundtruth / res["ged"]) * 100,
                                                                                      2)
            else:
                res["accuracy"] = "N/A"
    return results


def log_results(results):
    """Log results into an Excel file after checking that data exists."""
    if not results:
        print("Error: No results to log. Excel file will not be created.")
        return
    df = pd.DataFrame(results)
    if df.empty:
        print("Error: DataFrame is empty. Excel file will not be created.")
        return
    os.makedirs(RESULTS_DIR, exist_ok=True)
    try:
        df.to_excel(RESULTS_FILE, index=False, engine='openpyxl')
        print("Experiments completed. Results saved in", RESULTS_FILE)
    except Exception as e:
        print("Error writing Excel file:", e)


if __name__ == "__main__":
    results = run_ged(DATASET_PATH, COLLECTION_XML)
    if results:
        print(f"Parsed {len(results)} result(s).")
    else:
        print("No results parsed.")
    log_results(results)
