#!/usr/bin/env python3
"""
tester.py

This script trains (if needed) and tests the SimGNN models using JSON graph pair files
produced by proteins_converter.py. It uses relative paths throughout.

Any NumPy RuntimeWarnings (e.g., empty slices) are suppressed.
"""

import os
import sys
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)  # Suppress NumPy warnings

import pandas as pd

from param_parser import parameter_parser
from simgnn import SimGNNTrainer
from utils import tab_printer


def main():
    # Parse command line parameters.
    args = parameter_parser()

    # Determine the directory of this script.
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Set the relative path for JSON graph pairs
    json_folder = os.path.join("..", "..", "processed_data", "json_pairs", "PROTEINS")

    # Resolve relative paths properly for training and testing data
    args.training_graphs = os.path.normpath(os.path.join(script_dir, json_folder))
    args.testing_graphs = os.path.normpath(os.path.join(script_dir, json_folder))

    # Verify that training and testing folders exist.
    if not os.path.exists(args.training_graphs):
        print(f"Error: Training graphs folder '{args.training_graphs}' does not exist.")
        sys.exit(1)
    if not os.path.exists(args.testing_graphs):
        print(f"Error: Testing graphs folder '{args.testing_graphs}' does not exist.")
        sys.exit(1)

    print(f"Using training graphs folder: {args.training_graphs}")
    print(f"Using testing graphs folder: {args.testing_graphs}")

    # Set up model save/load path in a relative directory
    model_dir = os.path.join("..", "models")
    model_dir = os.path.normpath(os.path.join(script_dir, model_dir))

    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        print(f"Created models directory: {model_dir}")

    # Define the model file path
    model_file = os.path.join(model_dir, "simgnn_model.pth")

    # If a pretrained model exists, set load_path; otherwise, set save_path to train and save.
    if os.path.exists(model_file):
        args.load_path = model_file
        print(f"Pretrained model found. Will load model from: {model_file}")
    else:
        args.load_path = None
        args.save_path = model_file
        print("No pretrained model found. The model will be trained and saved.")

    # Print parameters in tabular format.
    tab_printer(args)

    # Initialize the SimGNN trainer.
    trainer = SimGNNTrainer(args)

    # Train or load the model.
    if args.load_path:
        trainer.load()
    else:
        trainer.fit()

    # Test the model.
    performance = trainer.score()
    if performance is None:
        performance = {"predicted_ged": "N/A", "accuracy": "N/A"}

    # Save the model if it was trained.
    if args.save_path:
        trainer.save()

    # Prepare the performance output directory (relative path)
    perf_dir = os.path.join("..", "..", "results", "neural", "PROTEINS")
    perf_dir = os.path.normpath(os.path.join(script_dir, perf_dir))

    if not os.path.exists(perf_dir):
        os.makedirs(perf_dir)
        print(f"Created performance directory: {perf_dir}")

    # Create a DataFrame from the performance metrics and save to an Excel file.
    excel_file = os.path.join(perf_dir, "performance.xlsx")
    df = pd.DataFrame([performance])
    df.to_excel(excel_file, index=False)
    print(f"Performance results saved to {excel_file}")


if __name__ == "__main__":
    main()
