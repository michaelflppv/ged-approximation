import pandas as pd
import numpy as np
import os
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter

# File paths
excel_ipfp = "../results/gedlib/PROTEINS/PROTEINS_HED_results.xlsx"
excel_exact = "../results/gedlib/PROTEINS/PROTEINS_STAR_results.xlsx"
gxl_directory = "../processed_data/gxl/PROTEINS/"  # directory containing GXL files representing graphs

# Load IPFP and STAR (exact GED) data; note: runtime is loaded and used now.
df_ipfp = pd.read_excel(excel_ipfp, usecols=["graph1", "graph2", "ged", "runtime"])
df_star = pd.read_excel(excel_exact, usecols=["graph1", "graph2", "ged"])
df_star.rename(columns={"ged": "exact_ged"}, inplace=True)

# Merge exact GED values for accuracy calculation (not used further here, but still computed)
df_ipfp = df_ipfp.merge(df_star, on=["graph1", "graph2"])


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


# Process graph pairs: compute average graph size (number of nodes), collect runtime, and compute average density.
graph_sizes = []  # X-axis: average number of nodes
runtimes = []  # Y-axis: computation time (from Excel)
densities = []  # Z-axis: average density

for _, row in df_ipfp.iterrows():
    # Convert IDs to integer to avoid trailing decimals
    graph1_id = int(row["graph1"])
    graph2_id = int(row["graph2"])
    runtime = row["runtime"]

    file1 = os.path.join(gxl_directory, f"graph_{graph1_id}.gxl")
    file2 = os.path.join(gxl_directory, f"graph_{graph2_id}.gxl")

    if os.path.exists(file1) and os.path.exists(file2):
        nodes1 = parse_gxl_nodes(file1)
        nodes2 = parse_gxl_nodes(file2)
        edges1 = parse_gxl_edges(file1)
        edges2 = parse_gxl_edges(file2)

        # Avoid division by zero (if any graph has fewer than 2 nodes)
        if nodes1 < 2 or nodes2 < 2:
            continue

        # Compute density for each graph
        density1 = edges1 / (nodes1 * (nodes1 - 1) / 2)
        density2 = edges2 / (nodes2 * (nodes2 - 1) / 2)
        avg_density = (density1 + density2) / 2

        avg_nodes = (nodes1 + nodes2) / 2  # average number of nodes

        if avg_density <= 0:
            continue

        graph_sizes.append(avg_nodes)
        runtimes.append(runtime)
        densities.append(avg_density)

# Convert lists to numpy arrays
graph_sizes = np.array(graph_sizes)
runtimes = np.array(runtimes)
densities = np.array(densities)

# Optionally, filter out data points with runtime <= 0 or density <= 0 (if needed)
mask = (runtimes > 0) & (densities > 0)
graph_sizes = graph_sizes[mask]
runtimes = runtimes[mask]
densities = densities[mask]

# Combine data and sort by graph size, then runtime (both ascending)
combined = sorted(zip(graph_sizes, runtimes, densities), key=lambda x: (x[0], x[1]))
graph_sizes, runtimes, densities = map(np.array, zip(*combined))

# Create a grid for interpolation over graph size and computation time
xi = np.linspace(graph_sizes.min(), graph_sizes.max(), 50)
yi = np.linspace(runtimes.min(), runtimes.max(), 50)
XI, YI = np.meshgrid(xi, yi)
ZI = griddata((graph_sizes, runtimes), densities, (XI, YI), method="cubic")

# Smooth the interpolated density surface using a Gaussian filter
ZI = gaussian_filter(ZI, sigma=1)

# Create 3D Surface Plot
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection="3d")

# Plot the interpolated, smoothed surface; X=graph size, Y=runtime, Z=density
surf = ax.plot_surface(XI, YI, ZI, cmap="viridis", edgecolor="k", alpha=0.8)
fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)

# Labels and formatting
ax.set_xlabel("Graph Size (Number of Nodes)", fontsize=12)
ax.set_ylabel("Computation Time (Runtime)", fontsize=12)
ax.set_zlabel("Density", fontsize=12)
ax.set_title("3D Surface Plot: Density vs. Graph Size & Computation Time", fontsize=14)
ax.view_init(elev=30, azim=130)  # Adjust viewing angle

# Display the plot
plt.show()
