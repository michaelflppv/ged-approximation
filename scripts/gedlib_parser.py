import os
import subprocess
import re
import pandas as pd
import tempfile
import xml.etree.ElementTree as ET
import platform

# Define relative paths
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define paths (adjust these relative paths as needed)
GED_EXECUTABLE = "/home/mfilippov/CLionProjects/gedlib/build/main_exec"  # Path to compiled C++ binary
DATASET_PATH = "../processed_data/gxl/PROTEINS"  # Path to PROTEINS dataset directory
COLLECTION_XML = "../processed_data/xml/PROTEINS.xml"  # Path to PROTEINS collection XML file
RESULTS_DIR = "../results/gedlib"  # Directory to save GEDLIB results
RESULTS_FILE = os.path.join(RESULTS_DIR, "PROTEINS_REFINE_results.xlsx")  # Path to save results

# Update method mapping according to new C++ enum values (assumed to be 0,1,2,3)
METHOD_NAMES = {
    0: "F2",
    20: "STAR (Exact)",
    10: "IPFP",
    11: "BIPARTITE",
    16: "REFINE",
    # Add additional method mappings if needed.
}

# Conditional import for resource module
if platform.system() != "Windows":
    import resource

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
        result = subprocess.run(command, capture_output=True, text=True)
        if result.stderr:
            print("GEDLIB stderr:", result.stderr)
        output_lines = result.stdout.strip().split("\n")

        # Also measure memory usage (if needed) from child processes.
        if platform.system() != "Windows":
            rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
            mem_usage_kb = rusage.ru_maxrss  # (on Linux, ru_maxrss is in kilobytes)
        else:
            import psutil
            process = psutil.Process()
            mem_usage_kb = process.memory_info().rss // 1024  # in kilobytes

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
        # Updated regex to capture the new output format:
        # Expected output format from C++:
        # METHOD=<method_id> GRAPH1=<graph1> GRAPH2=<graph2> PREDGED=<predged> GTGED=N/A RUNTIME=<runtime> MEM=<mem_usage>
        regex = re.compile(
            r"METHOD=(\d+).*?GRAPH1=(\d+).*?GRAPH2=(\d+).*?PREDGED=([\d.]+).*?RUNTIME=([\d.]+).*?MEM=([\d.]+)"
        )
        for line in output_lines:
            match = regex.search(line)
            if match:
                method_id = int(match.group(1))
                graph1 = int(match.group(2))
                graph2 = int(match.group(3))
                pred_ged = float(match.group(4))
                runtime = float(match.group(5))
                mem_usage = float(match.group(6))  # This is in MB as printed by the executable
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
                    "accuracy": "N/A",  # As before, since no ground truth GED is provided.
                    "precision": "N/A",
                    "rank_correlation": "N/A"
                })
        os.remove(preprocessed_xml)

        # Optionally, if you want to determine a ground truth GED (e.g., from STAR method), you can do so:
        groundtruth = None
        for res in results:
            if res["method"] == "STAR (Exact)":
                groundtruth = res["ged"]
                break
        for res in results:
            if groundtruth is not None:
                if res["method"] == "STAR (Exact)":
                    res["accuracy"] = 100.0
                else:
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


if __name__ == "__main__":
    results = run_ged(DATASET_PATH, COLLECTION_XML)
    log_results(results)
    print("Experiments completed. Results saved in", RESULTS_FILE)
