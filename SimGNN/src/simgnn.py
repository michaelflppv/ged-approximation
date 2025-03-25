import glob
import torch
import random
import numpy as np
from tqdm import tqdm, trange
from torch_geometric.nn import GCNConv
from layers import AttentionModule, TenorNetworkModule
from utils import process_pair, calculate_loss, calculate_normalized_ged

class SimGNN(torch.nn.Module):
    """
    SimGNN: A Neural Network Approach to Fast Graph Similarity Computation
    https://arxiv.org/abs/1808.05689
    """
    def __init__(self, args, number_of_labels):
        """
        :param args: Arguments object.
        :param number_of_labels: Number of node labels.
        """
        super(SimGNN, self).__init__()
        self.args = args
        self.number_labels = number_of_labels
        self.setup_layers()

    def calculate_bottleneck_features(self):
        """
        Deciding the shape of the bottleneck layer.
        """
        if self.args.histogram:
            self.feature_count = self.args.tensor_neurons + self.args.bins
        else:
            self.feature_count = self.args.tensor_neurons

    def setup_layers(self):
        """
        Creating the layers.
        """
        self.calculate_bottleneck_features()
        self.convolution_1 = GCNConv(self.number_labels, self.args.filters_1)
        self.convolution_2 = GCNConv(self.args.filters_1, self.args.filters_2)
        self.convolution_3 = GCNConv(self.args.filters_2, self.args.filters_3)
        self.attention = AttentionModule(self.args)
        self.tensor_network = TenorNetworkModule(self.args)
        self.fully_connected_first = torch.nn.Linear(self.feature_count,
                                                     self.args.bottle_neck_neurons)
        self.scoring_layer = torch.nn.Linear(self.args.bottle_neck_neurons, 1)

    def calculate_histogram(self, abstract_features_1, abstract_features_2):
        """
        Calculate histogram from similarity matrix.
        """
        scores = torch.mm(abstract_features_1, abstract_features_2).detach()
        scores = scores.view(-1, 1)
        hist = torch.histc(scores, bins=self.args.bins)
        hist = hist / torch.sum(hist)
        hist = hist.view(1, -1)
        return hist

    def convolutional_pass(self, edge_index, features):
        """
        Making convolutional pass.
        """
        features = self.convolution_1(features, edge_index)
        features = torch.nn.functional.relu(features)
        features = torch.nn.functional.dropout(features,
                                               p=self.args.dropout,
                                               training=self.training)

        features = self.convolution_2(features, edge_index)
        features = torch.nn.functional.relu(features)
        features = torch.nn.functional.dropout(features,
                                               p=self.args.dropout,
                                               training=self.training)

        features = self.convolution_3(features, edge_index)
        return features

    def forward(self, data):
        """
        Forward pass with graphs.
        """
        edge_index_1 = data["edge_index_1"]
        edge_index_2 = data["edge_index_2"]
        features_1 = data["features_1"]
        features_2 = data["features_2"]

        abstract_features_1 = self.convolutional_pass(edge_index_1, features_1)
        abstract_features_2 = self.convolutional_pass(edge_index_2, features_2)

        if self.args.histogram:
            hist = self.calculate_histogram(abstract_features_1,
                                            torch.t(abstract_features_2))

        pooled_features_1 = self.attention(abstract_features_1)
        pooled_features_2 = self.attention(abstract_features_2)
        scores = self.tensor_network(pooled_features_1, pooled_features_2)
        scores = torch.t(scores)

        if self.args.histogram:
            scores = torch.cat((scores, hist), dim=1).view(1, -1)

        scores = torch.nn.functional.relu(self.fully_connected_first(scores))
        score = torch.sigmoid(self.scoring_layer(scores))
        return score

class SimGNNTrainer(object):
    """
    SimGNN model trainer.
    """
    def __init__(self, args):
        """
        :param args: Arguments object.
        """
        self.args = args
        self.initial_label_enumeration()
        self.setup_model()

    def setup_model(self):
        """
        Creating a SimGNN.
        """
        self.model = SimGNN(self.args, self.number_of_labels)

    def initial_label_enumeration(self):
        """
        Collecting the unique node identifiers.
        """
        print("\nEnumerating unique labels.\n")
        # Fixing path concatenation using os.path.join would be ideal.
        self.training_graphs = glob.glob(self.args.training_graphs + r"\*.json")
        self.testing_graphs = glob.glob(self.args.testing_graphs + r"\*.json")
        graph_pairs = self.training_graphs + self.testing_graphs
        self.global_labels = set()
        for graph_pair in tqdm(graph_pairs):
            data = process_pair(graph_pair)
            labels_1 = {str(label) for label in data["labels_1"]}
            labels_2 = {str(label) for label in data["labels_2"]}
            self.global_labels = self.global_labels.union(labels_1)
            self.global_labels = self.global_labels.union(labels_2)
        self.global_labels = sorted(self.global_labels, key=lambda x: x)
        self.global_labels = {val: index for index, val in enumerate(self.global_labels)}
        self.number_of_labels = len(self.global_labels)

    def create_batches_from(self, graph_list):
        """
        Creating batches from a provided list of graph file paths.
        """
        random.shuffle(graph_list)
        batches = []
        for i in range(0, len(graph_list), self.args.batch_size):
            batches.append(graph_list[i:i+self.args.batch_size])
        return batches

    def transfer_to_torch(self, data):
        """
        Transferring the data to torch and creating a hash table.
        """
        new_data = dict()
        # Create undirected edges by adding reverse edges.
        edges_1 = data["graph_1"] + [[y, x] for x, y in data["graph_1"]]
        edges_2 = data["graph_2"] + [[y, x] for x, y in data["graph_2"]]

        edges_1 = torch.from_numpy(np.array(edges_1, dtype=np.int64).T).type(torch.long)
        edges_2 = torch.from_numpy(np.array(edges_2, dtype=np.int64).T).type(torch.long)

        features_1, features_2 = [], []

        for n in data["labels_1"]:
            n_str = str(n)
            features_1.append([1.0 if self.global_labels[n_str] == i else 0.0
                               for i in self.global_labels.values()])

        for n in data["labels_2"]:
            n_str = str(n)
            features_2.append([1.0 if self.global_labels[n_str] == i else 0.0
                               for i in self.global_labels.values()])

        features_1 = torch.FloatTensor(np.array(features_1))
        features_2 = torch.FloatTensor(np.array(features_2))

        new_data["edge_index_1"] = edges_1
        new_data["edge_index_2"] = edges_2
        new_data["features_1"] = features_1
        new_data["features_2"] = features_2

        norm_ged = data["ged"] / (0.5 * (len(data["labels_1"]) + len(data["labels_2"])))
        new_data["target"] = torch.from_numpy(np.exp(-norm_ged).reshape(1, 1)).view(-1).float()
        return new_data

    def process_batch(self, batch):
        """
        Forward pass with a batch of data.
        """
        self.optimizer.zero_grad()
        losses = 0
        for graph_pair in batch:
            data = process_pair(graph_pair)
            data = self.transfer_to_torch(data)
            target = data["target"]
            prediction = self.model(data)
            losses += torch.nn.functional.mse_loss(target, prediction)
        losses.backward(retain_graph=True)
        self.optimizer.step()
        loss = losses.item()
        return loss

    def validate(self):
        """
        Evaluate the model on the validation set.
        """
        self.model.eval()
        losses = []
        for graph_pair in self.val_graphs:
            data = process_pair(graph_pair)
            data = self.transfer_to_torch(data)
            target = data["target"]
            prediction = self.model(data)
            loss_val = torch.nn.functional.mse_loss(target, prediction).item()
            losses.append(loss_val)
        avg_loss = np.mean(losses)
        self.model.train()
        return avg_loss

    def fit(self):
        """
        Iteration-based training with validation.
        """
        print("\nModel training.\n")
        self.optimizer = torch.optim.Adam(self.model.parameters(),
                                          lr=self.args.learning_rate,
                                          weight_decay=self.args.weight_decay)
        self.model.train()

        # Split the training graphs into training and validation sets (80/20 split)
        random.shuffle(self.training_graphs)
        num_val = int(0.2 * len(self.training_graphs))
        self.val_graphs = self.training_graphs[:num_val]
        self.train_graphs = self.training_graphs[num_val:]

        total_iterations = self.args.iterations
        val_interval = self.args.val_interval
        iteration = 0
        best_val_loss = float('inf')
        best_model_state = None

        pbar = trange(total_iterations, desc="Training Iterations")
        while iteration < total_iterations:
            batches = self.create_batches_from(self.train_graphs)
            for batch in batches:
                loss_score = self.process_batch(batch)
                iteration += 1
                pbar.update(1)
                if iteration % val_interval == 0:
                    val_loss = self.validate()
                    pbar.set_description(f"Iter {iteration} | Val Loss: {val_loss:.5f}")
                    if val_loss < best_val_loss:
                        best_val_loss = val_loss
                        best_model_state = self.model.state_dict()
                if iteration >= total_iterations:
                    break
        pbar.close()
        if best_model_state is not None:
            self.model.load_state_dict(best_model_state)

    def score(self):
        """
        Scoring on the test set.
        """
        print("\n\nModel evaluation.\n")
        self.model.eval()
        self.scores = []
        self.ground_truth = []
        for graph_pair in tqdm(self.testing_graphs):
            data = process_pair(graph_pair)
            self.ground_truth.append(calculate_normalized_ged(data))
            data = self.transfer_to_torch(data)
            target = data["target"]
            prediction = self.model(data)
            self.scores.append(calculate_loss(prediction, target))
        self.print_evaluation()

    def print_evaluation(self):
        """
        Printing the error rates.
        """
        norm_ged_mean = np.mean(self.ground_truth)
        base_error = np.mean([(n - norm_ged_mean) ** 2 for n in self.ground_truth])
        model_error = np.mean(self.scores)
        print("\nBaseline error: " + str(round(base_error, 5)) + ".")
        print("\nModel test error: " + str(round(model_error, 5)) + ".")

    def save(self):
        torch.save(self.model.state_dict(), self.args.save_path)

    def load(self):
        self.model.load_state_dict(torch.load(self.args.load_path))
