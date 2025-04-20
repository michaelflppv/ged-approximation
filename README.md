# **Approximation Algorithms for Graph Edit Distance (GED)**  


This repository contains all code used for the **experimental work** in my Bachelor thesis on **Approximation Algorithms for Graph Edit Distance (GED)**. The experiments focus on benchmarking approximation methods against exact GED computations, using **GEDLIB** as the primary backend.

---

## **📌 Repository Overview**
- **Graph Edit Distance (GED) Evaluation**: Compare multiple GED approximation algorithms.
- **Dataset Processing & Conversion**: Convert datasets to different formats (TXT → GXL/XML, JSON).
- **GEDLIB Benchmarking**: Execute and log results from GEDLIB-based algorithms.
- **SimGNN Model Training & Evaluation**: Train and test a neural network-based GED predictor.
- **Results Analysis & Visualization**: Compare accuracy, runtime, and scalability across methods.

To get started with this project, clone the repository to your local machine using [git](https://git-scm.com/):

```bash
git clone https://github.com/michaelflppv/ged-approximation.git
cd ged-approximation
```

## **📌 Important Notice: Using Precompiled Data**
This repository includes **precompiled datasets** and large files (e.g., GXL/XML files, JSON graph pairs, and pre-trained models).  
To ensure these files are correctly downloaded, [Git LFS (Large File Storage)](https://git-lfs.github.com/) must be installed.
1. Download and install [Git LFS](https://git-lfs.github.com/).
2. Run the setup command:
```bash
git lfs install
```
3. Pull large files manually:
```bash
git lfs pull
```

---

## **📂 Project Structure**
```
📦 ged-approximation
├── 📜 README.md                       # Project documentation
├── 📂 data/                           # Raw graph datasets (AIDS, IMDB, etc.)
│   ├── 📂 AIDS/
│   ├── 📂 IMDB-BINARY/
│   ├── 📂 PROTEINS/
│   └── ...
├── 📂 processed_data/                # Preprocessed data for different tools
│   ├── 📂 gxl/                        # GXL graphs for GEDLIB
│   ├── 📂 json_pairs/                # JSON graph pairs for SimGNN
│   ├── 📂 synthetic_graphs/          # Synthetic graphs for experiments
│   ├── 📂 txt/                       # TXT graph pairs for AStar-BMao
│   ├── 📂 xml/                       # XML graph pair collections
├── 📂 results/                       # Stores output of GED computations
│   ├── 📂 exact_ged/                 # Ground truth edit distances
│   ├── 📂 extracted_paths/          # Edit paths from GEDLIB
│   ├── 📂 lower_bound/              # Lower bound estimations
│   ├── 📂 simgnn/                   # SimGNN predictions
│   ├── 📂 gedlib/                   # GEDLIB results
│   └── 📂 label_diversity/         # Label diversity stats
├── 📂 heuristics/                   # Heuristic lower bound estimations
│   ├── 📂 plots/                    # Visualizations of lower bounds
│   ├── 📜 estimate_lower_bound.py
│   └── 📜 validate_lower_bounds.py
├── 📂 SimGNN/                       # Neural GED model (SimGNN)
│   ├── 📂 assets/                   
│   ├── 📂 dataset/                 # Train/test data in JSON format
│   ├── 📂 models/                  # Saved PyTorch models
│   └── 📂 src/                     # Model code (SimGNN, training, eval)
│       ├── layers.py, simgnn.py, ...
│       └── simgnn_extract_edit_path.py, ...
📂 src/                                  # Main processing and analysis scripts
├── 📂 analysis/                         # Scripts and notebooks for analyzing GED results
│   ├── 📂 notebooks/                   # Jupyter Notebooks for visual exploration
│   │   ├── lower_bound_analysis.ipynb     # Analyze lower bound estimations
│   │   ├── plot_analysis.ipynb            # Plot comparison metrics
│   │   └── statistics_analysis.ipynb      # General dataset statistics
│   ├── 📂 C++_parsers/                 # Python wrappers for C++ GED results
│   │   ├── astar_exact_ged.py             # Parse A* GED output
│   │   ├── gedlib_edit_path.py            # Extract GEDLIB edit paths
│   │   └── gedlib_parser.py               # General GEDLIB result parser
├── 📂 converters/                      # Convert original TXT datasets into structured formats
│   ├── 📂 gxl_xml/                     # Convert to GXL/XML for GEDLIB
│   │   ├── preprocess_aids.py
│   │   ├── preprocess_imdb.py
│   │   ├── preprocess_proteins.py
│   │   └── preprocess_mutag.py
│   ├── 📂 json/                        # Convert to JSON for SimGNN
│   │   └── preprocess_all.py             
│   ├── 📂 txt/                         # TXT conversion handling
│   │   └── preprocess_all.py
├── 📂 edit_path_test/                 # Tools for evaluating edit paths (ground-truth vs predicted)
│   ├── 📂 generate_synthetic_graphs/  # Scripts for generating synthetic test data
│   │   ├── generate_gxl_collection.py     
│   │   └── generate_json_pairs.py         
│   ├── 📂 test/                       # Edit path validation utilities
│   │   └── gedlib_validate_edit_path.py   # Validate GEDLIB paths
│   └── 📜 apply_edit_path.py         # Apply and simulate edit path execution
├── 📂 helper_functions/              # Miscellaneous utility scripts
│   └── 📜 label_diversity_calculator.py   # Computes label diversity in datasets
├── 📂 gedlib/                      # GEDLIB C++ source and interface
│   ├── 📂 src/, include/, lib/     # C++ logic and libraries
│   ├── 📜 main.cpp, CMakeLists.txt # Entry and build files
│   └── 📜 install.py               # Installation script
├── 📂 median/                      # Placeholder (possibly for GED median)
├── 📂 tests/                       # Unit and functional tests
├── 📂 venv/                        # Python virtual environment (optional)
└── 📜 LICENSE, .gitignore, ...     # Meta files

```

---

## **🚀 Installation & Setup**
### **1️⃣ Install Dependencies**
Ensure you have Python 3 installed, then install the required packages:
```bash
pip install -r requirements.txt
```

### **2️⃣ Clone & Compile GEDLIB**
This repository partially relies on GEDLIB for GED computation. The required repository should already be installed within this poject. If not, refer to the [GEDLIB](https://github.com/dbblumenthal/gedlib) for more information.
Initial setup:
```bash
git clone https://github.com/dbblumenthal/gedlib.git
cd gedlib
mkdir build && cd build
cmake ..
make
```

My repostory called **[mixup](https://github.com/michaelflppv/mixup.git)** contains a backup copy of GEDLIB with the source code, required to compile this project.

### **📌 External Dependencies**
This project also relies on the **[Graph Edit Distance (GED) repository by Lijun Chang](https://github.com/LijunChang/Graph_Edit_Distance.git)** for **exact GED computation**.  

To use this repository:
1. **Clone the repository:**
   ```bash
   git clone https://github.com/LijunChang/Graph_Edit_Distance.git
   cd Graph_Edit_Distance
   ```
2. **Follow the build instructions** provided in the [repository]((https://github.com/LijunChang/Graph_Edit_Distance.git)) to compile and set up the exact GED computation framework.
---


## **📜 Citation & References**
If you use this code in your work, please cite:
```
@misc{Filippov2025,
  author = {Mikhail Filippov},
  title = {Approximation Algorithms for Graph Edit Distance (GED)},
  year = {2025},
  url = {https://github.com/michaelflppv/ged-approximation},
  note = {Bachelor Thesis, University of Mannheim}
}
```
For GEDLIB, refer to the [official repository](https://github.com/dbblumenthal/gedlib). The source code of GEDLIB is distributed under the [GNU Lesser General Public License](https://www.gnu.org/licenses/lgpl-3.0.en.html).

- D. B. Blumenthal, S. Bougleux, J. Gamper, and L. Brun. &ldquo;GEDLIB: A C++ library for graph edit distance computation&rdquo;, GbRPR 2019, [https://doi.org/10.1007/978-3-030-20081-7_2](https://doi.org/10.1007/978-3-030-20081-7_2)
- D. B. Blumenthal, N. Boria, J. Gamper, S. Bougleux, and L. Brun. &ldquo;Comparing heuristics for graph edit distance computation&rdquo;, VLDB J. 29(1), pp. 419-458, 2020, [https://doi.org/10.1007/s00778-019-00544-1](https://doi.org/10.1007/s00778-019-00544-1)

This repository provides a PyTorch implementation of SimGNN as described in the paper:

> SimGNN: A Neural Network Approach to Fast Graph Similarity Computation.
> Yunsheng Bai, Hao Ding, Song Bian, Ting Chen, Yizhou Sun, Wei Wang.
> WSDM, 2019.
> [[Paper]](http://web.cs.ucla.edu/~yzsun/papers/2019_WSDM_SimGNN.pdf)

and provided in [https://github.com/benedekrozemberczki/SimGNN](https://github.com/benedekrozemberczki/SimGNN).

---

## **📬 Contact**
For questions, create an issue or reach out via email.
