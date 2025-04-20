// Created by mfilippov on 11.02.25.
// Modified to allow specifying the GED method as a command-line argument
// and to choose either the lower or upper bound based on the method.
// Example usage:
//   ./edit_path_exec <dataset_path> <collection_xml> <ged_method>
//
#define GXL_GEDLIB_SHARED
#include "main.h"
#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "Usage: " << argv[0] << " <dataset_path> <collection_xml> <ged_method>" << std::endl;
        return 1;
    }

    std::string dataset_path = argv[1];
    std::string collection_xml = argv[2];
    std::string method_str = argv[3];

    // Convert method_str to uppercase for case-insensitive matching.
    std::transform(method_str.begin(), method_str.end(), method_str.begin(), ::toupper);

    // Disallow methods that are not intended for approximating GED.
    if (method_str == "RING_ML" || method_str == "BIPARTITE_ML") {
        std::cerr << "Method " << method_str << " should not be used for approximating GED." << std::endl;
        return 1;
    }

    // Mapping from string to GEDMethod enum value.
    std::unordered_map<std::string, ged::Options::GEDMethod> method_map = {
        {"BRANCH",              ged::Options::GEDMethod::BRANCH},
        {"BRANCH_FAST",         ged::Options::GEDMethod::BRANCH_FAST},
        {"BRANCH_TIGHT",        ged::Options::GEDMethod::BRANCH_TIGHT},
        {"BRANCH_UNIFORM",      ged::Options::GEDMethod::BRANCH_UNIFORM},
        {"BRANCH_COMPACT",      ged::Options::GEDMethod::BRANCH_COMPACT},
        {"PARTITION",           ged::Options::GEDMethod::PARTITION},
        {"HYBRID",              ged::Options::GEDMethod::HYBRID},
        {"RING",                ged::Options::GEDMethod::RING},
        {"ANCHOR_AWARE_GED",    ged::Options::GEDMethod::ANCHOR_AWARE_GED},
        {"WALKS",               ged::Options::GEDMethod::WALKS},
        {"IPFP",                ged::Options::GEDMethod::IPFP},
        {"BIPARTITE",           ged::Options::GEDMethod::BIPARTITE},
        {"SUBGRAPH",            ged::Options::GEDMethod::SUBGRAPH},
        {"NODE",                ged::Options::GEDMethod::NODE},
        // {"RING_ML",          ged::Options::GEDMethod::RING_ML},       // Not allowed
        // {"BIPARTITE_ML",     ged::Options::GEDMethod::BIPARTITE_ML},      // Not allowed
        {"REFINE",              ged::Options::GEDMethod::REFINE},
        {"BP_BEAM",             ged::Options::GEDMethod::BP_BEAM},
        {"SIMULATED_ANNEALING", ged::Options::GEDMethod::SIMULATED_ANNEALING},
        {"HED",                 ged::Options::GEDMethod::HED},
        {"STAR",                ged::Options::GEDMethod::STAR}
    };

    if (method_map.find(method_str) == method_map.end()) {
        std::cerr << "Invalid GED method: " << method_str << std::endl;
        return 1;
    }
    ged::Options::GEDMethod method = method_map[method_str];

    // Determine whether to use lower or upper bound based on the method.
    // Lower bound methods: only lower bound or both available (choose lower)
    std::unordered_set<std::string> lowerBoundMethods = {
        "BRANCH", "BRANCH_FAST", "BRANCH_TIGHT", "BRANCH_UNIFORM",
        "BRANCH_COMPACT", "PARTITION", "HYBRID", "ANCHOR_AWARE_GED",
        "SIMULATED_ANNEALING", "HED", "BIPARTITE", "NODE", "STAR"
    };
    // Upper bound methods: only upper bound
    std::unordered_set<std::string> upperBoundMethods = {
        "RING", "WALKS", "IPFP", "SUBGRAPH", "REFINE", "BP_BEAM"
    };

    bool use_lower_bound = false;
    if (lowerBoundMethods.find(method_str) != lowerBoundMethods.end()) {
        use_lower_bound = true;
    } else if (upperBoundMethods.find(method_str) != upperBoundMethods.end()) {
        use_lower_bound = false;
    } else {
        // This should not happen if the mapping is consistent.
        std::cerr << "Method " << method_str << " does not belong to a recognized bound category." << std::endl;
        return 1;
    }

    // Create and initialize GED environment.
    ged::GEDEnv<ged::GXLNodeID, ged::GXLLabel, ged::GXLLabel> ged_env;
    std::vector<ged::GEDGraph::GraphID> new_ids =
        ged_env.load_gxl_graphs(dataset_path, collection_xml);

    ged_env.set_edit_costs(ged::Options::EditCosts::CONSTANT);
    ged_env.init();

    // Set the selected method with additional options (example: setting threads)
    ged_env.set_method(method, "--threads 8");
    ged_env.init_method();

    // Loop over all pairs of graphs (i < j)
    for (size_t i = 1010; i < new_ids.size(); i++) {
        for (size_t j = i + 1; j < new_ids.size(); j++) {
            // Measure time before running the GED method.
            auto start_time = std::chrono::high_resolution_clock::now();

            // Run the selected GED method on the pair (new_ids[i], new_ids[j])
            ged_env.run_method(new_ids[i], new_ids[j]);

            // Measure time after running the GED method.
            auto end_time = std::chrono::high_resolution_clock::now();
            double runtime_sec = std::chrono::duration<double>(end_time - start_time).count();

            // Retrieve the GED approximation (lower or upper bound based on the method)
            double ged_value = use_lower_bound ?
                               ged_env.get_lower_bound(new_ids[i], new_ids[j]) :
                               ged_env.get_upper_bound(new_ids[i], new_ids[j]);

            // Print the result in the expected format:
            //   METHOD=... GRAPH1=... GRAPH2=... PREDGED=... GTGED=N/A RUNTIME=... MEM=...
            std::cout << "METHOD=" << static_cast<int>(method)
                      << " GRAPH1=" << new_ids[i]
                      << " GRAPH2=" << new_ids[j]
                      << " PREDGED=" << ged_value
                      << " GTGED=N/A"
                      << " RUNTIME=" << runtime_sec
                      << std::endl;
        }
    }

    return 0;
}
