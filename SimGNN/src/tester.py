import json
import torch
from simgnn import SimGNN, SimGNNTrainer
from param_parser import parameter_parser
from utils import process_pair

# Load the JSON file
data_path = 'C:\\Users\\mikef\\PycharmProjects\\SimGNN_v3\\src\\dataset\\test\\0.json'

# Parse command line arguments
args = parameter_parser()

# Initialize the trainer and model
trainer = SimGNNTrainer(args)
trainer.setup_model()

# Process the graph pair
data = process_pair(data_path)
copy_data = trainer.transfer_to_torch(data)

# Predict the similarity score
trainer.model.eval()
with torch.no_grad():
    score = trainer.model(copy_data)

print(f"Similarity score between the graphs: {score.item() * 100:.2f}%")
print(f"Graph Edit Distance (GED) value: {data['ged']}")