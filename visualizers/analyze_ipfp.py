import pandas as pd
import numpy as np
import os
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata

# File paths
excel_ipfp = "../results/gedlib/PROTEINS/PROTEINS_HED_results.xlsx"
excel_exact = "../results/gedlib/PROTEINS/PROTEINS_STAR_results.xlsx"
gxl_directory = "../processed_data/gxl/PROTEINS/"  # directory containing GXL files representing graphs

# Load IPFP and STAR (exact GED) data; note: we still load "runtime" but won't use it now.
df_ipfp = pd.read_excel(excel_ipfp, usecols=["graph1", "graph2", "ged", "runtime"])
df_star = pd.read_excel(excel_exact, usecols=["graph1", "graph2", "ged"])
df_star.rename(columns={"ged": "exact_ged"}, inplace=True)

# Merge exact GED values for accuracy calculation
df_ipfp = df_ipfp.merge(df_star, on=["graph1", "graph2"])

# Compute accuracy
df_ipfp["accuracy"] = abs(1 - abs(df_ipfp["ged"] - df_ipfp["exact_ged"]) / df_ipfp["exact_ged"])
df_ipfp["accuracy"] = df_ipfp["accuracy"].clip(0, 1)  # Ensure values stay between [0, 1]

# Function to parse a GXL file and extract the number of nodes
def parse_gxl_nodes(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    graph = root.find("graph")
    nodes = {node.attrib["id"] for node in graph.findall("node")}
    return len(nodes)

# Function to parse a GXL file and extract the number of edges
def parse_gxl_edges(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    graph = root.find("graph")
    edges = graph.findall("edge")
    return len(edges)

# Process graph pairs: compute average graph size (number of nodes) and average number of edges,
# and collect accuracy, filtering out rows where accuracy equals 0.
graph_sizes = []  # X-axis: average number of nodes
edge_counts = []  # Y-axis: average number of edges
accuracies = []   # Z-axis: accuracy

for _, row in df_ipfp.iterrows():
    # Convert IDs to integer to remove any trailing decimals
    graph1_id = int(row["graph1"])
    graph2_id = int(row["graph2"])
    accuracy = row["accuracy"]

    # Filter out results with 0 accuracy
    if accuracy == 0:
        continue

    # Construct file names with proper formatting: "graph_<id>.gxl"
    file1 = os.path.join(gxl_directory, f"graph_{graph1_id}.gxl")
    file2 = os.path.join(gxl_directory, f"graph_{graph2_id}.gxl")

    if os.path.exists(file1) and os.path.exists(file2):
        nodes1 = parse_gxl_nodes(file1)
        nodes2 = parse_gxl_nodes(file2)
        edges1 = parse_gxl_edges(file1)
        edges2 = parse_gxl_edges(file2)

        avg_nodes = (nodes1 + nodes2) / 2  # average number of nodes
        avg_edges = (edges1 + edges2) / 2    # average number of edges

        graph_sizes.append(avg_nodes / 12)
        edge_counts.append(avg_edges / 12)
        accuracies.append(accuracy)

# Check if any data was collected
if len(graph_sizes) == 0:
    raise ValueError("No valid graph pairs found. Check the file paths, naming conventions, and data filtering.")

# Combine data and sort by graph size then by edge count in ascending order
combined = sorted(zip(graph_sizes, edge_counts, accuracies), key=lambda x: (x[0], x[1]))
graph_sizes, edge_counts, accuracies = map(np.array, zip(*combined))

# Create a DataFrame for easier manipulation
df_combined = pd.DataFrame({
    "graph_size": graph_sizes,
    "edge_count": edge_counts,
    "accuracy": accuracies
})

# Calculate rolling mean and standard deviation
window_size = 5
df_combined["rolling_mean"] = df_combined["accuracy"].rolling(window=window_size, center=True).mean()
df_combined["rolling_std"] = df_combined["accuracy"].rolling(window=window_size, center=True).std()

# Filter out spikes
threshold = 2  # Number of standard deviations to consider as a spike
df_filtered = df_combined[
    (df_combined["accuracy"] <= df_combined["rolling_mean"] + threshold * df_combined["rolling_std"]) &
    (df_combined["accuracy"] >= df_combined["rolling_mean"] - threshold * df_combined["rolling_std"])
]

# Create a grid for interpolation over graph size and edge count
xi = np.linspace(df_filtered["graph_size"].min(), df_filtered["graph_size"].max(), 50)
yi = np.linspace(df_filtered["edge_count"].min(), df_filtered["edge_count"].max(), 50)
XI, YI = np.meshgrid(xi, yi)
ZI = griddata((df_filtered["graph_size"], df_filtered["edge_count"]), df_filtered["accuracy"], (XI, YI), method="cubic")

# Create 3D Surface Plot
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection="3d")

# Plot the interpolated surface; X=graph size, Y=average edges, Z=accuracy
surf = ax.plot_surface(XI, YI, ZI, cmap="viridis", edgecolor="k", alpha=0.8)
fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)

# Invert the axes

# Labels and formatting
ax.set_xlabel("Graph Size (Number of Nodes)", fontsize=12)
ax.set_ylabel("Average Number of Edges", fontsize=12)
ax.set_zlabel("Accuracy", fontsize=12)
ax.set_title("3D Surface Plot: Accuracy vs. Graph Size & Average Edges", fontsize=14)
ax.view_init(elev=30, azim=225)  # Adjust viewing angle for 180 degrees horizontal rotation

# Display the plot
plt.show()