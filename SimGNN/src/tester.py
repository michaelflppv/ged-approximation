#!/usr/bin/env python3
"""
tester.py

This script trains (if needed) and tests the SimGNN models using JSON graph pair files
produced by proteins_converter.py. It uses relative paths throughout.

Workflow:
1. Set training and testing graph folders to the JSON folder (../../data/PROTEINS_re/AIDS).
2. Check for a pretrained models in the "models" folder (./models relative to this script).
   - If found, load the models.
   - Otherwise, train the models and save it.
3. Test the models. It is assumed that trainer.score() returns a dictionary with performance
   metrics (e.g., predicted graph edit distance and accuracy).
4. Save the performance metrics to an Excel file in
   ../../scripts/data/PROTEINS_re/performance/performance.xlsx.

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

    # Override training and testing graph folders.
    # Default values (from parameter_parser) are "./dataset/train/" and "./dataset/test/"
    json_folder = os.path.abspath(os.path.join(script_dir, "..", "..", "data", "PROTEINS_re", "AIDS"))
    if args.training_graphs == "./dataset/train/":
        args.training_graphs = json_folder
    if args.testing_graphs == "./dataset/test/":
        args.testing_graphs = json_folder

    # Verify that training and testing folders exist.
    if not os.path.exists(args.training_graphs):
        print(f"Error: Training graphs folder '{args.training_graphs}' does not exist.")
        sys.exit(1)
    if not os.path.exists(args.testing_graphs):
        print(f"Error: Testing graphs folder '{args.testing_graphs}' does not exist.")
        sys.exit(1)

    print(f"Using training graphs folder: {args.training_graphs}")
    print(f"Using testing graphs folder: {args.testing_graphs}")

    # Set up models save/load path.
    model_dir = os.path.abspath(os.path.join(script_dir, "models"))
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        print(f"Created models directory: {model_dir}")
    # Define the models file path.
    model_file = os.path.join(model_dir, "simgnn_model.h5")

    # If a pretrained models exists, set load_path; otherwise, set save_path to train and save.
    if os.path.exists(model_file):
        args.load_path = model_file
        print(f"Pretrained models found. Will load models from: {model_file}")
    else:
        args.load_path = None
        args.save_path = model_file
        print("No pretrained models found. The models will be trained and saved.")

    # Print parameters in tabular format.
    tab_printer(args)

    # Initialize the SimGNN trainer.
    trainer = SimGNNTrainer(args)

    # Train or load the models.
    if args.load_path:
        trainer.load()
    else:
        trainer.fit()

    # Test the models.
    # It is assumed that trainer.score() returns a dictionary with performance metrics,
    # e.g., {"predicted_ged": ..., "accuracy": ...}
    performance = trainer.score()
    if performance is None:
        # If no performance dict is returned, create a placeholder.
        performance = {"predicted_ged": "N/A", "accuracy": "N/A"}

    # Save the models if it was trained.
    if args.save_path:
        trainer.save()

    # Prepare the performance output directory (relative path):
    perf_dir = os.path.abspath(
        os.path.join(script_dir, "..", "..", "scripts", "data", "PROTEINS_re", "performance"))
    if not os.path.exists(perf_dir):
        os.makedirs(perf_dir)
        print(f"Created performance directory: {perf_dir}")

    # Create a DataFrame from the performance metrics and save to an Excel file.
    df = pd.DataFrame([performance])
    excel_file = os.path.join(perf_dir, "performance.xlsx")
    df.to_excel(excel_file, index=False)
    print(f"Performance results saved to {excel_file}")


if __name__ == "__main__":
    main()
