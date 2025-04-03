#!/usr/bin/env python3
import os
import json
import random
import itertools
import copy

# ----- Configuration -----
NUM_GRAPHS = 100  # total graph variants to generate
NUM_NODES = 5  # nodes indexed 0 to 4
MAX_MODS = 5  # each graph gets 0 to 5 modifications
BASE_LABEL = 2  # base label for every node
ALTERNATIVE_LABELS = [1, 3]  # allowed label changes (from 2)
# Base connectivity: a simple chain 0-1, 1-2, 2-3, 3-4
BASE_EDGES = {(0, 1), (1, 2), (2, 3), (3, 4)}
# For edge additions we allow any edge among nodes (u,v) with u < v that is NOT in BASE_EDGES.
ALL_POSSIBLE_EDGES = {(u, v) for u in range(NUM_NODES) for v in range(u + 1, NUM_NODES)}
ALLOWED_EDGE_ADDITIONS = ALL_POSSIBLE_EDGES - BASE_EDGES


# ----- Functions to generate graph variants -----
def create_base_graph():
    """
    Returns a dictionary representing the base graph.
    - "edges" is a list of edges (each edge is a sorted list [u, v]).
    - "labels" is a list of node labels.
    - "mods" is a set that will record modifications as tuples.
    """
    graph = {
        "edges": [list(edge) for edge in sorted(BASE_EDGES)],
        "labels": [BASE_LABEL for _ in range(NUM_NODES)],
        "mods": set()  # each modification will be a tuple, e.g., ("label", node, new_label)
    }
    return graph


def available_modifications(graph):
    """
    Returns a list of available modification operations for the current graph state.
    Three types are allowed:
      - Label modification: For any node whose label is still the base label, we can change it.
      - Edge deletion: For any edge that is in the base graph and still present, we can remove it.
      - Edge addition: For any allowed edge (not in BASE_EDGES) that is not yet present.

    Each modification is represented as a tuple:
      ("label", node, new_label)
      ("edge_del", u, v)
      ("edge_add", u, v)
    """
    mods = []
    # Label modifications: only allow a node to be modified if its label is still the base label.
    for i, lbl in enumerate(graph["labels"]):
        if lbl == BASE_LABEL:
            for new_lbl in ALTERNATIVE_LABELS:
                mods.append(("label", i, new_lbl))
    # Edge deletion: only for edges that were in the base and are still present.
    current_edges = {tuple(sorted(e)) for e in graph["edges"]}
    for edge in BASE_EDGES:
        if edge in current_edges:
            mods.append(("edge_del", edge[0], edge[1]))
    # Edge addition: allowed only for edges not in current_edges and from ALLOWED_EDGE_ADDITIONS.
    for edge in ALLOWED_EDGE_ADDITIONS:
        if edge not in current_edges:
            mods.append(("edge_add", edge[0], edge[1]))
    return mods


def apply_modification(graph, mod):
    """
    Applies a given modification operation to the graph.
    Updates the "edges" or "labels" accordingly.
    """
    mod_type = mod[0]
    if mod_type == "label":
        # mod is ("label", node, new_label)
        _, node, new_label = mod
        graph["labels"][node] = new_label
    elif mod_type == "edge_del":
        # mod is ("edge_del", u, v)
        _, u, v = mod
        # Remove the edge [u,v] (edges stored as sorted lists)
        edge = sorted([u, v])
        graph["edges"] = [e for e in graph["edges"] if sorted(e) != edge]
    elif mod_type == "edge_add":
        # mod is ("edge_add", u, v)
        _, u, v = mod
        edge = sorted([u, v])
        # Add the edge if not already present
        if edge not in [sorted(e) for e in graph["edges"]]:
            graph["edges"].append(edge)
    else:
        raise ValueError("Unknown modification type: " + mod_type)
    # Record the modification in the mods set.
    graph["mods"].add(mod)


def generate_graph_variant():
    """
    Generates one graph variant by copying the base graph and applying up to MAX_MODS modifications.
    Returns a new graph dictionary with keys "edges", "labels", and "mods".
    """
    graph = create_base_graph()
    num_mods = random.randint(0, MAX_MODS)
    for _ in range(num_mods):
        available = available_modifications(graph)
        if not available:
            break  # no further modifications available
        mod = random.choice(available)
        apply_modification(graph, mod)
    return graph


# ----- GED computation -----
def compute_ged(mods1, mods2):
    """
    Computes the graph edit distance between two graphs as the size of the symmetric difference
    between their modification sets.
    """
    common = mods1.intersection(mods2)
    return (len(mods1) + len(mods2) - 2 * len(common))


# ----- Main Script: Generate pairs in JSON -----
def main():
    random.seed(42)  # For reproducibility

    # Generate 100 graph variants
    variants = []
    for i in range(NUM_GRAPHS):
        variant = generate_graph_variant()
        # Remove the "mods" set from the graph before JSON export.
        # (We keep it here for GED computation but output only edges and labels.)
        variants.append(variant)

    # Prepare output directory for JSON files
    output_dir = "json_pairs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    pair_count = 0
    # Generate all unique pairs (i < j)
    for i, j in itertools.combinations(range(NUM_GRAPHS), 2):
        graph1 = variants[i]
        graph2 = variants[j]
        ged = compute_ged(graph1["mods"], graph2["mods"])
        # (By our construction each variant has at most MAX_MODS modifications,
        # so ged is guaranteed to be <= 10.)
        pair_data = {
            "graph_1": graph1["edges"],
            "graph_2": graph2["edges"],
            "labels_1": graph1["labels"],
            "labels_2": graph2["labels"],
            "ged": ged
        }
        # File name: pair_i_j.json (we use 0-indexing in file names, but you could add 1)
        filename = os.path.join(output_dir, f"pair_{i}_{j}.json")
        with open(filename, "w") as f:
            json.dump(pair_data, f)
        pair_count += 1

    print(f"Generated {pair_count} JSON graph pair files in '{output_dir}'.")


if __name__ == "__main__":
    main()
