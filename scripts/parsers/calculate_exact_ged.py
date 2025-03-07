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
                                timeout=10)
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


def should_skip_pair(dataset, graph_id1, graph_id2, lb_df):
    """
    Check the Excel file (lb_df) for the given dataset and graph pair (graph_id1, graph_id2)
    using a fixed heuristic ("BMao"). If the lower bound exceeds the chosen threshold,
    return True (i.e. skip the pair).

    Note: the Excel file has columns: "Dataset", "graph_id1", "graph_id2", "Heuristic", "Lower Bound".
    The graph id values in the Excel file are double, so we convert them to int before comparing.
    """
    # Choose the heuristic (hardcoded inside the function)
    heuristic = "BMao"
    # Set a threshold (you may change this value)
    threshold = 50

    try:
        id1 = int(graph_id1)
        id2 = int(graph_id2)
    except ValueError:
        print(f"Warning: could not convert graph ids {graph_id1}, {graph_id2} to int.")
        return False

    df_filtered = lb_df[(lb_df["Dataset"] == dataset) & (lb_df["Heuristic"] == heuristic)]
    # Ensure conversion to int
    df_filtered = df_filtered.copy()
    df_filtered["graph_id1"] = df_filtered["graph_id1"].astype(int)
    df_filtered["graph_id2"] = df_filtered["graph_id2"].astype(int)

    matching_rows = df_filtered[
        ((df_filtered["graph_id1"] == id1) & (df_filtered["graph_id2"] == id2)) |
        ((df_filtered["graph_id1"] == id2) & (df_filtered["graph_id2"] == id1))
        ]

    if not matching_rows.empty:
        lb_value = matching_rows.iloc[0]["Lower Bound"]
        if lb_value > threshold:
            return True

    return False


def test_all_heuristics(dataset, lb_df, graph_pairs, threshold=50):
    """
    Test how many pairs would be skipped by each heuristic (for the given dataset and threshold).
    For each unique heuristic in the lower bound Excel file for the specified dataset, this
    function iterates over the provided graph pairs and counts those that would be skipped.
    The results are printed out without affecting the processing of pairs.
    """
    # Get unique heuristics for the dataset
    heuristics = lb_df[lb_df["Dataset"] == dataset]["Heuristic"].unique()
    print("\n--- Testing All Heuristics ---")
    for heuristic in heuristics:
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

            df_filtered = lb_df[(lb_df["Dataset"] == dataset) & (lb_df["Heuristic"] == heuristic)].copy()
            df_filtered["graph_id1"] = df_filtered["graph_id1"].astype(int)
            df_filtered["graph_id2"] = df_filtered["graph_id2"].astype(int)

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
    print("--- End of Heuristic Testing ---\n")


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
    This function overwrites any existing file.
    """
    df = pd.DataFrame(results_list, columns=["graph_id_1", "graph_id_2",
                                             "min_ged", "max_ged",
                                             "runtime", "candidates", "matches"])
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    print(f"Results saved to {excel_file}")


def signal_handler(signum, frame):
    """
    Handle signals by saving partial results before exiting.
    """
    print(f"\nSignal {signum} received. Saving partial results and exiting.")
    global output_excel, results
    save_results(output_excel, results)
    sys.exit(1)


def main(txt_dir, ged_executable, output_excel_param, num_workers, dataset, lb_excel, test_heuristics):
    global output_excel, results
    output_excel = output_excel_param

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load the lower bound Excel file.
    try:
        lb_df = pd.read_excel(lb_excel)
    except Exception as e:
        print(f"Error loading lower bound Excel file {lb_excel}: {e}")
        sys.exit(1)

    # Gather all .txt files in the specified directory.
    txt_files = [os.path.join(txt_dir, f) for f in os.listdir(txt_dir) if f.endswith('.txt')]
    txt_files.sort()
    results = []

    # Generate all unique graph pairs (i < j).
    graph_pairs = [(txt_files[i], txt_files[j], ged_executable)
                   for i in range(len(txt_files)) for j in range(i + 1, len(txt_files))]
    total_pairs_initial = len(graph_pairs)
    print(f"Total graph pairs available: {total_pairs_initial}")

    """
    if 27922 >= total_pairs_initial:
        print("Not enough pairs to start processing. Exiting.")
        sys.exit(0)
    graph_pairs = graph_pairs[27922:]
    print(f"Processing {len(graph_pairs)} pairs starting from the 27922nd pair.")
    """

    test_all_heuristics(dataset, lb_df, graph_pairs, threshold=50)

    # Filter out pairs to process based on the fixed heuristic ("BMao") and threshold.
    filtered_pairs = []
    skipped_count = 0
    for pair in graph_pairs:
        file1, file2, ged_exec = pair
        id1 = get_graph_id_from_filename(file1)
        id2 = get_graph_id_from_filename(file2)
        if should_skip_pair(dataset, id1, id2, lb_df):
            print(f"Skipping pair: {file1} and {file2} (lower bound threshold exceeded)")
            skipped_count += 1
            continue
        filtered_pairs.append(pair)

    print(
        f"Skipped {skipped_count} pairs out of {len(graph_pairs)} based on the lower bound threshold (using heuristic 'BMao').")

    pool = Pool(processes=num_workers)
    try:
        for count, res in enumerate(pool.imap(process_pair, filtered_pairs), 1):
            results.append(res)
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
        save_results(output_excel, results)

    total_pairs_processed = len(filtered_pairs)
    overall_pairs = len(graph_pairs)
    print(f"Final ratio of skipped pairs to total pairs (after slicing): {skipped_count}/{overall_pairs} "
          f"({skipped_count / overall_pairs:.2%} skipped, {total_pairs_processed} processed)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute the Graph Edit Distance (GED) for all graph pairs in a directory using parallel processing.\n"
                    "Additional lower bound checking is performed using an Excel file with heuristic estimates."
    )
    parser.add_argument("txt_dir", help="Directory containing the graph txt files")
    parser.add_argument("ged_executable", help="Path to the GED executable")
    parser.add_argument("output_excel", help="Output Excel file (new file will be created)")
    parser.add_argument("--workers", type=int, default=cpu_count(),
                        help="Number of parallel workers (default: all CPU cores)")
    parser.add_argument("--dataset", required=True,
                        help="Dataset name to filter the lower bound Excel file")
    parser.add_argument("--lb_excel", required=True,
                        help="Path to the Excel file containing lower bound estimations")
    parser.add_argument("--test_heuristics", action="store_true",
                        help="If set, test all heuristics and print out how many pairs would be skipped (without filtering them).")

    args = parser.parse_args()
    main(args.txt_dir, args.ged_executable, args.output_excel, args.workers, args.dataset, args.lb_excel,
         args.test_heuristics)
