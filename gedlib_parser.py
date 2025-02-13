import subprocess
import re
import pandas as pd
import os
import tempfile

# Define paths
GED_EXECUTABLE = "/home/mfilippov/CLionProjects/gedlib/build/main_exec"  # Path to compiled C++ binary (Modify if needed)
DATASET_PATH = "/home/mfilippov/PycharmProjects/ged-approximation/data_converters/data/IMDB-BINARY/results"  # Path to dataset directory (Modify if needed)
COLLECTION_XML = "/home/mfilippov/PycharmProjects/ged-approximation/data_converters/data/IMDB-BINARY/collections/collection.xml"
RESULTS_DIR = "data/IMDB-BINARY/performance"  # Directory to save results (Modify if needed)
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

def run_ged(dataset_path, collection_xml):
    """Run the GEDLIB executable and parse its output."""
    # Preprocess collection XML to remove DOCTYPE lines.
    preprocessed_xml = preprocess_xml_file(collection_xml)
    command = [GED_EXECUTABLE, dataset_path, preprocessed_xml]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        if result.stderr:
            print("GEDLIB stderr:", result.stderr)
        output_lines = result.stdout.strip().split("\n")
        results = []
        for line in output_lines:
            match = re.search(r"METHOD=(\d+) DIST=([\d.]+) TIME=([\d.]+)", line)
            if match:
                method_id = int(match.group(1))
                distance = float(match.group(2))
                runtime = float(match.group(3))
                method_name = METHOD_NAMES.get(method_id, f"Unknown Method {method_id}")
                results.append({"method": method_name, "ged": distance, "runtime": runtime})
        os.remove(preprocessed_xml)
        return results
    except Exception as e:
        return [{"error": str(e)}]

def log_results(results):
    """Log results to an Excel file."""
    df = pd.DataFrame(results)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    df.to_excel(RESULTS_FILE, index=False, engine='openpyxl')

results = run_ged(DATASET_PATH, COLLECTION_XML)
log_results(results)
print("Experiments completed. Results saved in", RESULTS_FILE)