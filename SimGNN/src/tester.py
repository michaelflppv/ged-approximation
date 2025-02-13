import os
import glob
import torch
import pandas as pd
from simgnn import SimGNNTrainer
from param_parser import parameter_parser
from utils import process_pair


def main():
    # Parse command-line arguments for SimGNN settings.
    args = parameter_parser()

    # Initialize the trainer and set up the model.
    trainer = SimGNNTrainer(args)
    trainer.setup_model()
    trainer.model.eval()  # set to evaluation mode

    # Directory containing your 1000 JSON files.
    test_dir = "data/PROTEINS/json"  # adjust if necessary
    json_files = glob.glob(os.path.join(test_dir, "*.json"))

    if not json_files:
        print("No JSON files found in the test directory.")
        return

    results = []
    for json_file in json_files:
        try:
            # Process the JSON file into the internal format.
            data = process_pair(json_file)
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
            continue

        # Transfer data to torch tensors.
        copy_data = trainer.transfer_to_torch(data)

        # Predict the GED value with the model.
        with torch.no_grad():
            score = trainer.model(copy_data)
        # Assume the model output is the predicted GED value.
        predicted_ged = score.item()

        # Optionally, read the groundtruth GED from the JSON (if desired).
        ground_truth = data.get("ged", None)

        results.append({
            "file": os.path.basename(json_file),
            "predicted_ged": predicted_ged,
            "ground_truth": ground_truth
        })

        print(
            f"Processed {os.path.basename(json_file)}: predicted GED = {predicted_ged:.2f}, ground truth = {ground_truth}")

    # Save all results into an Excel file.
    output_file = os.path.join("data", "SimGNN_results.xlsx")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df = pd.DataFrame(results)
    df.to_excel(output_file, index=False, engine='openpyxl')

    print(f"All predictions completed. Results saved to {output_file}")


if __name__ == "__main__":
    main()
