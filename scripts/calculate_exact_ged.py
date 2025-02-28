#!/usr/bin/env python3
import os
import re
import subprocess
import argparse
import pandas as pd
import signal
import sys
import resource
from multiprocessing import Pool, cpu_count

# Global variables so signal handlers can access the results and output filename.
results = []
output_excel = None

def parse_executable_output(output):
    """
    Parse the output from the GED executable.
    """
    min_ged, max_ged, total_time, candidates, matches = None, None, None, None, None

    m = re.search(r"min_ged:\s*(\d+),\s*max_ged:\s*(\d+)", output)
    if m:
        min_ged = int(m.group(1))
        max_ged = int(m.group(2))

    m = re.search(r"Total time:\s*([^\s]+)\s*\(microseconds\)", output)
    if m:
        try:
            total_time = int(m.group(1)) / 1_000_000  # Convert microseconds to seconds
        except ValueError:
            total_time = "N/A"

    m = re.search(r"#candidates:\s*(\d+),\s*#matches:\s*(\d+)", output)
    if m:
        candidates = int(m.group(1))
        matches = int(m.group(2))

    return min_ged, max_ged, total_time, candidates, matches

def run_ged_executable(graph_file1, graph_file2, ged_executable):
    """
    Call the GED executable for a single pair of graphs.
    """
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
        "-l", "BMao",
        "-t", "-1",
        "-g"
    ]

    try:
        result = subprocess.run(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                check=True,
                                preexec_fn=set_unlimited,
                                timeout=300)
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"Timeout expired for command: {' '.join(cmd)}. Skipping this pair.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}")
        print(e)
        return None

def get_graph_id_from_filename(filename):
    """
    Extract the graph id from the filename.
    """
    base = os.path.basename(filename)
    match = re.match(r"graph_(\d+)\.txt", base)
    return match.group(1) if match else base

def process_pair(args):
    """
    Worker function for parallel GED computation.
    """
    file1, file2, ged_executable = args
    id1, id2 = get_graph_id_from_filename(file1), get_graph_id_from_filename(file2)

    print(f"Processing pair: {file1} and {file2}")
    output = run_ged_executable(file1, file2, ged_executable)

    if output is None:
        print(f"Error processing pair ({file1}, {file2}). Inserting N/A for results.")
        return {"graph_id_1": id1, "graph_id_2": id2, "min_ged": "N/A",
                "max_ged": "N/A", "runtime": "N/A", "candidates": "N/A", "matches": "N/A"}

    min_ged, max_ged, runtime, candidates, matches = parse_executable_output(output)
    return {"graph_id_1": id1, "graph_id_2": id2, "min_ged": min_ged,
            "max_ged": max_ged, "runtime": runtime, "candidates": candidates, "matches": matches}

def save_results(excel_file, results_list):
    """
    Save the results list to an Excel file with the correct column order.
    """
    df = pd.DataFrame(results_list, columns=["graph_id_1", "graph_id_2",
                                              "min_ged", "max_ged",
                                              "runtime", "candidates", "matches"])
    df.to_excel(excel_file, index=False)
    print(f"Results saved to {excel_file}")

def signal_handler(signum, frame):
    """
    Handle signals by saving partial results before exiting.
    """
    print(f"\nSignal {signum} received. Saving partial results and exiting.")
    global output_excel, results
    save_results(output_excel, results)
    sys.exit(1)

def main(txt_dir, ged_executable, output_excel_param, num_workers):
    global output_excel, results
    output_excel = output_excel_param

    # Set signal handlers for SIGINT and SIGTERM.
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Gather all .txt files in the specified directory.
    txt_files = [os.path.join(txt_dir, f) for f in os.listdir(txt_dir) if f.endswith('.txt')]
    txt_files.sort()
    results = []

    # Generate all unique graph pairs (i < j).
    graph_pairs = [(txt_files[i], txt_files[j], ged_executable)
                   for i in range(len(txt_files)) for j in range(i + 1, len(txt_files))]
    print(f"Total graph pairs to process: {len(graph_pairs)}")

    pool = Pool(processes=num_workers)
    try:
        # Process results one by one using imap.
        for count, res in enumerate(pool.imap(process_pair, graph_pairs), 1):
            results.append(res)
            # Immediately save the current results to the Excel file.
            save_results(output_excel, results)
            if count % 10 == 0:
                print(f"{count} pairs processed.")
    except KeyboardInterrupt:
        print("KeyboardInterrupt caught in main loop. Terminating pool and saving partial results.")
        pool.terminate()
        pool.join()
        save_results(output_excel, results)
        sys.exit(1)
    except Exception as e:
        print("An error occurred:", e)
        pool.terminate()
        pool.join()
        save_results(output_excel, results)
        sys.exit(1)
    else:
        pool.close()
        pool.join()
    finally:
        # In any case, ensure that results are saved.
        save_results(output_excel, results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute the Graph Edit Distance (GED) for all graph pairs in a directory using parallel processing.")
    parser.add_argument("txt_dir", help="Directory containing the graph txt files")
    parser.add_argument("ged_executable", help="Path to the GED executable")
    parser.add_argument("output_excel", help="Output Excel file")
    parser.add_argument("--workers", type=int, default=cpu_count(),
                        help="Number of parallel workers (default: all CPU cores)")

    args = parser.parse_args()
    main(args.txt_dir, args.ged_executable, args.output_excel, args.workers)
