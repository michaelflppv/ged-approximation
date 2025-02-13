import subprocess
import re
import pandas as pd
import os
import tempfile
import xml.etree.ElementTree as ET
import resource

# Define paths
GED_EXECUTABLE = "/home/mfilippov/CLionProjects/gedlib/build/main_exec"  # Path to compiled C++ binary (Modify if needed)
DATASET_PATH = "/home/mfilippov/PycharmProjects/ged-approximation/data_converters/data/PROTEINS/results"  # Path to dataset directory (Modify if needed)
COLLECTION_XML = "/home/mfilippov/PycharmProjects/ged-approximation/data_converters/data/PROTEINS/collections/collection.xml"
RESULTS_DIR = "data/PROTEINS/performance"  # Directory to save results (Modify if needed)
RESULTS_FILE = os.path.join(RESULTS_DIR, "ged_results.xlsx")  # Path to save results (Modify if needed)

METHOD_NAMES = {
    20: "STAR (Exact)",
    10: "IPFP",
    11: "BIPARTITE",
    16: "REFINE",
    # Add additional method mappings if needed.
}


def preprocess_xml_file(xml_path):
    """Remove DOCTYPE declarations from the XML file and return path to a temporary file."""
    with open(xml_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
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
        return None, None
    file1 = graphs[0].get('file')
    file2 = graphs[1].get('file')
    path1 = os.path.join(dataset_path, file1)
    path2 = os.path.join(dataset_path, file2)
    props1 = get_graph_properties(path1)
    props2 = get_graph_properties(path2)
    return props1, props2


def run_ged(dataset_path, collection_xml):
    """Run the GEDLIB executable and parse its output, while collecting additional metrics."""
    # Preprocess collection XML to remove DOCTYPE lines.
    preprocessed_xml = preprocess_xml_file(collection_xml)
    command = [GED_EXECUTABLE, dataset_path, preprocessed_xml]
    try:
        # Run GEDLIB and capture output.
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        if result.stderr:
            print("GEDLIB stderr:", result.stderr)
        output_lines = result.stdout.strip().split("\n")

        # Measure memory usage (in kilobytes) for child processes.
        rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
        mem_usage_kb = rusage.ru_maxrss  # (on Linux, ru_maxrss is in kilobytes)

        # Get properties for the first two graphs.
        props = get_first_two_graph_properties(dataset_path, collection_xml)
        if props is not None:
            (n1, e1, p1), (n2, e2, p2) = props
            avg_n = (n1 + n2) / 2
            avg_p = (p1 + p2) / 2
            scalability = max(n1, n2)
        else:
            n1 = n2 = avg_n = scalability = None
            p1 = p2 = avg_p = None

        results = []
        # First, collect all method outputs.
        for line in output_lines:
            match = re.search(r"METHOD=(\d+) DIST=([\d.]+) TIME=([\d.]+)", line)
            if match:
                method_id = int(match.group(1))
                distance = float(match.group(2))
                runtime = float(match.group(3))
                method_name = METHOD_NAMES.get(method_id, f"Unknown Method {method_id}")
                results.append({
                    "method": method_name,
                    "ged": distance,
                    "runtime": runtime,
                    "graph1_n": n1 if n1 is not None else "N/A",
                    "graph1_density": round(p1, 4) if p1 is not None else "N/A",
                    "graph2_n": n2 if n2 is not None else "N/A",
                    "graph2_density": round(p2, 4) if p2 is not None else "N/A",
                    "average_n": avg_n if avg_n is not None else "N/A",
                    "average_density": round(avg_p, 4) if avg_p is not None else "N/A",
                    "memory_usage_kb": mem_usage_kb,
                    # Placeholders; will update below.
                    "scalability": scalability if scalability is not None else "N/A",
                    "accuracy": None,
                    "precision": "N/A",
                    "rank_correlation": "N/A"
                })
        os.remove(preprocessed_xml)

        # Determine groundtruth GED from STAR (Exact).
        groundtruth = None
        for res in results:
            if res["method"] == "STAR (Exact)":
                groundtruth = res["ged"]
                break
        # If STAR method was not found, we cannot compute relative accuracy.
        for res in results:
            if groundtruth is not None:
                if res["method"] == "STAR (Exact)":
                    res["accuracy"] = 100.0
                else:
                    # Assume approximate GED values are >= groundtruth.
                    res["accuracy"] = round((groundtruth / res["ged"]) * 100, 2)
            else:
                res["accuracy"] = "N/A"

        return results
    except Exception as e:
        return [{"error": str(e)}]


def log_results(results):
    """Log results into an Excel file."""
    df = pd.DataFrame(results)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    df.to_excel(RESULTS_FILE, index=False, engine='openpyxl')


results = run_ged(DATASET_PATH, COLLECTION_XML)
log_results(results)
print("Experiments completed. Results saved in", RESULTS_FILE)