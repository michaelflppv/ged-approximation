#!/usr/bin/env python3
import os
import json
from torch_geometric.datasets import GEDDataset


def process_graph(data):
    """
    Process a torch_geometric Data object:
      - Convert its edge_index tensor to a list of edge pairs.
      - Ensure that node indices are 0-indexed.
      - Create a list of default labels (here all zeros) for each node.
    """
    num_nodes = data.num_nodes
    if data.edge_index is not None and data.edge_index.numel() > 0:
        # Convert edge_index (shape [2, num_edges]) to a list of edges.
        edge_index = data.edge_index.cpu().numpy()
        edge_list = edge_index.transpose().tolist()
        # Re-index nodes if necessary (ensure 0-indexing).
        if edge_list:
            min_val = min(min(pair) for pair in edge_list)
            if min_val != 0:
                edge_list = [[u - min_val, v - min_val] for u, v in edge_list]
    else:
        edge_list = []
    # Since nodes are unlabeled, assign a default label (0) for every node.
    labels = [0] * num_nodes
    return edge_list, labels


def main():
    # Root directory where GED datasets will be stored.
    root_dir = '../../../data/ged'
    # Check if the processed folder exists.
    processed_dir = os.path.join(root_dir, "processed")
    if not os.path.exists(processed_dir) or len(os.listdir(processed_dir)) == 0:
        print("Processed Linux dataset not found locally in:")
        print(f"  {processed_dir}")
        print("It will be downloaded from pytorch_geometric (if available).")

    # Attempt to load the Linux dataset (training set) from pytorch_geometric.
    try:
        dataset = GEDDataset(root=root_dir, name="LINUX", train=True)
    except Exception as e:
        print("Error downloading/loading the Linux dataset from pytorch_geometric:")
        print(e)
        return

    # Filter: select only graphs with 10 or fewer nodes.
    filtered_graphs = [data for data in dataset if data.num_nodes <= 10]
    if len(filtered_graphs) >= 1000:
        filtered_graphs = filtered_graphs[:1000]
    else:
        print(f"Warning: Only found {len(filtered_graphs)} graphs with 10 or fewer nodes.")

    num_graphs = len(filtered_graphs)
    print(f"Processing {num_graphs} graphs.")

    # Directory where JSON graph pair files will be stored.
    output_dir = r"C:\project_data\simgnn_data\train"
    os.makedirs(output_dir, exist_ok=True)

    pair_count = 0
    # Create pairs: each graph is paired with every other (without repetition).
    for i in range(num_graphs):
        data1 = filtered_graphs[i]
        edge_list1, labels1 = process_graph(data1)

        for j in range(i + 1, num_graphs):
            data2 = filtered_graphs[j]
            edge_list2, labels2 = process_graph(data2)

            # Retrieve the graph edit distance (GED) using original graph indices.
            ged_value = int(dataset.ged[data1.i, data2.i])

            pair_dict = {
                "graph_1": edge_list1,
                "graph_2": edge_list2,
                "labels_1": labels1,
                "labels_2": labels2,
                "ged": ged_value
            }

            filename = f"LINUX_pair_{data1.i}_{data2.i}.json"
            file_path = os.path.join(output_dir, filename)

            with open(file_path, 'w') as f:
                json.dump(pair_dict, f)

            pair_count += 1
            if pair_count % 1000 == 0:
                print(f"Generated {pair_count} JSON files...")

    print(f"Finished generating {pair_count} JSON graph pairs in directory '{output_dir}'.")


if __name__ == "__main__":
    main()
