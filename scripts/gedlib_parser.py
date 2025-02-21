#!/usr/bin/env python3
"""
This script runs the GEDLIB executable and captures its output line-by-line,
parses that output and writes the results to an Excel file as soon as possible.
This way, if the process is terminated, the already computed results are saved.
It includes extensive debug output and error checking.
"""

import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import platform
import pandas as pd
import signal
import sys
from glob import glob

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

# Global variable to hold intermediate results.
global_results = []  # This will be appended to as new lines are parsed.

def log_results(results):
    """Log results into an Excel file after checking that data exists."""
    if not results:
        print("Warning: No results to log.")
        return
    df = pd.DataFrame(results)
    if df.empty:
        print("Warning: DataFrame is empty; nothing to write.")
        return
    os.makedirs(RESULTS_DIR, exist_ok=True)
    try:
        df.to_excel(RESULTS_FILE, index=False, engine='openpyxl')
        print(f"Intermediate results saved in {RESULTS_FILE} (total rows: {len(df)}).")
    except Exception as e:
        print("Error writing Excel file:", e)

# Signal handler to flush current results before exiting.
def signal_handler(signum, frame):
    print(f"\nSignal {signum} received. Saving intermediate results before exiting.")
    log_results(global_results)
    sys.exit(0)

# Register signal handlers.
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
if hasattr(signal, "SIGHUP"):
    signal.signal(signal.SIGHUP, signal_handler)

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
    """Run the GEDLIB executable and parse its output line-by-line, flushing intermediate results."""
    try:
        preprocessed_xml = preprocess_xml_file(collection_xml)
    except Exception as e:
        print("Failed to preprocess collection XML:", e)
        return [{"error": "Preprocessing XML failed"}]

    command = [GED_EXECUTABLE, dataset_path, preprocessed_xml]
    print("Running command:", " ".join(command))
    try:
        # Use Popen to read output line-by-line.
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    except Exception as e:
        print("Error starting subprocess:", e)
        os.remove(preprocessed_xml)
        return [{"error": str(e)}]

    # Get additional metrics from graph properties.
    props = get_first_two_graph_properties(dataset_path, collection_xml)
    if props is not None:
        (n1, e1, p1), (n2, e2, p2) = props
        avg_n = (n1 + n2) / 2
        avg_p = (p1 + p2) / 2
        scalability = max(n1, n2)
    else:
        avg_n = avg_p = scalability = None
        n1 = n2 = p1 = p2 = None

    # Define regex to match expected output lines.
    regex = re.compile(
        r"METHOD=(\d+)\s+GRAPH1=(\d+)\s+GRAPH2=(\d+)\s+PREDGED=([\d.]+)\s+GTGED=N/A\s+RUNTIME=([\d.]+)\s+MEM=([\d.]+)"
    )

    line_count = 0
    flush_interval = 10  # flush every 10 lines

    # Process GEDLIB stdout line-by-line.
    for line in process.stdout:
        line = line.strip()
        line_count += 1
        if not line:
            continue
        match = regex.search(line)
        if match:
            method_id = int(match.group(1))
            graph1 = int(match.group(2))
            graph2 = int(match.group(3))
            pred_ged = float(match.group(4))
            runtime = float(match.group(5))
            mem_usage = float(match.group(6))  # in MB as printed by the executable
            method_name = METHOD_NAMES.get(method_id, f"Unknown Method {method_id}")
            result_entry = {
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
            }
            global_results.append(result_entry)
        else:
            print("Warning: Line did not match expected format:", line)

        # Periodically flush to Excel file.
        if line_count % flush_interval == 0:
            log_results(global_results)

    # Close stdout and wait for process to finish.
    process.stdout.close()
    process.wait()

    # Process any stderr output.
    stderr = process.stderr.read()
    if stderr:
        print("Stderr output from GEDLIB:", stderr)
    process.stderr.close()

    # Final flush before finishing.
    log_results(global_results)
    os.remove(preprocessed_xml)

    # Optionally, compute "accuracy" based on Exact if available.
    groundtruth = None
    for res in global_results:
        if res["method"] == "STAR (Exact)":
            groundtruth = res["ged"]
            break
    for res in global_results:
        if groundtruth is not None and res["ged"] != 0:
            res["accuracy"] = 100.0 if res["method"] == "STAR (Exact)" else round((groundtruth / res["ged"]) * 100, 2)
        else:
            res["accuracy"] = "N/A"

    return global_results

if __name__ == "__main__":
    results = run_ged(DATASET_PATH, COLLECTION_XML)
    if results:
        print(f"Parsed {len(results)} result(s).")
    else:
        print("No results parsed.")
    # Final log is already done during run_ged.
