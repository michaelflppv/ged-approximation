#!/usr/bin/env python3
import os
import re
import subprocess
import pandas as pd
import signal
import sys
import resource
import time
import numpy as np
import psutil
import multiprocessing
from multiprocessing import Process

# Global variables so signal handlers can access the results and output filename.
results = []
output_excel = None

def process_dataset(dataset_name):
    """
    Process a single dataset completely.
    """
    print(f"Starting processing for dataset: {dataset_name}")

    # Set paths for this dataset
    txt_dir = f"../../processed_data/txt/{dataset_name}"
    ged_executable = "../../Graph_Edit_Distance/ged"
    output_excel = f"../../results/exact_ged/{dataset_name}/results.xlsx"
    workers = max(1, multiprocessing.cpu_count() // 3)  # Divide CPU cores between 3 datasets
    lb_folder = f"../../results/lower_bound/{dataset_name}"
    test_heuristics = False

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_excel), exist_ok=True)

    # Call the main function with dataset-specific parameters
    main(txt_dir, ged_executable, output_excel, workers, dataset_name, lb_folder, test_heuristics)


def main(txt_dir, ged_executable, output_excel_param, num_workers, dataset, lb_folder, test_heuristics):
    # Global variables for this process
    results = []
    output_excel = output_excel_param

    # Set up signal handlers
    signal.signal(signal.SIGINT, lambda signum, frame: signal_handler_local(signum, frame, output_excel, results))
    signal.signal(signal.SIGTERM, lambda signum, frame: signal_handler_local(signum, frame, output_excel, results))

    # --- Load the filtering file(s) ---
    filtering_file = os.path.join(lb_folder, f"{dataset}_Combined_Basic_Node_Edge_Count_Difference.xlsx")
    if os.path.exists(filtering_file):
        try:
            lb_df_filter = pd.read_excel(filtering_file)
            lb_df_filter["graph_id1"] = lb_df_filter["graph_id1"].astype(int)
            lb_df_filter["graph_id2"] = lb_df_filter["graph_id2"].astype(int)
        except Exception as e:
            print(f"Error loading filtering Excel file {filtering_file}: {e}")
            return
    else:
        # Check for part1 and part2 files
        part1_file = os.path.join(lb_folder, f"{dataset}_Combined_Basic_Node_Edge_Count_Difference_part1.xlsx")
        part2_file = os.path.join(lb_folder, f"{dataset}_Combined_Basic_Node_Edge_Count_Difference_part2.xlsx")
        if os.path.exists(part1_file) and os.path.exists(part2_file):
            try:
                lb_df_part1 = pd.read_excel(part1_file)
                lb_df_part1["graph_id1"] = lb_df_part1["graph_id1"].astype(int)
                lb_df_part1["graph_id2"] = lb_df_part1["graph_id2"].astype(int)
                lb_df_part2 = pd.read_excel(part2_file)
                lb_df_part2["graph_id1"] = lb_df_part2["graph_id1"].astype(int)
                lb_df_part2["graph_id2"] = lb_df_part2["graph_id2"].astype(int)
                # Do not merge the parts; instead, use a list of DataFrames.
                lb_df_filter = [lb_df_part1, lb_df_part2]
            except Exception as e:
                print(f"Error loading part files: {e}")
                return
        else:
            print(f"Neither {filtering_file} nor both part files found in {lb_folder}.")
            return

    # Gather all .txt files
    if not os.path.exists(txt_dir):
        print(f"Text directory {txt_dir} not found. Skipping dataset {dataset}.")
        return

    txt_files = [os.path.join(txt_dir, f) for f in os.listdir(txt_dir) if f.endswith('.txt')]
    if not txt_files:
        print(f"No text files found in {txt_dir}. Skipping dataset {dataset}.")
        return

    txt_files.sort()

    # Generate all unique graph pairs
    graph_pairs = [
        (txt_files[i], txt_files[j], ged_executable)
        for i in range(len(txt_files))
        for j in range(i + 1, len(txt_files))
    ]
    total_pairs_initial = len(graph_pairs)
    print(f"{dataset}: Total graph pairs available: {total_pairs_initial}")

    # Limit to 100000 pairs
    max_pairs = 100000
    if len(graph_pairs) > max_pairs:
        import random
        random.seed(42)  # For reproducibility
        graph_pairs = random.sample(graph_pairs, max_pairs)
        print(f"{dataset}: Limited to {max_pairs} randomly selected pairs")

    if test_heuristics:
        test_all_heuristics_in_folder(dataset, lb_folder, graph_pairs, threshold=150)

    # On-the-fly filtering for LB > 150
    skipped_count = 0
    total_valid = 0
    total_runtime = 0
    total_memory = 0
    runtimes = []
    memory_usages = []

    def valid_pairs():
        nonlocal skipped_count
        for pair in graph_pairs:
            file1, file2, ged_exec = pair
            id1 = get_graph_id_from_filename(file1)
            id2 = get_graph_id_from_filename(file2)
            if should_skip_pair(dataset, id1, id2, lb_df_filter, threshold=150):
                skipped_count += 1
            else:
                yield pair

    # Create a worker pool for this dataset
    from multiprocessing import Pool
    pool = Pool(processes=num_workers)
    try:
        for count, res in enumerate(pool.imap(process_pair, valid_pairs()), 1):
            total_valid += 1

            # Skip rows with all "N/A"
            if all(
                    res[field] == "N/A"
                    for field in ["min_ged", "max_ged", "runtime", "candidates", "matches", "memory_usage_mb"]
            ):
                continue

            # Track statistics
            if res["runtime"] != "N/A":
                total_runtime += res["runtime"]
                runtimes.append(res["runtime"])

            if res["memory_usage_mb"] != "N/A":
                total_memory += res["memory_usage_mb"]
                memory_usages.append(res["memory_usage_mb"])

            if count % 10 == 0:
                print(f"{dataset}: {count} valid pairs processed.")

            results.append(res)
            save_results(output_excel, results)

            # Stop after processing 5000 valid pairs
            if count >= max_pairs:
                print(f"{dataset}: Reached limit of {max_pairs} pairs. Stopping.")
                break

    except KeyboardInterrupt:
        print(f"{dataset}: KeyboardInterrupt caught. Terminating pool and saving partial results.")
        pool.terminate()
        pool.join()
        save_results(output_excel, results)
    except Exception as e:
        print(f"{dataset}: An error occurred: {e}")
        pool.terminate()
        pool.join()
        save_results(output_excel, results)
    else:
        pool.close()
        pool.join()
    finally:
        save_results(output_excel, results)

        # Print statistics
        valid_results = len(runtimes)
        if valid_results > 0:
            avg_runtime = total_runtime / valid_results
            avg_memory = total_memory / valid_results

            if len(runtimes) > 1:
                std_runtime = np.std(runtimes)
                std_memory = np.std(memory_usages)
            else:
                std_runtime = 0
                std_memory = 0

            print(f"\n--- {dataset} Performance Statistics ---")
            print(f"Total runtime: {total_runtime:.2f} seconds")
            print(f"Average runtime: {avg_runtime:.4f} seconds (std: {std_runtime:.4f})")
            print(f"Total memory usage: {total_memory:.2f} MB")
            print(f"Average memory usage: {avg_memory:.2f} MB (std: {std_memory:.2f})")
            print("----------------------------")

    overall_pairs = min(total_pairs_initial, max_pairs)
    print(f"{dataset}: Final ratio of LB-skipped pairs to total pairs: {skipped_count}/{overall_pairs} "
          f"({(skipped_count / overall_pairs) if overall_pairs > 0 else 0:.2%} skipped, {total_valid} processed)")


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


def run_ged_executable_with_memory(graph_file1, graph_file2, ged_executable):
    """
    Call the GED executable for a single pair of graphs and measure runtime and memory usage.
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
        "-l", "BMao",  # Filtering heuristic
        "-t", "-1",
        "-g"
    ]

    try:
        start_time = time.time()
        process = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                preexec_fn=set_unlimited)

        # Monitor memory usage
        max_memory_mb = 0
        process_psutil = psutil.Process(process.pid)

        while process.poll() is None:
            try:
                # Get memory info in MB
                memory_info = process_psutil.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
                max_memory_mb = max(max_memory_mb, memory_mb)
                time.sleep(0.1)  # Poll every 100ms

                # Check for timeout
                if time.time() - start_time > 30:  # 30 second timeout
                    process.kill()
                    return None, None, None

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process has already terminated
                break

        stdout, _ = process.communicate()
        end_time = time.time()
        runtime = end_time - start_time

        if process.returncode != 0:
            return None, None, None

        return stdout, runtime, max_memory_mb

    except Exception as e:
        print(f"Error running subprocess: {e}")
        return None, None, None


def get_graph_id_from_filename(filename):
    """
    Extract the graph id from the filename.
    """
    base = os.path.basename(filename)
    match = re.match(r"graph_(\d+)\.txt", base)
    return match.group(1) if match else base


def should_skip_pair(dataset, graph_id1, graph_id2, lb_df, threshold=150):
    """
    Check the filtering Excel file(s) for the given dataset and graph pair (graph_id1, graph_id2).
    Returns True if the "Lower Bound" exceeds the threshold.

    If lb_df is a list (i.e. loaded from part1 and part2 files), check each one.
    """
    try:
        id1 = int(graph_id1)
        id2 = int(graph_id2)
    except ValueError:
        print(f"Warning: could not convert graph ids {graph_id1}, {graph_id2} to int.")
        return False

    # If lb_df is a list, iterate over each DataFrame
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


def test_all_heuristics_in_folder(dataset, lb_folder, graph_pairs, threshold=150):
    """
    For every Excel file in lb_folder starting with the dataset name,
    load its lower bound info and test how many pairs would be skipped if that heuristic were used.
    """
    print(f"\n--- Testing All Heuristics in Folder for {dataset} ---")
    for filename in os.listdir(lb_folder):
        if filename.endswith(".xlsx") and filename.startswith(f"{dataset}_"):
            file_path = os.path.join(lb_folder, filename)
            try:
                df = pd.read_excel(file_path)
                df["graph_id1"] = df["graph_id1"].astype(int)
                df["graph_id2"] = df["graph_id2"].astype(int)
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
                continue

            heuristic = filename[len(dataset) + 1:-5]
            skip_count = 0
            evaluated_count = 0
            for pair in graph_pairs:
                file1, file2, _ = pair
                id1 = get_graph_id_from_filename(file1)
                id2 = get_graph_id_from_filename(file2)
                try:
                    id1_int = int(id1)
                    id2_int = int(id2)
                except ValueError:
                    continue

                df_filtered = df.copy()
                matching_rows = df_filtered[
                    ((df_filtered["graph_id1"] == id1_int) & (df_filtered["graph_id2"] == id2_int)) |
                    ((df_filtered["graph_id1"] == id2_int) & (df_filtered["graph_id2"] == id1_int))
                    ]

                if not matching_rows.empty:
                    evaluated_count += 1
                    lb_value = matching_rows.iloc[0]["Lower Bound"]
                    if lb_value > threshold:
                        skip_count += 1

            if evaluated_count > 0:
                ratio = skip_count / evaluated_count
                print(
                    f"Heuristic '{heuristic}': Would skip {skip_count} out of {evaluated_count} evaluated pairs ({ratio:.2%}).")
            else:
                print(f"Heuristic '{heuristic}': No matching pairs found for evaluation.")
    print(f"--- End of Heuristic Testing for {dataset} ---\n")


def process_pair(args):
    """
    Worker function for parallel GED computation.
    """
    file1, file2, ged_executable = args
    id1, id2 = get_graph_id_from_filename(file1), get_graph_id_from_filename(file2)

    output, runtime_measured, memory_mb = run_ged_executable_with_memory(file1, file2, ged_executable)
    if output is None:
        # Return all N/A for this pair
        return {
            "graph_id_1": id1,
            "graph_id_2": id2,
            "min_ged": "N/A",
            "max_ged": "N/A",
            "runtime": "N/A",
            "candidates": "N/A",
            "matches": "N/A",
            "memory_usage_mb": "N/A"
        }

    min_ged, max_ged, parsed_time, candidates, matches = parse_executable_output(output)

    return {
        "graph_id_1": id1,
        "graph_id_2": id2,
        "min_ged": min_ged,
        "max_ged": max_ged,
        "runtime": runtime_measured,  # Use the directly measured runtime
        "candidates": candidates,
        "matches": matches,
        "memory_usage_mb": memory_mb
    }


def save_results(excel_file, results_list):
    """
    Save the results list to an Excel file.
    """
    df = pd.DataFrame(results_list, columns=["graph_id_1", "graph_id_2",
                                            "min_ged", "max_ged",
                                            "runtime", "candidates", "matches",
                                            "memory_usage_mb"])
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)


def signal_handler_local(signum, frame, excel_file, results_list):
    """
    Handle signals by saving partial results.
    """
    print(f"\nSignal {signum} received. Saving partial results and exiting.")
    save_results(excel_file, results_list)
    sys.exit(1)


if __name__ == "__main__":
    # List of datasets to process in parallel
    datasets = ["AIDS", "IMDB-BINARY", "PROTEINS"]

    # Start a separate process for each dataset
    processes = []
    for dataset_name in datasets:
        p = Process(target=process_dataset, args=(dataset_name,))
        p.start()
        processes.append(p)
        print(f"Started process for dataset: {dataset_name}")

    # Wait for all processes to complete
    for p in processes:
        p.join()

    print("All datasets processed!")