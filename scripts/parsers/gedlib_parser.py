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
import psutil  # For polling subprocess memory usage

# Define relative paths (adjust these relative paths as needed)
script_dir = os.path.dirname(os.path.abspath(__file__))

GED_EXECUTABLE = "/home/mfilippov/CLionProjects/gedlib/build/main_exec"
DATASET_PATH = "/home/mfilippov/ged_data/processed_data/gxl/AIDS"
COLLECTION_XML = "/home/mfilippov/ged_data/processed_data/xml/AIDS.xml"
RESULTS_DIR = "/home/mfilippov/ged_data/results/gedlib/AIDS"
# Updated: Remove extra "AIDS/" from the file name.
RESULTS_FILE = os.path.join(RESULTS_DIR, "AIDS_IPFP_results_ubuntu.xlsx")
# New: Path to the Excel file with exact GED results (must contain columns "graph_id_1", "graph_id_2", and "min_ged")
EXACT_GED_FILE = "/home/mfilippov/ged_data/results/exact_ged/AIDS/results.xlsx"

# Update method mapping according to new C++ enum values (adjust as needed)
METHOD_NAMES = {
    8: "Anchor Aware",
    10: "IPFP",
    11: "BIPARTITE",
    16: "REFINE",
    19: "HED",
    20: "STAR (Exact)"
}

# Conditional import for resource module
if platform.system() != "Windows":
    import resource

# Global variable to hold intermediate results.
global_results = []  # This will be appended to as new lines are parsed.

# Global lookup dictionary for exact GED results.
exact_lookup = {}


def load_exact_lookup(exact_file):
    """Load the exact GED results and return a lookup dict mapping (graph_id_1, graph_id_2) to min_ged."""
    try:
        df_exact = pd.read_excel(exact_file)
        df_exact["min_ged_numeric"] = pd.to_numeric(df_exact["min_ged"], errors="coerce")
        df_exact = df_exact.dropna(subset=["min_ged_numeric"])
        lookup = {}
        for _, row in df_exact.iterrows():
            try:
                g1 = int(row["graph_id_1"])
                g2 = int(row["graph_id_2"])
            except Exception as e:
                g1 = row["graph_id_1"]
                g2 = row["graph_id_2"]
            lookup[(g1, g2)] = row["min_ged_numeric"]
        return lookup
    except Exception as e:
        print("Error loading exact GED file:", e)
        return {}


def compute_absolute_error(pred, exact):
    return abs(pred - exact)


def compute_squared_error(pred, exact):
    return (pred - exact) ** 2


def log_results(results):
    """Log results into one or more Excel files after checking that data exists.
       The resulting Excel file(s) will contain only the following columns (in order):
         method, ged, runtime, graph_id_1, graph_id_2, accuracy, absolute_error, squared_error,
         memory_usage_mb, graph1_n, graph1_density, graph2_n, graph2_density, scalability
       If the number of rows exceeds 1,048,573, the results are split into multiple files.
       This function also checks for existing corrupted files and uses a fallback engine if needed.
    """
    if not results:
        print("Warning: No results to log.")
        return
    df = pd.DataFrame(results)
    if df.empty:
        print("Warning: DataFrame is empty; nothing to write.")
        return

    # Rename graph1 and graph2 to graph_id_1 and graph_id_2.
    df["graph_id_1"] = df["graph1"]
    df["graph_id_2"] = df["graph2"]
    # Select and order the desired columns.
    desired_columns = [
        "method",
        "graph_id_1",
        "graph_id_2",
        "ged",
        "accuracy",
        "absolute_error",
        "squared_error",
        "runtime",
        "memory_usage_mb",
        "graph1_n",
        "graph1_density",
        "graph2_n",
        "graph2_density",
        "scalability"
    ]
    df = df[desired_columns]
    os.makedirs(RESULTS_DIR, exist_ok=True)

    max_rows = 1048573
    if len(df) > max_rows:
        num_files = (len(df) + max_rows - 1) // max_rows
        print(f"DataFrame has {len(df)} rows; splitting into {num_files} file(s).")
        for part in range(num_files):
            start = part * max_rows
            end = start + max_rows
            chunk = df.iloc[start:end]
            if part == 0:
                file_path = RESULTS_FILE
            else:
                base, ext = os.path.splitext(RESULTS_FILE)
                file_path = f"{base}_part{part+1}{ext}"
            if os.path.exists(file_path):
                try:
                    from openpyxl import load_workbook
                    load_workbook(file_path)
                except Exception as e:
                    print(f"Existing results file {file_path} appears corrupted ({e}). Removing it.")
                    os.remove(file_path)
            temp_file = os.path.join(RESULTS_DIR, f"temp_results_part{part+1}.xlsx")
            try:
                chunk.to_excel(temp_file, index=False, engine='openpyxl')
                os.replace(temp_file, file_path)
                print(f"Intermediate results saved in {file_path} (rows: {len(chunk)}).")
            except Exception as e:
                print(f"Error writing Excel file with openpyxl for {file_path}:", e)
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                try:
                    chunk.to_excel(temp_file, index=False, engine='xlsxwriter')
                    os.replace(temp_file, file_path)
                    print(f"Intermediate results saved with fallback engine in {file_path} (rows: {len(chunk)}).")
                except Exception as e2:
                    print(f"Error writing Excel file with fallback engine for {file_path}:", e2)
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
    else:
        file_path = RESULTS_FILE
        if os.path.exists(file_path):
            try:
                from openpyxl import load_workbook
                load_workbook(file_path)
            except Exception as e:
                print(f"Existing results file {file_path} appears corrupted ({e}). Removing it.")
                os.remove(file_path)
        temp_file = os.path.join(RESULTS_DIR, "temp_results.xlsx")
        try:
            df.to_excel(temp_file, index=False, engine='openpyxl')
            os.replace(temp_file, file_path)
            print(f"Intermediate results saved in {file_path} (total rows: {len(df)}).")
        except Exception as e:
            print("Error writing Excel file with openpyxl:", e)
            if os.path.exists(temp_file):
                os.remove(temp_file)
            try:
                df.to_excel(temp_file, index=False, engine='xlsxwriter')
                os.replace(temp_file, file_path)
                print(f"Intermediate results saved with fallback engine in {file_path} (total rows: {len(df)}).")
            except Exception as e2:
                print("Error writing Excel file with fallback engine:", e2)
                if os.path.exists(temp_file):
                    os.remove(temp_file)


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

    # Create a psutil Process object for the subprocess.
    try:
        ged_process = psutil.Process(process.pid)
    except Exception as e:
        print("Error creating psutil.Process for GEDLIB:", e)
        ged_process = None

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
    # This regex no longer awaits any MEM field from the executable.
    regex = re.compile(
        r"METHOD=(\d+)\s+GRAPH1=(\d+)\s+GRAPH2=(\d+)\s+PREDGED=([\d.]+)\s+GTGED=N/A\s+RUNTIME=([\d.]+).*"
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
            # Poll current memory usage from the subprocess via psutil.
            try:
                memory_usage_mb = ged_process.memory_info().rss / (1024 * 1024)
            except Exception:
                memory_usage_mb = "N/A"
            method_name = METHOD_NAMES.get(method_id, f"Unknown Method {method_id}")
            result_entry = {
                "method": method_name,
                "graph1": graph1,
                "graph2": graph2,
                "ged": pred_ged,
                "accuracy": "N/A",  # Will be computed later.
                "absolute_error": "N/A",  # Will be computed later.
                "squared_error": "N/A",  # Will be computed later.
                "runtime": runtime,
                "memory_usage_mb": memory_usage_mb,
                "graph1_n": n1 if n1 is not None else "N/A",
                "graph1_density": round(p1, 4) if p1 is not None else "N/A",
                "graph2_n": n2 if n2 is not None else "N/A",
                "graph2_density": round(p2, 4) if p2 is not None else "N/A",
                "scalability": scalability if scalability is not None else "N/A",
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

    # Compute accuracy, absolute error, and squared error using exact GED values.
    for res in global_results:
        key = (res["graph1"], res["graph2"])
        # Only compute errors if an exact GED value exists for this pair.
        if key in exact_lookup:
            exact_val = exact_lookup[key]
            # If the exact value is not NA and prediction is nonzero, compute errors.
            if pd.notna(exact_val) and res["ged"] != "N/A":
                res["accuracy"] = round((exact_val / res["ged"]) * 100, 2)
                res["absolute_error"] = round(compute_absolute_error(res["ged"], exact_val), 4)
                res["squared_error"] = round(compute_squared_error(res["ged"], exact_val), 4)
            else:
                res["accuracy"] = "N/A"
                res["absolute_error"] = "N/A"
                res["squared_error"] = "N/A"
        else:
            res["accuracy"] = "N/A"
            res["absolute_error"] = "N/A"
            res["squared_error"] = "N/A"

    return global_results


if __name__ == "__main__":
    # Load exact GED lookup table.
    exact_lookup = load_exact_lookup(EXACT_GED_FILE)
    results = run_ged(DATASET_PATH, COLLECTION_XML)
    if results:
        print(f"Parsed {len(results)} result(s).")
    else:
        print("No results parsed.")
    # Final log is already done during run_ged.
