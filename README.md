# **Approximation Algorithms for Graph Edit Distance (GED)**  


This repository contains all code used for the **experimental work** in my Bachelor thesis on **Approximation Algorithms for Graph Edit Distance (GED)**. The experiments focus on benchmarking approximation methods against exact GED computations, using **AStar-BMao, GEDLIB** and **SimGNN** as the primary backend.

---

## **Repository Overview**
- **Graph Edit Distance (GED) Evaluation**: Compare multiple GED approximation algorithms.
- **Dataset Processing & Conversion**: Convert datasets to different formats (TXT → GXL/XML, JSON).
- **GEDLIB Benchmarking**: Execute and log results from AStar- and GEDLIB-based algorithms.
- **SimGNN Model Training & Evaluation**: Train and test a neural network-based GED predictor.
- **Results Analysis & Visualization**: Compare accuracy, runtime, and memory usage across methods.

To get started with this project, clone the repository to your local machine using [git](https://git-scm.com/):

```bash
git clone https://github.com/michaelflppv/ged-approximation.git
cd ged-approximation
```

## **📌 Important Notice: Using Precompiled Data**
This repository includes **precompiled datasets** and large files (e.g., GXL/XML files, JSON graph pairs, and pre-trained models). To ensure these files are correctly downloaded, [Git LFS (Large File Storage)](https://git-lfs.github.com/) must be installed.
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

#### 1.1 System & OS Dependencies
- **Linux**: Ubuntu 18.04+ / Debian / Fedora (recommended)
- **Windows**: Windows 10+ (WSL recommended)
- **macOS**: macOS 10.14+ (M1/M2 compatible)

#### 1.2 Language & Runtime Versions

- Python 3.9–3.11 (dependencies pinned via Poetry)
- C++17‑compatible compiler (e.g. GCC ≥ 7, Clang ≥ 5, MSVC ≥ 2017)

Python dependencies are managed with Poetry. After installing [Poetry](https://python-poetry.org/) and Git LFS, set up the environment with:
```bash
poetry install
# optional: enter the virtualenv
poetry shell
```
Use `poetry run <command>` when executing project scripts.

#### 1.3 Build Tools

- **CMake**: Required for building the C++ components. Install it from [CMake](https://cmake.org/download/).
- **Doxygen**: Required for generating documentation. Install it from [Doxygen](https://www.doxygen.nl/download.html).
- **OpenMP**: Required for parallel processing. Ensure your compiler supports [OpenMP](https://www.openmp.org/).
- **macOS**: Install `libomp` so headers and libs are available to CMake:
```bash
brew install libomp
```

Find more information on how to install these tools in [GEDLIB](https://github.com/dbblumenthal/gedlib).

### **2️⃣ Clone & Compile GEDLIB**
This repository partially relies on GEDLIB for GED computation. The required repository and its external libraries should already be installed within this project. If not, refer to the [GEDLIB](https://github.com/dbblumenthal/gedlib) for more information.

To compile the C++ code, navigate to the `gedlib` directory and run:
```bash
cd gedlib
python install.py --clean --doc --lib gxl
mkdir build && cd build
cmake ..
make
```

My repostory called **[mixup](https://github.com/michaelflppv/mixup.git)** contains a backup copy of GEDLIB with the source code, required to compile this project.

### **3️⃣ Set Up External Dependencies**
This project also relies on the **[Graph Edit Distance (GED) repository by Lijun Chang](https://github.com/LijunChang/Graph_Edit_Distance.git)** for **exact GED computation**.  

To use this repository:
1. **Clone the repository:**
   ```bash
   git clone https://github.com/LijunChang/Graph_Edit_Distance.git
   cd Graph_Edit_Distance
   ```
2. **Follow the build instructions** provided in the [repository]((https://github.com/LijunChang/Graph_Edit_Distance.git)) to compile and set up the exact GED computation framework.
---

## **🧪 Run Experiments**
### 1️⃣ Data Conversion
To convert datasets into the required formats, follow these steps:
- Navigate to the [src/converters](https://github.com/michaelflppv/ged-approximation/tree/main/src/converters) directory.
- Run the appropriate conversion script for your dataset. For example, to convert the AIDS dataset to GXL:
  - Choose [gxl_xml]() directory.
  - Select the appropriate script (e.g., `preprocess_aids.py`) or specify the dataset name in the script (e.g., `preprocess_all.py`).
  - Run the script:
  ```bash
   python preprocess_aids.py
   ```
### 2️⃣ Lower Bound Estimation
To estimate lower bounds for the graph pairs:
- Navigate to [heuristics](https://github.com/michaelflppv/ged-approximation/tree/main/heuristics) and run:
   ```bash
   python estimate_lower_bound.py
   ```
- The results will be saved in the `results/lower_bound` directory.

### 3️⃣ Exact GED Computation
To compute the exact GED using the AStar-BMao algorithm:
- Set up the environment as described in the **Installation & Setup** section.
- Navigate to [src/c++_parsers](https://github.com/michaelflppv/ged-approximation/blob/main/src/c%2B%2B_parsers).
- Run the AStar-BMao script:
   ```bash
   python astar_exact_ged.py
   ```
- If you want, you can adjust the amount of threads and graph pairs used for the computation in the script.
- The results will be saved in the `results/exact_ged` directory.

### 4️⃣ GEDLIB Computation
To compute an approximate GED using any algorithm available in the GEDLIB:
- Set up the environment as described in the **Installation & Setup** section.
- Navigate to [src/c++_parsers](https://github.com/michaelflppv/ged-approximation/blob/main/src/c%2B%2B_parsers).
- Select the appropriate script (e.g., `gedlib_parser.py`) and the algorithm you want to use.
- For changing the algorithm, you can modify the `command = [GED_EXECUTABLE, dataset_path, preprocessed_xml, "IPFP"]` line in the script.
- Run the script:
   ```bash
   python gedlib_parser.py
   ```

### 5️⃣ SimGNN Training & Evaluation
To train the model, navigate to [SimGNN/src](https://github.com/michaelflppv/ged-approximation/tree/main/SimGNN/src) and run `main.py`:
```bash 
python main.py
```
For more information and hyperparameter settings, refer to original [SimGNN repository](https://github.com/benedekrozemberczki/SimGNN).

To test the model, navigate to [SimGNN/src](https://github.com/michaelflppv/ged-approximation/tree/main/SimGNN/src) and run:
```bash
python simgnn_evaluate.py
```
To test the model on a specific dataset, you can modify the paths in the script. The results will be saved in the `results/simgnn` directory.

### 6️⃣ Edit Path Extraction & Validation
The repository includes tools for extracting and validating edit paths using GEDLIB algorithms and SimGNN. To extract edit paths:
- To extract edit path for a pair of graphs, navigate either to [src/c++_parsers](https://github.com/michaelflppv/ged-approximation/blob/main/src/c%2B%2B_parsers) or [SimGNN/src](https://github.com/michaelflppv/ged-approximation/tree/main/SimGNN/src) for GEDLIB and SimGNN respectively.
  - Run the appropriate script (e.g., `gedlib_edit_path.py` or `simgnn_extract_edit_path.py`) and specify the graph pair and dataset path.
- To validate or apply edit paths, navigate to [src/edit_path_test](https://github.com/michaelflppv/ged-approximation/tree/main/src/edit_path_test) and choose an appropriate script (e.g., `gedlib_validate_edit_path.py` or `apply_edit_path.py`). Modify the paths in the script to point to the edit path files and dataset.
- To validate the edit paths for SimGNN, navigate to [simgnn_validate_edit_path.py](https://github.com/michaelflppv/ged-approximation/blob/main/SimGNN/src/simgnn_validate_edit_path.py) and follow the same steps.

### 7️⃣ Results Analysis & Visualization
This repository includes Jupyter Notebooks for analyzing and visualizing the results of the experiments. To explore the results:
- Navigate to [notebooks](https://github.com/michaelflppv/ged-approximation/tree/main/src/analysis/notebooks).
- Open the desired notebook (e.g., `lower_bound_analysis.ipynb`, `plot_analysis.ipynb`, or `statistics_analysis.ipynb`) and run the cells to visualize the results.
---

## **🗃️ Datasets**

The repository includes several datasets for benchmarking the GED algorithms. The datasets are stored in the `data` directory and include:
- **AIDS**: A dataset of molecular graphs.
- **IMDB-BINARY**: A dataset of binary graphs representing movie co-appearances.
- **PROTEINS**: A dataset of protein structures represented as graphs.

These datasets were taken from TUDataset, which is a collection of benchmark datasets for graph machine learning. For more information on the datasets, refer to the [TUDataset](https://chrsmrrs.github.io/datasets/docs/datasets/) website.

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

- Blumenthal, D. B., Bougleux, S., Gamper, J., & Brun, L. (2019). GEDLIB: A C++ library for graph edit distance computation. In Graph-Based Representations in Pattern Recognition (GbRPR 2019). [Paper](https://doi.org/10.1007/978-3-030-20081-7_2).
- Blumenthal, D. B., Boria, N., Gamper, J., Bougleux, S., & Brun, L. (2020). Comparing heuristics for graph edit distance computation. VLDB Journal, 29(1), 419-458. [Paper](https://doi.org/10.1007/s00778-019-00544-1).
- Chang, L., Feng, X., Lin, X., Qin, L., Zhang, W., & Ouyang, D. (2020). Speeding Up GED Verification for Graph Similarity Search. In Proceedings of the 36th International Conference on Data Engineering (ICDE'20). [Paper](https://ieeexplore.ieee.org/document/9101700).
- Chang, L., Feng, X., Yao, K., Qin, L., & Zhang, W. (2022). Accelerating Graph Similarity Search via Efficient GED Computation. IEEE Transactions on Knowledge and Data Engineering (TKDE). [Paper](https://ieeexplore.ieee.org/document/9720081).
- Bai, Y., Ding, H., Bian, S., Chen, T., Sun, Y., & Wang, W. (2019). SimGNN: A Neural Network Approach to Fast Graph Similarity Computation. In Proceedings of the 12th ACM International Conference on Web Search and Data Mining (WSDM 2019). [Paper](http://web.cs.ucla.edu/~yzsun/papers/2019_WSDM_SimGNN.pdf).

The SimGNN implementation is based on the [original repository](https://github.com/benedekrozemberczki/SimGNN) by Benedek Rozemberczki.

---

## **📬 Contact**
For questions, create an issue or reach out via email.
