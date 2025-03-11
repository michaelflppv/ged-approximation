#!/usr/bin/env python3
"""
This script runs the GEDLIB executable and captures its output line-by-line,
parses that output, and writes the results to an Excel file as soon as possible.
Intermediate results are flushed frequently so that if the process is terminated
(e.g. via Ctrl+C), the work done so far is saved. The Excel file is written using
a fallback strategy and will be split into multiple files if the data exceeds Excel’s
maximum row capacity.
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
import psutil  # For polling subprocess memory usage
from typing import Optional

if platform.system() != "Windows":
    import resource

# --------------------------
# Global variables and settings
# --------------------------
global_results = []            # Intermediate results list.
global_ged_process: Optional[subprocess.Popen] = None  # Handle to the GEDLIB subprocess.
global_preprocessed_xml: Optional[str] = None          # Path to the temporary preprocessed XML.

# Modify these paths as needed:
GED_EXECUTABLE = "../../gedlib/build/main_exec"
DATASET_PATH    = "/mnt/c/project_data/processed_data/gxl/AIDS"
COLLECTION_XML  = "/mnt/c/project_data/processed_data/xml/AIDS.xml"
RESULTS_DIR     = "/mnt/c/project_data/results/gedlib/AIDS"
RESULTS_FILE    = os.path.join(RESULTS_DIR, "AIDS_IPFP_results_ubuntu.xlsx")
EXACT_GED_FILE  = "/home/mfilippov/ged_data/results/exact_ged/AIDS/results.xlsx"  # Optional lookup file.
# Mapping of method ID to method names.
METHOD_NAMES = {
    8:  "Anchor Aware",
    10: "IPFP",
    11: "BIPARTITE",
    16: "REFINE",
    19: "HED",
    20: "STAR (Exact)"
}
# Maximum number of rows per Excel file.
EXCEL_MAX_ROWS = 1048573

# --------------------------
# Utility Functions
# --------------------------
def set_unlimited():
    """Set resource limits to unlimited (if supported)."""
    if platform.system() != "Windows":
        try:
            resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        except Exception as e:
            print("Warning: could not set RLIMIT_AS unlimited:", e)
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        except Exception as e:
            print("Warning: could not set RLIMIT_CPU unlimited:", e)

def log_results(results):
    """
    Save the current results to Excel.
    If the DataFrame exceeds Excel's maximum row limit, split the results across multiple files.
    Uses openpyxl as the primary engine, with xlsxwriter as fallback.
    """
    if not results:
        print("No results to save.")
        return

    df = pd.DataFrame(results)
    if df.empty:
        print("DataFrame is empty; nothing to write.")
        return

    # Standardize column names.
    df["graph_id_1"] = df["graph1"]
    df["graph_id_2"] = df["graph2"]
    desired_columns = [
        "method", "graph_id_1", "graph_id_2", "ged", "accuracy",
        "absolute_error", "squared_error", "runtime", "memory_usage_mb",
        "graph1_n", "graph1_density", "graph2_n", "graph2_density", "scalability"
    ]
    df = df[desired_columns]
    os.makedirs(RESULTS_DIR, exist_ok=True)

    if len(df) > EXCEL_MAX_ROWS:
        num_files = (len(df) + EXCEL_MAX_ROWS - 1) // EXCEL_MAX_ROWS
        print(f"DataFrame has {len(df)} rows; splitting into {num_files} files.")
        for part in range(num_files):
            start = part * EXCEL_MAX_ROWS
            end = start + EXCEL_MAX_ROWS
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
                    print(f"Existing file {file_path} is corrupted ({e}). Removing it.")
                    os.remove(file_path)
            temp_file = os.path.join(RESULTS_DIR, f"temp_results_part{part+1}.xlsx")
            try:
                chunk.to_excel(temp_file, index=False, engine='openpyxl')
                os.replace(temp_file, file_path)
                print(f"Saved {len(chunk)} rows to {file_path}.")
            except Exception as e:
                print(f"Error writing {file_path} with openpyxl: {e}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                try:
                    chunk.to_excel(temp_file, index=False, engine='xlsxwriter')
                    os.replace(temp_file, file_path)
                    print(f"Saved with fallback engine: {len(chunk)} rows to {file_path}.")
                except Exception as e2:
                    print(f"Failed to write {file_path} with fallback: {e2}")
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
    else:
        file_path = RESULTS_FILE
        if os.path.exists(file_path):
            try:
                from openpyxl import load_workbook
                load_workbook(file_path)
            except Exception as e:
                print(f"Existing file {file_path} is corrupted ({e}). Removing it.")
                os.remove(file_path)
        temp_file = os.path.join(RESULTS_DIR, "temp_results.xlsx")
        try:
            df.to_excel(temp_file, index=False, engine='openpyxl')
            os.replace(temp_file, file_path)
            print(f"Saved {len(df)} rows to {file_path}.")
        except Exception as e:
            print("Error writing Excel file with openpyxl:", e)
            if os.path.exists(temp_file):
                os.remove(temp_file)
            try:
                df.to_excel(temp_file, index=False, engine='xlsxwriter')
                os.replace(temp_file, file_path)
                print(f"Saved with fallback engine: {len(df)} rows to {file_path}.")
            except Exception as e2:
                print("Failed to write Excel file with fallback engine:", e2)
                if os.path.exists(temp_file):
                    os.remove(temp_file)

def signal_handler(signum, frame):
    """Handle termination signals by cleaning up and saving partial results."""
    print(f"\nSignal {signum} received. Saving intermediate results and exiting.")
    global global_ged_process, global_preprocessed_xml
    if global_ged_process is not None:
        try:
            global_ged_process.terminate()
            global_ged_process.wait(timeout=5)
        except Exception as e:
            print("Error terminating GED subprocess:", e)
    if global_preprocessed_xml is not None and os.path.exists(global_preprocessed_xml):
        try:
            os.remove(global_preprocessed_xml)
        except Exception as e:
            print("Error removing temporary XML file:", e)
    log_results(global_results)
    sys.exit(1)

# Register signal handlers for graceful termination.
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
if hasattr(signal, "SIGHUP"):
    signal.signal(signal.SIGHUP, signal_handler)

def preprocess_xml_file(xml_path: str) -> str:
    """
    Remove any DOCTYPE declarations from the XML file to avoid parsing issues,
    and return the path to a temporary file with the cleaned XML.
    """
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

def get_graph_properties(gxl_file: str):
    """
    Parse the given GXL file and compute:
      - number of nodes (n)
      - number of edges (e)
      - density = 2*e / (n*(n-1)) for undirected graphs (if n > 1)
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
    density = (2 * e) / (n * (n - 1)) if n > 1 else 0
    return n, e, density

def get_first_two_graph_properties(dataset_path: str, collection_xml: str):
    """
    Parse the collection XML (after cleaning) to retrieve the first two graph file names,
    then compute and return their (n, edges, density) properties.
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

def run_ged(dataset_path: str, collection_xml: str):
    """
    Run the GEDLIB executable with the given dataset and collection XML.
    Parse its output line-by-line and flush intermediate results every few lines.
    On termination or error, results are saved and temporary files are cleaned up.
    """
    global global_ged_process, global_preprocessed_xml
    try:
        preprocessed_xml = preprocess_xml_file(collection_xml)
        global_preprocessed_xml = preprocessed_xml
    except Exception as e:
        print("Failed to preprocess collection XML:", e)
        return [{"error": "Preprocessing XML failed"}]

    command = [GED_EXECUTABLE, dataset_path, preprocessed_xml]
    print("Running command:", " ".join(command))
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            preexec_fn=set_unlimited if platform.system() != "Windows" else None
        )
        global_ged_process = process
    except Exception as e:
        print("Error starting GED subprocess:", e)
        os.remove(preprocessed_xml)
        global_preprocessed_xml = None
        return [{"error": str(e)}]

    try:
        ged_proc = psutil.Process(process.pid)
    except Exception as e:
        print("Error creating psutil.Process for GEDLIB:", e)
        ged_proc = None

    props = get_first_two_graph_properties(dataset_path, collection_xml)
    if props is not None:
        (n1, _, d1), (n2, _, d2) = props
        scalability = max(n1, n2)
    else:
        scalability = None
        n1 = n2 = d1 = d2 = None

    # Regular expression to match expected output lines.
    regex = re.compile(
        r"METHOD=(\d+)\s+GRAPH1=(\d+)\s+GRAPH2=(\d+)\s+PREDGED=([\d.]+)\s+GTGED=N/A\s+RUNTIME=([\d.]+).*"
    )

    line_count = 0
    flush_interval = 5  # Flush intermediate results every 5 lines.
    try:
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
                try:
                    memory_usage_mb = ged_proc.memory_info().rss / (1024 * 1024) if ged_proc else "N/A"
                except Exception:
                    memory_usage_mb = "N/A"
                method_name = METHOD_NAMES.get(method_id, f"Unknown Method {method_id}")
                result_entry = {
                    "method": method_name,
                    "graph1": graph1,
                    "graph2": graph2,
                    "ged": pred_ged,
                    "accuracy": "N/A",         # Optionally compute later using exact GED lookup.
                    "absolute_error": "N/A",
                    "squared_error": "N/A",
                    "runtime": runtime,
                    "memory_usage_mb": memory_usage_mb,
                    "graph1_n": n1 if n1 is not None else "N/A",
                    "graph1_density": round(d1, 4) if d1 is not None else "N/A",
                    "graph2_n": n2 if n2 is not None else "N/A",
                    "graph2_density": round(d2, 4) if d2 is not None else "N/A",
                    "scalability": scalability if scalability is not None else "N/A"
                }
                global_results.append(result_entry)
            else:
                print("Warning: Unmatched line:", line)

            if line_count % flush_interval == 0:
                log_results(global_results)
    except Exception as e:
        print("Error while processing GED output:", e)
    finally:
        try:
            process.stdout.close()
        except Exception:
            pass
        process.wait()
        try:
            stderr = process.stderr.read()
            if stderr:
                print("GEDLIB stderr:", stderr)
        except Exception:
            pass
        try:
            process.stderr.close()
        except Exception:
            pass
        log_results(global_results)
        if global_preprocessed_xml is not None and os.path.exists(global_preprocessed_xml):
            try:
                os.remove(global_preprocessed_xml)
                global_preprocessed_xml = None
            except Exception as e:
                print("Error removing temporary XML file:", e)
    return global_results

if __name__ == "__main__":
    try:
        results = run_ged(DATASET_PATH, COLLECTION_XML)
        if results:
            print(f"Finished processing {len(results)} result(s).")
        else:
            print("No results processed.")
    except Exception as e:
        print("Unexpected error:", e)
        log_results(global_results)
        sys.exit(1)
