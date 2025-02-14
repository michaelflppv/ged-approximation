"""SimGNN runner."""

import os
from utils import tab_printer
from simgnn import SimGNNTrainer
from param_parser import parameter_parser

def main():
    """
    Parsing command line parameters, reading data.
    Fitting and scoring a SimGNN model.
    """
    args = parameter_parser()
    tab_printer(args)
    trainer = SimGNNTrainer(args)

    if args.load_path:
        trainer.load()
    else:
        trainer.fit()
    #trainer.score()

    # Set default save path relative to the src folder if not provided.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(script_dir, "..", "models")
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)
    if not args.save_path:
        args.save_path = os.path.join(models_dir, "simgnn_model.pth")

    trainer.save()

if __name__ == "__main__":
    main()
