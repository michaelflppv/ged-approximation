import subprocess
import re
import pandas as pd

# Define paths
GED_EXECUTABLE = "/home/mfilippov/CLionProjects/gedlib/build/main_exec"  # Path to compiled C++ binary
DATASET_PATH = "/home/mfilippov/CLionProjects/gedlib/data/datasets/GREC/data"
COLLECTION_XML = "/home/mfilippov/CLionProjects/gedlib/data/collections/GREC.xml"
RESULTS_FILE = "ged_results.xlsx"

METHOD_NAMES = {
    10: "IPFP",
    11: "BIPARTITE",
    16: "REFINE",
    # Add other method mappings here
}

# Function to run GEDLIB C++ program and capture output
def run_ged(dataset_path, collection_xml):
    """Runs GEDLIB and parses output."""
    command = [GED_EXECUTABLE, dataset_path, collection_xml]

    try:
        # Execute and capture output
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
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

        return results
    except Exception as e:
        return [{"error": str(e)}]

# Function to log results
def log_results(results):
    """Logs results into an Excel file."""
    df = pd.DataFrame(results)
    df.to_excel(RESULTS_FILE, index=False, engine='openpyxl')

# Run experiment
results = run_ged(DATASET_PATH, COLLECTION_XML)

# Log results
log_results(results)

print("Experiments completed. Results saved in", RESULTS_FILE)