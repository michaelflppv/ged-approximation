#!/usr/bin/env python3
import subprocess
import json

def main():
    # Specify your parameters here:
    dataset = "PROTEINS"
    dataset_path = f"/home/mfilippov/ged_data/processed_data/gxl/{dataset}"          # Update as needed
    collection_xml = f"/home/mfilippov/ged_data/processed_data/xml/{dataset}.xml"      # Update as needed
    idx1 = 0                                   # Graph index 1 (zero-based)
    idx2 = 305                                 # Graph index 2 (zero-based)
    executable = "/home/mfilippov/CLionProjects/gedlib/build/edit_path_exec"         # Path to the executable
    output_file = f"/home/mfilippov/ged_data/results/extracted_paths/ipfp_{dataset}_edit_path_for_{idx1}_{idx2}.json"  # Output JSON file

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

    # We expect the executable to output a JSON string.
    try:
        output_json = json.loads(result.stdout)
    except Exception as e:
        print("Error parsing JSON output:", e)
        print("Output was:", result.stdout)
        return

    # Save the JSON to the specified output file.
    try:
        with open(output_file, "w") as f:
            json.dump(output_json, f, indent=4)
        print(f"Results saved to {output_file}")
    except Exception as e:
        print("Error saving results:", e)

if __name__ == "__main__":
    main()
