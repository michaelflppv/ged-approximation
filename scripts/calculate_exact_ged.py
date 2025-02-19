#!/usr/bin/env python3
"""
calculate_exact_ged.py

This script reads the converted PROTEINS.txt file (which contains multiple graphs in the following format):

    t # <graph_label>
    v <local_vertex_id> <vertex_label>
    e <local_vertex_id1> <local_vertex_id2> <edge_label>

It then compares every unique pair of graphs by:
  1. Writing each graph (from PROTEINS.txt) into a temporary file.
  2. Calling the GED executable (e.g., "./ged -d <graph_g.txt> -q <graph_q.txt> -m pair -p astar -l LSa -g")
  3. Parsing the output to extract at least:
       - The graph identifiers (from the "t" line or from the executable’s output)
       - The computed GED value.
  4. Collecting results for all pairs and computing overall min and max GED.
  5. Saving all the results into an Excel file.

It is sufficient to parse the PROTEINS.txt file only once into memory (as a list of graph blocks),
rather than reading it twice.
"""

import os
import sys
import subprocess
import re
import tempfile
import pandas as pd
from itertools import combinations


def parse_graphs(file_path):
    """
    Parses the converted PROTEINS.txt file into a list of graph blocks.
    Each block is a list of lines corresponding to one graph.
    The first line of each block starts with 't', and we also extract an identifier.
    Returns a list of tuples: (graph_id, graph_text)
    """
    graphs = []
    current_graph = []
    current_id = None
    with open(file_path, "r") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("t "):
                # If we have a current graph, store it.
                if current_graph:
                    graphs.append((current_id, "\n".join(current_graph)))
                    current_graph = []
                # Extract graph identifier from the "t" line.
                # Format: "t # <graph_label>" - we take <graph_label> as id.
                parts = line.split()
                if len(parts) >= 3:
                    current_id = parts[2]
                else:
                    current_id = f"graph_{len(graphs) + 1}"
                current_graph.append(line)
            else:
                current_graph.append(line)
        # Add the last graph block.
        if current_graph:
            graphs.append((current_id, "\n".join(current_graph)))
    return graphs


def call_ged(graph_g_file, graph_q_file, ged_executable="./ged"):
    """
    Calls the GED executable with the given database and query files.
    Returns the raw output (as string) of the executable.
    Example command:
       ./ged -d <graph_g_file> -q <graph_q_file> -m pair -p astar -l LSa -g
    """
    command = [ged_executable, "-d", graph_g_file, "-q", graph_q_file, "-m", "pair", "-p", "astar", "-l", "LSa", "-g"]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        output = result.stdout.strip()
        return output
    except Exception as e:
        print(f"Error calling GED for files {graph_g_file} and {graph_q_file}: {e}")
        return None


def parse_ged_output(output):
    """
    Parses the output of the GED executable to extract relevant information.
    Expected output format (for example):
      METHOD=20 GRAPH1=18 GRAPH2=42531 PREDGED=132 GTGED=N/A RUNTIME=0.123 MEM=12.34
    Returns a dict with keys: method, graph1, graph2, ged, runtime, mem.
    """
    regex = re.compile(
        r"METHOD=(\d+).*?GRAPH1=(\S+).*?GRAPH2=(\S+).*?PREDGED=([\d.]+).*?RUNTIME=([\d.]+).*?MEM=([\d.]+)"
    )
    match = regex.search(output)
    if match:
        return {
            "method": int(match.group(1)),
            "graph1": match.group(2),
            "graph2": match.group(3),
            "ged": float(match.group(4)),
            "runtime": float(match.group(5)),
            "memory": float(match.group(6))
        }
    else:
        return None


def main():
    # Define paths.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    proteins_txt = "../processed_data/txt/PROTEINS/PROTEINS.txt"
    ged_executable = "/home/mfilippov/CLionProjects/Graph_Edit_Distance/ged"  # adjust if needed
    output_excel = os.path.join(script_dir, "..", "..", "results", "exact_ged_results.xlsx")

    if not os.path.exists(proteins_txt):
        print(f"Error: {proteins_txt} not found.")
        sys.exit(1)

    # Parse the PROTEINS.txt file once.
    graphs = parse_graphs(proteins_txt)
    num_graphs = len(graphs)
    print(f"Parsed {num_graphs} graphs from PROTEINS.txt.")

    # We'll collect results as a list of dicts.
    results = []
    overall_min_ged = float("inf")
    overall_max_ged = float("-inf")

    # For each unique pair of graphs:
    pair_count = 0
    total_pairs = num_graphs * (num_graphs - 1) // 2
    print(f"Processing {total_pairs} graph pairs...")

    # Use combinations from itertools.
    for (id1, graph1_text), (id2, graph2_text) in combinations(graphs, 2):
        pair_count += 1
        # Create temporary files for the two graphs.
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp_g:
            tmp_g.write(graph1_text)
            file_g = tmp_g.name
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp_q:
            tmp_q.write(graph2_text)
            file_q = tmp_q.name

        # Call the GED executable.
        output = call_ged(file_g, file_q, ged_executable=ged_executable)

        # Clean up the temporary files.
        os.remove(file_g)
        os.remove(file_q)

        if output is None:
            continue

        parsed = parse_ged_output(output)
        if parsed is None:
            print(f"Warning: Could not parse output for pair ({id1}, {id2}). Output was:\n{output}")
            continue

        # For reporting, we include the pair identifiers and the GED value.
        results.append({
            "Graph1 ID": id1,
            "Graph2 ID": id2,
            "GED": parsed["ged"],
            "Runtime (s)": parsed["runtime"],
            "Memory Usage (MB)": parsed["memory"],
        })

        # Update overall min and max GED.
        if parsed["ged"] < overall_min_ged:
            overall_min_ged = parsed["ged"]
        if parsed["ged"] > overall_max_ged:
            overall_max_ged = parsed["ged"]

        # Optionally print progress.
        if pair_count % 10 == 0:
            print(f"Processed {pair_count}/{total_pairs} pairs...", end="\r")

    print(f"\nProcessed {pair_count} pairs.")
    print(f"Overall min GED: {overall_min_ged}, max GED: {overall_max_ged}")

    # Create a DataFrame and add overall min and max as extra rows.
    df = pd.DataFrame(results)
    summary = pd.DataFrame({
        "Graph1 ID": ["Overall"],
        "Graph2 ID": ["min GED / max GED"],
        "GED": [f"{overall_min_ged} / {overall_max_ged}"],
        "Runtime (s)": [""],
        "Memory Usage (MB)": [""]
    })
    df_final = pd.concat([df, summary], ignore_index=True)

    # Ensure the output directory exists.
    output_dir = os.path.dirname(output_excel)
    os.makedirs(output_dir, exist_ok=True)

    df_final.to_excel(output_excel, index=False)
    print(f"Results saved to {output_excel}")


if __name__ == "__main__":
    main()
