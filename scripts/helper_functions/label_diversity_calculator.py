import os
import glob
import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET

MAX_EXCEL_ROWS = 1048576  # Max rows per Excel sheet

def parse_gxl_labels(gxl_file):
    """
    Parse a single .gxl file named like "12.gxl" and return two sets:
      - node_labels: distinct labels for all nodes
      - edge_labels: distinct labels for all edges

    We look for node labels under <attr name="symbol">,
    and edge labels under <attr name="valence">.
    """
    tree = ET.parse(gxl_file)
    root = tree.getroot()

    node_labels = set()
    edge_labels = set()

    # --- Parse Node Labels (from <attr name="symbol">) ---
    for node in root.findall(".//node"):
        symbol_attr = node.find("./attr[@name='symbol']")
        if symbol_attr is not None:
            # Attempt string, int, float children
            symbol_str = None
            for child_tag in ["string", "int", "float"]:
                child = symbol_attr.find(child_tag)
                if child is not None and child.text:
                    symbol_str = child.text.strip()
                    break
            if symbol_str:
                node_labels.add(symbol_str)

    # --- Parse Edge Labels (from <attr name='valence'>) ---
    for edge in root.findall(".//edge"):
        valence_attr = edge.find("./attr[@name='valence']")
        if valence_attr is not None:
            valence_str = None
            for child_tag in ["string", "int", "float"]:
                child = valence_attr.find(child_tag)
                if child is not None and child.text:
                    valence_str = child.text.strip()
                    break
            if valence_str:
                edge_labels.add(valence_str)

    return node_labels, edge_labels

def custom_pairwise_median(count1, count2):
    """
    Special median rule for two distinct counts:
      - If both are 0 => return np.nan
      - If only one is 0 => return the other
      - Else => return the average
    """
    if count1 == 0 and count2 == 0:
        return np.nan
    elif count1 == 0:
        return count2
    elif count2 == 0:
        return count1
    else:
        return (count1 + count2) / 2.0

def compute_node_edge_label_diversities(dataset_dir):
    """
    1) Reads all .gxl files named "<graph_id>.gxl" in dataset_dir.
    2) For each graph, parse node/edge labels => store distinct counts.
    3) For each pair (i, j) with i < j, compute the special median for node & edge counts.
    4) Save to one or more Excel files "<dataset>_node_edge_label_diversities(...).xlsx"
       in the directory "C:\\project_data\\results\\label_diversity", splitting
       the DataFrame if it exceeds Excel's max row limit.
    """

    # Check if the dataset directory exists and is not empty
    if not os.path.exists(dataset_dir):
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    if not os.listdir(dataset_dir):
        raise ValueError(f"Dataset directory is empty: {dataset_dir}")

    # 1) Gather .gxl files in dataset_dir (files named like "12.gxl", "123.gxl", etc.)
    gxl_files = glob.glob(os.path.join(dataset_dir, "*.gxl"))
    if not gxl_files:
        raise ValueError(f"No .gxl files found in directory: {dataset_dir}")

    # 2) Parse each file => store distinct label counts
    label_info = {}
    for gxl_path in gxl_files:
        base_name = os.path.basename(gxl_path)           # e.g. "12.gxl"
        graph_id = os.path.splitext(base_name)[0]        # e.g. "12"

        node_labels, edge_labels = parse_gxl_labels(gxl_path)
        label_info[graph_id] = {
            "node_count": len(node_labels),
            "edge_count": len(edge_labels)
        }

    # 3) Build a list of records for each pair (i, j), i < j
    graph_ids = sorted(label_info.keys(), key=lambda x: str(x))
    records = []
    for i in range(len(graph_ids)):
        for j in range(i+1, len(graph_ids)):
            g1 = graph_ids[i]
            g2 = graph_ids[j]

            n1 = label_info[g1]["node_count"]
            n2 = label_info[g2]["node_count"]
            e1 = label_info[g1]["edge_count"]
            e2 = label_info[g2]["edge_count"]

            node_median = custom_pairwise_median(n1, n2)
            edge_median = custom_pairwise_median(e1, e2)

            records.append({
                "graph_id_1": str(g1),
                "graph_id_2": str(g2),
                "node_labels": node_median,
                "edge_labels": edge_median
            })

    df = pd.DataFrame(records)

    # Extract dataset name from the directory path
    dataset_name = os.path.basename(os.path.normpath(dataset_dir))

    # 4) Save Excel file(s) to "C:\project_data\results\label_diversity"
    output_dir = r"C:\project_data\results\label_diversity"
    os.makedirs(output_dir, exist_ok=True)

    # If the DataFrame fits into one sheet, save directly.
    # Otherwise, split into multiple files.
    if len(df) <= MAX_EXCEL_ROWS:
        output_file = os.path.join(output_dir, f"{dataset_name}_node_edge_label_diversities.xlsx")
        df.to_excel(output_file, index=False)
        print(f"Saved results to: {output_file}")
    else:
        # Split into chunks that fit within Excel's row limit
        chunk_size = 1_000_000  # a bit under 1,048,576 to be safe
        start = 0
        part_num = 1
        df_len = len(df)

        while start < df_len:
            end = min(start + chunk_size, df_len)
            chunk_df = df.iloc[start:end]
            chunk_file = os.path.join(
                output_dir,
                f"{dataset_name}_node_edge_label_diversities_part{part_num}.xlsx"
            )
            chunk_df.to_excel(chunk_file, index=False)
            print(f"Saved chunk {part_num} (rows {start}–{end-1}) to {chunk_file}")
            part_num += 1
            start = end


if __name__ == "__main__":
    dataset_dir = r"C:\project_data\processed_data\gxl\PROTEINS"
    compute_node_edge_label_diversities(dataset_dir)
