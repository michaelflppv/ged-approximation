#!/usr/bin/env python3
import os
import re
import subprocess
import argparse
import pandas as pd
import signal
import sys
import resource

# Global variable to store results and the Excel filename so that signal handlers can access them.
results = []
output_excel = None


def parse_executable_output(output):
    """
    Parse the output from the GED executable.
    We expect lines such as:
      "*** GEDs ***"
      "min_ged: 12, max_ged: 45"
      ... other progress lines ...
      "Total time: 123456 (microseconds), total search space: 7890"
      "#candidates: 34, #matches: 12"

    Returns:
      min_ged, max_ged, total_time, candidates, matches
    """
    min_ged = None
    max_ged = None
    total_time = None
    candidates = None
    matches = None

    m = re.search(r"min_ged:\s*(\d+),\s*max_ged:\s*(\d+)", output)
    if m:
        min_ged = int(m.group(1))
        max_ged = int(m.group(2))

    m = re.search(r"Total time:\s*([^\s]+)\s*\(microseconds\)", output)
    if m:
        try:
            total_time = int(m.group(1))
        except ValueError:
            total_time = m.group(1)

    m = re.search(r"#candidates:\s*(\d+),\s*#matches:\s*(\d+)", output)
    if m:
        candidates = int(m.group(1))
        matches = int(m.group(2))

    return min_ged, max_ged, total_time, candidates, matches


def run_ged_executable(graph_file1, graph_file2, ged_executable):
    """
    Call the GED executable for a single pair of graphs.
    Command line:
      ./ged -d <graph_file1> -q <graph_file2> -m pair -p astar -l LSa -g

    The process is started with resource limits lifted (set to unlimited) so that it can use
    as much CPU time and memory as available on the system.

    Returns:
      The captured output (stdout+stderr) or None on error.
    """

    # Function to set resource limits to unlimited
    def set_unlimited():
        try:
            resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        except Exception as e:
            print("Warning: could not set RLIMIT_AS unlimited:", e)
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        except Exception as e:
            print("Warning: could not set RLIMIT_CPU unlimited:", e)

    cmd = [
        ged_executable,
        "-d", graph_file1,
        "-q", graph_file2,
        "-m", "pair",
        "-p", "astar",
        "-l", "LSa",
        "-g"
    ]
    try:
        # Set a timeout of 100 seconds (i.e., 100,000,000 microseconds)
        result = subprocess.run(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                check=True,
                                preexec_fn=set_unlimited,
                                timeout=100)
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"Timeout expired for command: {' '.join(cmd)}. Proceeding with the next pair.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}")
        print(e)
        return None


def get_graph_id_from_filename(filename):
    """
    Extract the graph id from the filename.
    Assumes files are named as "graph_<id>.txt"
    """
    base = os.path.basename(filename)
    match = re.match(r"graph_(\d+)\.txt", base)
    if match:
        return match.group(1)
    else:
        return base


def save_results(excel_file, results_list):
    """
    Save the results list to an Excel file.
    """
    df = pd.DataFrame(results_list, columns=["graph_id_1", "graph_id_2",
                                             "min_ged", "max_ged",
                                             "total_time", "candidates", "matches"])
    df.to_excel(excel_file, index=False)
    print(f"Results written to {excel_file}")


def signal_handler(signum, frame):
    """
    Handle signals (e.g. SIGINT or SIGTERM) by saving partial results before exit.
    """
    print(f"\nSignal {signum} received. Saving partial results and exiting.")
    global output_excel, results
    save_results(output_excel, results)
    sys.exit(1)


def main(txt_dir, ged_executable, output_excel_param):
    global output_excel, results
    output_excel = output_excel_param

    # Install signal handlers for SIGINT (Ctrl+C) and SIGTERM.
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Gather all .txt files in the specified directory.
    txt_files = [os.path.join(txt_dir, f) for f in os.listdir(txt_dir) if f.endswith('.txt')]
    txt_files.sort()  # Assumes naming "graph_<id>.txt" for proper ordering.
    results = []

    try:
        # For each unique pair (i, j) with i < j.
        for i in range(len(txt_files)):
            for j in range(i + 1, len(txt_files)):
                file1 = txt_files[i]
                file2 = txt_files[j]

                # Get graph IDs and skip any pair with graph_1.txt.
                id1 = get_graph_id_from_filename(file1)
                id2 = get_graph_id_from_filename(file2)

                print(f"Processing pair: {file1} and {file2}")
                output = run_ged_executable(file1, file2, ged_executable)
                if output is None:
                    print(f"Error processing pair ({file1}, {file2}). Inserting N/A for results.")
                    results.append({
                        "graph_id_1": id1,
                        "graph_id_2": id2,
                        "min_ged": "N/A",
                        "max_ged": "N/A",
                        "total_time": "N/A",
                        "candidates": "N/A",
                        "matches": "N/A"
                    })
                    continue
                # Parse and add the results.
                min_ged, max_ged, total_time, candidates, matches = parse_executable_output(output)
                results.append({
                    "graph_id_1": id1,
                    "graph_id_2": id2,
                    "min_ged": min_ged,
                    "max_ged": max_ged,
                    "total_time": total_time,
                    "candidates": candidates,
                    "matches": matches
                })
    except Exception as e:
        print("An unexpected error occurred. Saving partial results before termination.")
        save_results(output_excel, results)
        raise e
    else:
        save_results(output_excel, results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="For every pair of graph txt files in a directory, compute the Graph Edit Distance (GED) using a C++ executable and output the results to an Excel file."
    )
    parser.add_argument("txt_dir", help="Directory containing the graph txt files")
    parser.add_argument("ged_executable",
                        help="Path to the GED executable (e.g. /mnt/c/Users/mikef/CLionProjects/Graph_Edit_Distance/ged)")
    parser.add_argument("output_excel", help="Output Excel file (e.g. results.xlsx)")
    args = parser.parse_args()
    main(args.txt_dir, args.ged_executable, args.output_excel)
