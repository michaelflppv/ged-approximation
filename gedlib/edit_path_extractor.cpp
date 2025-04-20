// edit_path_extractor.cpp

#include "src/env/ged_env.hpp"
#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <set>
#include <sstream>
#include <algorithm>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

struct GraphState {
    std::vector<bool> active;
    std::vector<std::string> labels;
    std::vector<std::vector<bool>> edgeExists;
    std::vector<std::vector<std::string>> edgeLabels;
    std::size_t numNodes;
};

std::vector<json> extractEditPath(
    const ged::ExchangeGraph<ged::GXLNodeID, ged::GXLLabel, ged::GXLLabel> &ex1,
    const ged::ExchangeGraph<ged::GXLNodeID, ged::GXLLabel, ged::GXLLabel> &ex2,
    const ged::NodeMap &node_map,
    int &nodeMatches,
    int &edgeMatches)
{
    std::vector<json> editOps;
    std::vector<ged::NodeMap::Assignment> assignments;
    node_map.as_relation(assignments);

    std::map<std::size_t, std::size_t> mapping;
    for (const auto &assign : assignments) {
        if (assign.first < ex1.num_nodes && assign.second < ex2.num_nodes) {
            mapping[assign.first] = assign.second;
        }
    }

    const std::size_t DUMMY = ged::GEDGraph::dummy_node();

    GraphState state;
    state.numNodes = ex1.num_nodes;
    state.active.resize(state.numNodes, true);
    state.labels.resize(state.numNodes, "");
    for (std::size_t i = 0; i < state.numNodes; i++) {
        std::ostringstream oss;
        if (i < ex1.node_labels.size()) {
            for (const auto &kv : ex1.node_labels[i]) {
                oss << kv.first << "=" << kv.second << ";";
            }
        }
        state.labels[i] = oss.str();
    }
    state.edgeExists.resize(state.numNodes, std::vector<bool>(state.numNodes, false));
    state.edgeLabels.resize(state.numNodes, std::vector<std::string>(state.numNodes, ""));
    for (std::size_t i = 0; i < state.numNodes; i++) {
        for (std::size_t j = i + 1; j < state.numNodes; j++) {
            if (ex1.adj_matrix[i][j] == 1) {
                state.edgeExists[i][j] = true;
                auto itEdge = ex1.edge_labels.find({i, j});
                if (itEdge != ex1.edge_labels.end()) {
                    std::ostringstream ossEdge;
                    for (const auto &kv : itEdge->second) {
                        ossEdge << kv.first << "=" << kv.second << ";";
                    }
                    state.edgeLabels[i][j] = ossEdge.str();
                }
            }
        }
    }

    for (std::size_t i = 0; i < ex1.num_nodes; i++) {
        if (i >= state.active.size() || !state.active[i])
            continue;
        json op;
        auto it = mapping.find(i);
        if (it != mapping.end() && it->second != DUMMY) {
            std::size_t target = it->second;
            std::string targetLabel;
            if (target < ex2.node_labels.size()) {
                std::ostringstream oss;
                for (const auto &kv : ex2.node_labels[target]) {
                    oss << kv.first << "=" << kv.second << ";";
                }
                targetLabel = oss.str();
            }
            if (state.labels[i] != targetLabel) {
                op["op"] = "substitute";
                op["graph1_node"] = i;
                op["graph2_node"] = target;
                op["graph1_label"] = state.labels[i];
                op["graph2_label"] = targetLabel;
                state.labels[i] = targetLabel;
            } else {
                op["op"] = "match";
                op["graph1_node"] = i;
                op["graph2_node"] = target;
                op["label"] = state.labels[i];
                nodeMatches++;
            }
            editOps.push_back(op);
        } else {
            op["op"] = "delete";
            op["graph1_node"] = i;
            op["graph1_label"] = state.labels[i];
            editOps.push_back(op);
            state.active[i] = false;
            for (std::size_t j = 0; j < state.numNodes; j++) {
                if (j == i) continue;
                std::size_t a = std::min(i, j);
                std::size_t b = std::max(i, j);
                state.edgeExists[a][b] = false;
            }
        }
    }

    std::set<std::size_t> mappedG2;
    for (const auto &p : mapping) {
        if (p.second != DUMMY) {
            mappedG2.insert(p.second);
        }
    }
    for (std::size_t j = 0; j < ex2.num_nodes; j++) {
        if (mappedG2.find(j) == mappedG2.end()) {
            if (j < state.numNodes && !state.active[j]) {
                json op;
                std::ostringstream oss;
                if (j < ex2.node_labels.size()) {
                    for (const auto &kv : ex2.node_labels[j]) {
                        oss << kv.first << "=" << kv.second << ";";
                    }
                }
                op["op"] = "insert";
                op["graph2_node"] = j;
                op["graph2_label"] = oss.str();
                editOps.push_back(op);
                state.active[j] = true;
                state.labels[j] = oss.str();
            } else if (j >= state.numNodes) {
                json op;
                std::ostringstream oss;
                if (j < ex2.node_labels.size()) {
                    for (const auto &kv : ex2.node_labels[j]) {
                        oss << kv.first << "=" << kv.second << ";";
                    }
                }
                op["op"] = "insert";
                op["graph2_node"] = j;
                op["graph2_label"] = oss.str();
                editOps.push_back(op);
                state.active.push_back(true);
                state.labels.push_back(oss.str());
                state.numNodes++;
                for (std::size_t k = 0; k < state.numNodes - 1; k++) {
                    state.edgeExists[k].push_back(false);
                    state.edgeLabels[k].push_back("");
                }
                state.edgeExists.push_back(std::vector<bool>(state.numNodes, false));
                state.edgeLabels.push_back(std::vector<std::string>(state.numNodes, ""));
            }
        }
    }

    for (std::size_t i = 0; i < ex1.num_nodes; i++) {
        for (std::size_t k = i + 1; k < ex1.num_nodes; k++) {
            if (ex1.adj_matrix[i][k] == 1) {
                json op;
                if (i < state.active.size() && k < state.active.size() &&
                    state.active[i] && state.active[k])
                {
                    std::size_t mapped_i = (mapping.count(i) ? mapping.at(i) : DUMMY);
                    std::size_t mapped_k = (mapping.count(k) ? mapping.at(k) : DUMMY);
                    if (mapped_i != DUMMY && mapped_k != DUMMY &&
                        mapped_i < ex2.num_nodes && mapped_k < ex2.num_nodes)
                    {
                        if (ex2.adj_matrix[mapped_i][mapped_k] == 1) {
                            std::string currentEdgeLabel = "";
                            if (i < state.numNodes && k < state.numNodes && state.edgeExists[i][k])
                                currentEdgeLabel = state.edgeLabels[i][k];
                            std::string targetEdgeLabel = "";
                            {
                                auto itEdge = ex2.edge_labels.find({mapped_i, mapped_k});
                                if (itEdge != ex2.edge_labels.end()) {
                                    std::ostringstream ossEdge;
                                    for (const auto &kv : itEdge->second) {
                                        ossEdge << kv.first << "=" << kv.second << ";";
                                    }
                                    targetEdgeLabel = ossEdge.str();
                                }
                            }
                            if (currentEdgeLabel != targetEdgeLabel) {
                                op["op"] = "substitute_edge";
                                op["graph1_edge"] = { i, k };
                                op["graph2_edge"] = { mapped_i, mapped_k };
                                op["graph1_label"] = currentEdgeLabel;
                                op["graph2_label"] = targetEdgeLabel;
                                state.edgeLabels[i][k] = targetEdgeLabel;
                            } else {
                                op["op"] = "match_edge";
                                op["graph1_edge"] = { i, k };
                                op["graph2_edge"] = { mapped_i, mapped_k };
                                op["label"] = currentEdgeLabel;
                                edgeMatches++;
                            }
                            editOps.push_back(op);
                        } else {
                            if (i < state.numNodes && k < state.numNodes && state.edgeExists[i][k]) {
                                op["op"] = "delete_edge";
                                op["graph1_edge"] = { i, k };
                                editOps.push_back(op);
                                state.edgeExists[i][k] = false;
                            }
                        }
                    } else {
                        if (i < state.numNodes && k < state.numNodes && state.edgeExists[i][k]) {
                            op["op"] = "delete_edge";
                            op["graph1_edge"] = { i, k };
                            op["note"] = "endpoint deleted";
                            editOps.push_back(op);
                            state.edgeExists[i][k] = false;
                        }
                    }
                }
            }
        }
    }

    for (std::size_t j = 0; j < ex2.num_nodes; j++) {
        for (std::size_t k = j + 1; k < ex2.num_nodes; k++) {
            if (ex2.adj_matrix[j][k] == 1) {
                if (j < state.active.size() && k < state.active.size() &&
                    state.active[j] && state.active[k])
                {
                    if (!(j < state.numNodes && k < state.numNodes && state.edgeExists[j][k])) {
                        json op;
                        op["op"] = "insert_edge";
                        op["graph2_edge"] = { j, k };
                        editOps.push_back(op);
                        state.edgeExists[j][k] = true;
                        std::string targetEdgeLabel = "";
                        {
                            auto itEdge = ex2.edge_labels.find({j, k});
                            if (itEdge != ex2.edge_labels.end()) {
                                std::ostringstream oss;
                                for (const auto &kv : itEdge->second) {
                                    oss << kv.first << "=" << kv.second << ";";
                                }
                                targetEdgeLabel = oss.str();
                            }
                        }
                        state.edgeLabels[j][k] = targetEdgeLabel;
                    }
                }
            }
        }
    }

    return editOps;
}

int main(int argc, char* argv[]) {
    if (argc < 5) {
        std::cerr << "Usage: " << argv[0]
                  << " <dataset_path> <collection_xml> <idx1> <idx2>\n";
        return 1;
    }

    std::string dataset_path   = argv[1];
    std::string collection_xml = argv[2];
    int idx1 = std::stoi(argv[3]);
    int idx2 = std::stoi(argv[4]);

    ged::GEDEnv<ged::GXLNodeID, ged::GXLLabel, ged::GXLLabel> ged_env;
    std::vector<ged::GEDGraph::GraphID> all_ids =
        ged_env.load_gxl_graphs(dataset_path, collection_xml);

    if (idx1 < 0 || idx1 >= static_cast<int>(all_ids.size()) ||
        idx2 < 0 || idx2 >= static_cast<int>(all_ids.size()))
    {
        std::cerr << "Error: graph indices out of range. Must be between 0 and "
                  << (all_ids.size() - 1) << std::endl;
        return 1;
    }

    ged::GEDGraph::GraphID origId1 = all_ids[idx1];
    ged::GEDGraph::GraphID origId2 = all_ids[idx2];

    auto ex1 = ged_env.get_graph(origId1, true, true, true);
    auto ex2 = ged_env.get_graph(origId2, true, true, true);

    ged::GEDGraph::GraphID newId1 = ged_env.load_exchange_graph(
        ex1,
        ged::undefined(),
        ged::Options::ExchangeGraphType::ADJ_LISTS,
        "temp1",
        "temp_class1"
    );
    ged::GEDGraph::GraphID newId2 = ged_env.load_exchange_graph(
        ex2,
        ged::undefined(),
        ged::Options::ExchangeGraphType::ADJ_LISTS,
        "temp2",
        "temp_class2"
    );

    ged_env.set_edit_costs(ged::Options::EditCosts::CONSTANT);
    ged_env.init();
    ged_env.set_method(ged::Options::GEDMethod::IPFP);
    ged_env.init_method();
    ged_env.run_method(newId1, newId2);

    double gedCost = ged_env.get_upper_bound(newId1, newId2);
    ged::NodeMap nodeMap = ged_env.get_node_map(newId1, newId2);

    auto exG1 = ged_env.get_graph(newId1, true, true, true);
    auto exG2 = ged_env.get_graph(newId2, true, true, true);

    int nodeMatches = 0;
    int edgeMatches = 0;
    std::vector<json> editPath = extractEditPath(exG1, exG2, nodeMap, nodeMatches, edgeMatches);

    json output;
    output["edit_operations"] = editPath;
    output["edit_operations_count"] = editPath.size();
    output["graph_edit_distance"] = gedCost;
    output["node_matches"] = nodeMatches;
    output["edge_matches"] = edgeMatches;

    std::cout << output.dump(2) << std::endl;

    return 0;
}