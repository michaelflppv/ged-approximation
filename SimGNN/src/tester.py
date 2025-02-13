import os
import glob
import torch
import pandas as pd
from simgnn import SimGNNTrainer
from param_parser import parameter_parser
from utils import process_pair


def main():
    args = parameter_parser()
    trainer = SimGNNTrainer(args)
    trainer.setup_model()
    trainer.model.eval()

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    test_dir = os.path.join(BASE_DIR, 'data', 'AIDS', 'json')
    perf_dir = os.path.join(BASE_DIR, 'data', 'AIDS', 'performance')
    os.makedirs(perf_dir, exist_ok=True)
    output_file = os.path.join(perf_dir, "SimGNN_results.xlsx")

    json_files = glob.glob(os.path.join(test_dir, "*.json"))
    if not json_files:
        print("No JSON files found in:", test_dir)
        return

    results = []
    for json_file in json_files:
        try:
            data = process_pair(json_file)
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
            continue

        copy_data = trainer.transfer_to_torch(data)
        with torch.no_grad():
            score = trainer.model(copy_data)
        predicted_ged = score.item()
        ground_truth = data.get("ged", None)
        results.append({
            "file": os.path.basename(json_file),
            "predicted_ged": predicted_ged,
            "ground_truth": ground_truth
        })
        print(f"Processed {os.path.basename(json_file)}: Predicted GED = {predicted_ged:.2f}")

    df = pd.DataFrame(results)
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"All predictions completed. Results saved to {output_file}")


if __name__ == "__main__":
    main()
