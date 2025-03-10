#!/usr/bin/env python3
import subprocess
import json

def main():
    # Specify your parameters here:
    dataset_path = "/home/mfilippov/ged_data/processed_data/gxl/PROTEINS"          # Replace with your dataset directory path
    collection_xml = "/home/mfilippov/ged_data/processed_data/xml/PROTEINS.xml" # Replace with your collection XML file path
    idx1 = 0                                   # Graph index 1 (zero-based)
    idx2 = 1                                   # Graph index 2 (zero-based)
    executable = "/home/mfilippov/CLionProjects/gedlib/build/edit_path_exec"            # Path to the GEDLIB executable
    output_file = "/home/mfilippov/ged_data/results/extracted_paths/ipfp_edit_path.json"           # Name of the output JSON file

    # Build the command with required arguments.
    command = [
        executable,
        dataset_path,
        collection_xml,
        str(idx1),
        str(idx2)
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("Error running the executable:", e)
        print("stderr:", e.stderr)
        return

    output_lines = result.stdout.strip().splitlines()
    if not output_lines:
        print("No output received from the executable.")
        return

    # The first line is expected to be "Approximate Graph Edit Distance = <value>"
    try:
        cost_line = output_lines[0]
        parts = cost_line.split("=")
        if len(parts) < 2:
            raise ValueError("Invalid output format for GED cost.")
        ged_cost = float(parts[1].strip())
    except Exception as e:
        print("Error parsing GED cost:", e)
        return

    # Remaining lines are the edit operations.
    edit_operations = output_lines[1:]

    results = {
        "graph_edit_distance": ged_cost,
        "edit_operations": edit_operations
    }

    try:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=4)
        print(f"Results saved to {output_file}")
    except Exception as e:
        print("Error saving results:", e)

if __name__ == "__main__":
    main()
