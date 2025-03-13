#!/usr/bin/env python3
import os
import re
import subprocess
import pandas as pd
import signal
import sys
import resource

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
        "-l", "Combined_Basic_Node_Edge_Count_Difference",  # Filtering heuristic
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
                                timeout=5)
        return result.stdout
    except subprocess.TimeoutExpired:
        return None
    except subprocess.CalledProcessError:
        return None


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
    print("\n--- Testing All Heuristics in Folder ---")
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
    print("--- End of Heuristic Testing ---\n")


def process_pair(args):
    """
    Worker function for parallel GED computation.
    """
    file1, file2, ged_executable = args
    id1, id2 = get_graph_id_from_filename(file1), get_graph_id_from_filename(file2)

    output = run_ged_executable(file1, file2, ged_executable)
    if output is None:
        # Return all N/A for this pair
        return {
            "graph_id_1": id1,
            "graph_id_2": id2,
            "min_ged": "N/A",
            "max_ged": "N/A",
            "runtime": "N/A",
            "candidates": "N/A",
            "matches": "N/A"
        }

    min_ged, max_ged, runtime, candidates, matches = parse_executable_output(output)
    return {
        "graph_id_1": id1,
        "graph_id_2": id2,
        "min_ged": min_ged,
        "max_ged": max_ged,
        "runtime": runtime,
        "candidates": candidates,
        "matches": matches
    }


def save_results(excel_file, results_list):
    """
    Save the results list to an Excel file.
    """
    df = pd.DataFrame(results_list, columns=["graph_id_1", "graph_id_2",
                                             "min_ged", "max_ged",
                                             "runtime", "candidates", "matches"])
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    # print(f"Results saved to {excel_file}")


def signal_handler(signum, frame):
    """
    Handle signals by saving partial results.
    """
    print(f"\nSignal {signum} received. Saving partial results and exiting.")
    global output_excel, results
    save_results(output_excel, results)
    sys.exit(1)


def main(txt_dir, ged_executable, output_excel_param, num_workers, dataset, lb_folder, test_heuristics):
    global output_excel, results
    output_excel = output_excel_param

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # --- Modification: Load the filtering file(s) ---
    filtering_file = os.path.join(lb_folder, f"{dataset}_Combined_Basic_Node_Edge_Count_Difference.xlsx")
    if os.path.exists(filtering_file):
        try:
            lb_df_filter = pd.read_excel(filtering_file)
            lb_df_filter["graph_id1"] = lb_df_filter["graph_id1"].astype(int)
            lb_df_filter["graph_id2"] = lb_df_filter["graph_id2"].astype(int)
        except Exception as e:
            print(f"Error loading filtering Excel file {filtering_file}: {e}")
            sys.exit(1)
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
                sys.exit(1)
        else:
            print(f"Neither {filtering_file} nor both part files found in {lb_folder}.")
            sys.exit(1)
    # ----------------------------------------------------

    # Gather all .txt files
    txt_files = [os.path.join(txt_dir, f) for f in os.listdir(txt_dir) if f.endswith('.txt')]
    txt_files.sort()
    results = []

    # Generate all unique graph pairs
    graph_pairs = [
        (txt_files[i], txt_files[j], ged_executable)
        for i in range(len(txt_files))
        for j in range(i + 1, len(txt_files))
    ]
    total_pairs_initial = len(graph_pairs)
    print(f"Total graph pairs available: {total_pairs_initial}")

    # Skip the first N pairs if needed
    skip_first = 33320
    if skip_first < len(graph_pairs):
        graph_pairs = graph_pairs[skip_first:]
    else:
        graph_pairs = []
    print(f"Skipping first {skip_first} pairs. Now {len(graph_pairs)} remain for possible processing.")

    if test_heuristics:
        test_all_heuristics_in_folder(dataset, lb_folder, graph_pairs, threshold=150)

    # On-the-fly filtering for LB > 150
    skipped_count = 0
    total_valid = 0

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

    from multiprocessing import Pool
    pool = Pool(processes=num_workers)
    try:
        for count, res in enumerate(pool.imap(process_pair, valid_pairs()), 1):
            total_valid += 1

            # ------------------- MODIFICATION: SKIP ROWS WITH ALL "N/A" -------------------
            # If the result dictionary indicates all fields are "N/A", skip it entirely.
            if all(
                    res[field] == "N/A"
                    for field in ["min_ged", "max_ged", "runtime", "candidates", "matches"]
            ):
                continue
            elif count % 10 == 0:
                print(f"{count} valid pairs processed.")
            # -----------------------------------------------------------------------------

            results.append(res)
            save_results(output_excel, results)
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

    overall_pairs = total_pairs_initial
    print(f"Final ratio of LB-skipped pairs to total pairs: {skipped_count}/{overall_pairs} "
          f"({(skipped_count / overall_pairs) if overall_pairs > 0 else 0:.2%} skipped, {total_valid} processed)")


if __name__ == "__main__":
    # Specify parameters here
    txt_dir = "/home/mfilippov/ged_data/processed_data/txt/IMDB-BINARY"
    ged_executable = "/home/mfilippov/CLionProjects/Graph_Edit_Distance/ged"
    output_excel = "/home/mfilippov/ged_data/results/exact_ged/IMDB-BINARY/results_3_ubuntu.xlsx"
    workers = 8
    dataset = "IMDB-BINARY"
    lb_folder = "/home/mfilippov/ged_data/results/lower_bound/IMDB-BINARY"
    test_heuristics = False

    main(txt_dir, ged_executable, output_excel, workers, dataset, lb_folder, test_heuristics)
