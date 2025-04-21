#!/usr/bin/env python3
import os
import re
import subprocess
import pandas as pd
import signal
import sys
import time
import random
import platform
import argparse

# Try to import resource; note that on Windows this may not be available.
try:
    import resource
    RESOURCE_AVAILABLE = True
except ImportError:
    RESOURCE_AVAILABLE = False

from multiprocessing import Pool

# -------------------------------
# Utility Functions
# -------------------------------

def set_unlimited():
    """
    Set resource limits to unlimited if possible.
    On Windows, resource limits are not supported so this is skipped.
    """
    if not RESOURCE_AVAILABLE or os.name == 'nt':
        # On Windows or if resource module is unavailable, do nothing.
        return
    try:
        resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    except Exception as e:
        print("Warning: could not set RLIMIT_AS unlimited:", e)
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    except Exception as e:
        print("Warning: could not set RLIMIT_CPU unlimited:", e)


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
    Timeout is set to 30 seconds.
    """
    cmd = [
        ged_executable,
        "-d", graph_file1,
        "-q", graph_file2,
        "-m", "pair",
        "-p", "astar",
        "-l", "BMao",  # Fixed heuristic name in command.
        "-t", "-1",
        "-g"
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
            preexec_fn=set_unlimited,
            timeout=30
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return None
    except subprocess.CalledProcessError:
        return None


def get_graph_id_from_filename(filename):
    """
    Extract the graph id from the filename.
    Assumes filenames are in the form "graph_<id>.txt".
    """
    base = os.path.basename(filename)
    match = re.match(r"graph_(\d+)\.txt", base)
    return match.group(1) if match else base


def should_skip_pair(dataset, graph_id1, graph_id2, lb_df, threshold=150):
    """
    Check the filtering Excel file for the given dataset and graph pair.
    Returns True if the "Lower Bound" exceeds the threshold.
    """
    try:
        id1 = int(graph_id1)
        id2 = int(graph_id2)
    except ValueError:
        print(f"Warning: could not convert graph ids {graph_id1}, {graph_id2} to int.")
        return False

    if isinstance(lb_df, list):
        for df in lb_df:
            df_filtered = df[df["Dataset"] == dataset]
            matching_rows = df_filtered[
                ((df_filtered["graph_id1"] == id1) & (df_filtered["graph_id2"] == id2)) |
                ((df_filtered["graph_id1"] == id2) & (df_filtered["graph_id2"] == id1))
            ]
            if not matching_rows.empty:
                lb_value = matching_rows.iloc[0]["Lower Bound"]
                if lb_value > threshold:
                    return True
        return False
    else:
        df_filtered = lb_df[lb_df["Dataset"] == dataset]
        matching_rows = df_filtered[
            ((df_filtered["graph_id1"] == id1) & (df_filtered["graph_id2"] == id2)) |
            ((df_filtered["graph_id1"] == id2) & (df_filtered["graph_id2"] == id1))
        ]
        if not matching_rows.empty:
            lb_value = matching_rows.iloc[0]["Lower Bound"]
            if lb_value > threshold:
                return True
        return False


# -------------------------------
# Worker Function
# -------------------------------

def process_pair(pair, apply_heuristic, lb_df_filter, dataset, threshold, ged_executable):
    """
    Process a single pair of graphs.
    If apply_heuristic is True and the pair is filtered out, mark it as skipped.
    Otherwise, run the GED executable and parse its output.
    """
    file1, file2 = pair
    id1 = get_graph_id_from_filename(file1)
    id2 = get_graph_id_from_filename(file2)

    if apply_heuristic and lb_df_filter is not None:
        if should_skip_pair(dataset, id1, id2, lb_df_filter, threshold):
            return {
                "graph_id_1": id1,
                "graph_id_2": id2,
                "min_ged": "skipped",
                "max_ged": "skipped",
                "runtime": 0,  # No processing time if skipped.
                "candidates": "skipped",
                "matches": "skipped",
                "skipped": True
            }

    output = run_ged_executable(file1, file2, ged_executable)
    if output is None:
        return {
            "graph_id_1": id1,
            "graph_id_2": id2,
            "min_ged": "N/A",
            "max_ged": "N/A",
            "runtime": "N/A",
            "candidates": "N/A",
            "matches": "N/A",
            "skipped": False
        }

    min_ged, max_ged, runtime, candidates, matches = parse_executable_output(output)
    return {
        "graph_id_1": id1,
        "graph_id_2": id2,
        "min_ged": min_ged,
        "max_ged": max_ged,
        "runtime": runtime,
        "candidates": candidates,
        "matches": matches,
        "skipped": False
    }


def worker(args):
    """
    Unpack arguments for multiprocessing.
    """
    pair, apply_heuristic, lb_df_filter, dataset, threshold, ged_executable = args
    return process_pair(pair, apply_heuristic, lb_df_filter, dataset, threshold, ged_executable)


def run_experiment(pairs, apply_heuristic, lb_df_filter, dataset, threshold, ged_executable, num_workers):
    """
    Run GED processing on the given pairs using a multiprocessing pool.
    Returns the list of results and total elapsed wall-clock time.
    """
    results = []
    start_time = time.time()
    args_list = [(pair, apply_heuristic, lb_df_filter, dataset, threshold, ged_executable) for pair in pairs]
    with Pool(processes=num_workers) as pool:
        for count, res in enumerate(pool.imap(worker, args_list), 1):
            if count % 10 == 0:
                print(f"{count} pairs processed.")
            results.append(res)
    total_time = time.time() - start_time
    return results, total_time

def save_results_excel(output_file, baseline_results, heuristic_results_dict, summary):
    invalid_chars = r'[\\/*?:\[\]]'
    def sanitize_sheet_name(sheet_name):
        import re
        # Replace any invalid characters with an underscore
        return re.sub(invalid_chars, '_', sheet_name)[:31]  # Excel sheet names are limited to 31 characters

    from pandas import ExcelWriter, DataFrame
    with ExcelWriter(output_file, engine="openpyxl") as writer:
        DataFrame(baseline_results).to_excel(writer, sheet_name="Without_Heuristics", index=False)
        for heuristic, res in heuristic_results_dict.items():
            sheet_name = f"Heuristic_ {heuristic}"
            safe_sheet_name = sanitize_sheet_name(sheet_name)
            DataFrame(res).to_excel(writer, sheet_name=safe_sheet_name, index=False)
        DataFrame(summary).to_excel(writer, sheet_name="Summary", index=False)


def signal_handler(signum, frame):
    print(f"Signal {signum} received. Exiting.")
    sys.exit(1)

def parse_command_line():
    parser = argparse.ArgumentParser(description="Run heuristic GED experiments.")
    parser.add_argument("--txt_dir", type=str, default="../processed_data/txt/AIDS",
                        help="Directory containing .txt graph files (default: ../processed_data/txt/AIDS).")
    parser.add_argument("--ged_executable", type=str, default="../Graph_Edit_Distance/ged",
                        help="Path to the GED executable (default: ../Graph_Edit_Distance/ged).")
    parser.add_argument("--output_excel", type=str, default="../results/lower_bound/AIDS/heuristic_comparison.xlsx",
                        help="Output Excel file path (default: ../results/lower_bound/AIDS/heuristic_comparison.xlsx).")
    parser.add_argument("--dataset", type=str, default="AIDS",
                        help="Dataset name (e.g. AIDS).")
    parser.add_argument("--lb_folder", type=str, default="../results/lower_bound/AIDS",
                        help="Folder containing heuristic Excel files (default: ../results/lower_bound/AIDS).")
    parser.add_argument("--workers", type=int, default=8,
                        help="Number of workers for multiprocessing (default: 8).")
    parser.add_argument("--threshold", type=int, default=150,
                        help="Threshold value for heuristic filtering (default: 150).")
    parser.add_argument("--num_pairs", type=int, default=1000,
                        help="Number of random pairs to test (default: 1000).")
    return parser.parse_args()

# -------------------------------
# Main Function
# -------------------------------

def main():
    # Parameters (adjust these as needed)
    args = parse_command_line()
    txt_dir = args.txt_dir
    ged_executable = args.ged_executable
    output_excel = args.output_excel
    dataset = args.dataset
    lb_folder = args.lb_folder
    workers = args.workers
    threshold = args.threshold
    num_pairs = args.num_pairs

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Gather all .txt files and sort.
    txt_files = [os.path.join(txt_dir, f) for f in os.listdir(txt_dir) if f.endswith('.txt')]
    txt_files.sort()
    if len(txt_files) < 2:
        print("Not enough graph files available to form pairs. Exiting.")
        sys.exit(1)

    # Generate all unique pairs.
    all_pairs = []
    n = len(txt_files)
    for i in range(n):
        for j in range(i + 1, n):
            all_pairs.append((txt_files[i], txt_files[j]))

    if len(all_pairs) < num_pairs:
        print(f"Not enough pairs available: only {len(all_pairs)} pairs. Exiting.")
        sys.exit(1)

    # Randomly select num_pairs pairs.
    random_pairs = random.sample(all_pairs, num_pairs)
    print(f"Selected {num_pairs} random pairs for testing.")

    # -------------------------------
    # Experiment 1: Baseline (Without Heuristics)
    # -------------------------------
    print("Running baseline experiment WITHOUT heuristic filtering...")
    baseline_results, baseline_time = run_experiment(
        pairs=random_pairs,
        apply_heuristic=False,
        lb_df_filter=None,
        dataset=dataset,
        threshold=threshold,
        ged_executable=ged_executable,
        num_workers=workers
    )
    print(f"Baseline experiment completed in {baseline_time:.2f} seconds.")

    baseline_summary = {
        "Experiment": "Baseline (No Heuristics)",
        "Total Pairs": num_pairs,
        "Time (s)": baseline_time,
        "Pairs Skipped": 0,
        "Pairs Processed": num_pairs,
        "Time Saved (s)": 0  # Baseline has no saving.
    }

    # -------------------------------
    # Experiment 2: With Each Heuristic
    # -------------------------------
    # Find all heuristic Excel files in lb_folder for the given dataset.
    heuristic_files = [
        f for f in os.listdir(lb_folder)
        if f.endswith(".xlsx") and f.startswith(f"{dataset}_")
    ]
    if not heuristic_files:
        print(f"No heuristic Excel files found in {lb_folder} for dataset {dataset}. Exiting.")
        sys.exit(1)

    heuristic_results_dict = {}
    summary_list = [baseline_summary]

    for file in heuristic_files:
        heuristic_path = os.path.join(lb_folder, file)
        try:
            lb_df_filter = pd.read_excel(heuristic_path)
            lb_df_filter["graph_id1"] = lb_df_filter["graph_id1"].astype(int)
            lb_df_filter["graph_id2"] = lb_df_filter["graph_id2"].astype(int)
        except Exception as e:
            print(f"Error loading heuristic file {heuristic_path}: {e}")
            continue

        # Derive heuristic name from file name.
        heuristic_name = file[len(dataset) + 1:-5]
        print(f"\nRunning experiment WITH heuristic filtering using '{heuristic_name}'...")
        results_withheur, time_withheur = run_experiment(
            pairs=random_pairs,
            apply_heuristic=True,
            lb_df_filter=lb_df_filter,
            dataset=dataset,
            threshold=threshold,
            ged_executable=ged_executable,
            num_workers=workers
        )
        skipped_count = sum(1 for r in results_withheur if r.get("skipped"))
        processed_count = num_pairs - skipped_count

        summary_entry = {
            "Experiment": f"Heuristic: {heuristic_name}",
            "Total Pairs": num_pairs,
            "Time (s)": time_withheur,
            "Pairs Skipped": skipped_count,
            "Pairs Processed": processed_count,
            "Time Saved (s)": baseline_time - time_withheur
        }
        summary_list.append(summary_entry)
        heuristic_results_dict[heuristic_name] = results_withheur
        print(f"Experiment with heuristic '{heuristic_name}' completed in {time_withheur:.2f} seconds. "
              f"Skipped: {skipped_count}, Processed: {processed_count}")

    # -------------------------------
    # Save All Results to Excel
    # -------------------------------
    save_results_excel(output_excel, baseline_results, heuristic_results_dict, summary_list)
    print(f"\nAll results have been saved to {output_excel}.")
    print("Summary:")
    for entry in summary_list:
        print(entry)


if __name__ == "__main__":
    main()
